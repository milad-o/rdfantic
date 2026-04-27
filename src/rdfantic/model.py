"""GraphModel — Pydantic base class for RDF graph views."""

from __future__ import annotations

from typing import Any, ClassVar, Self, get_type_hints

from pydantic import BaseModel, ConfigDict, Field
from rdflib import RDF, BNode, Graph, URIRef
from rdflib.term import Identifier

from rdfantic.constraints import get_sh_constraints
from rdfantic.fields import get_predicate
from rdfantic.types import (
    python_value_to_rdf,
    rdf_value_to_python,
    unwrap_type,
)


class GraphModel(BaseModel):
    """A typed view into an RDF graph.

    Subclass this and declare fields with ``predicate()`` to map them to
    RDF predicates.  The model is a *lens* — it reads/writes only the
    triples it declares and ignores everything else in the graph.

    Class attributes set via ``model_config``:

    * ``rdf_type``: The ``rdf:type`` URI for nodes this view matches.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rdf_type: ClassVar[URIRef | None] = None

    subject: URIRef | BNode | None = Field(
        default=None,
        exclude=True,
        description="The RDF subject this instance was read from, or None.",
    )

    # ------------------------------------------------------------------
    # Read: graph → Python
    # ------------------------------------------------------------------

    @classmethod
    def from_graph(
        cls,
        graph: Graph,
        subject: URIRef | BNode,
        *,
        max_depth: int | None = None,
        _current_depth: int = 0,
    ) -> Self:
        """Read a node from the graph and validate it into this model.

        Only extracts predicates declared by the model's fields.
        Extra triples on the node are silently ignored (Open World).

        Args:
            graph: An rdflib Graph to read from.
            subject: The subject node to extract data for.
            max_depth: Maximum nesting depth for recursive traversal.
                ``None`` means unlimited. ``0`` means no nested models
                are traversed (their fields become ``None`` or empty).

        Returns:
            A validated instance of this model.

        Raises:
            ValidationError: If extracted data doesn't satisfy the model's
                type constraints (e.g. a required field has no matching triple).
        """
        hints = get_type_hints(cls)
        field_values: dict[str, Any] = {}
        depth_exceeded = max_depth is not None and _current_depth >= max_depth

        for field_name, field_info in cls.model_fields.items():
            pred = get_predicate(field_info)
            if pred is None:
                continue

            annotation = hints[field_name]
            inner_type, is_optional, is_multi = unwrap_type(annotation)

            # Check whether inner_type is a GraphModel subclass (nested view)
            is_nested = _is_graph_model(inner_type)

            objects = list(graph.objects(subject, pred))

            if is_multi:
                if is_nested and not depth_exceeded:
                    values = [
                        inner_type.from_graph(
                            graph,
                            obj,
                            max_depth=max_depth,
                            _current_depth=_current_depth + 1,
                        )
                        for obj in objects
                        if isinstance(obj, (URIRef, BNode))
                    ]
                elif is_nested:
                    values = []
                else:
                    values = [rdf_value_to_python(obj, inner_type) for obj in objects]
                # Preserve the declared collection type
                origin = _collection_origin(annotation)
                field_values[field_name] = origin(values) if origin else values
            elif objects:
                obj = objects[0]
                if is_nested and not depth_exceeded:
                    if isinstance(obj, (URIRef, BNode)):
                        field_values[field_name] = inner_type.from_graph(
                            graph,
                            obj,
                            max_depth=max_depth,
                            _current_depth=_current_depth + 1,
                        )
                elif is_nested:
                    field_values[field_name] = None
                else:
                    field_values[field_name] = rdf_value_to_python(obj, inner_type)
            elif is_optional:
                field_values[field_name] = None
            # else: missing required field — Pydantic validation will raise

        instance = cls.model_validate(field_values)
        instance.subject = subject
        return instance

    # ------------------------------------------------------------------
    # Write: Python → triples
    # ------------------------------------------------------------------

    def to_triples(
        self,
        subject: URIRef | BNode | None = None,
    ) -> list[tuple[Identifier, URIRef, Identifier]]:
        """Serialize this instance to a flat list of RDF triples.

        Nested models are serialized recursively and their triples are
        appended to the same list.  A linking triple connects the parent
        subject to the nested subject.  Use ``to_graph()`` if you only
        need the resulting graph and don't need to inspect individual triples.

        Args:
            subject: The subject IRI to use. Falls back to the subject
                this instance was read from, or generates a blank node.

        Returns:
            A flat list of (subject, predicate, object) triples, including
            triples from nested models.
        """
        subj = subject or self.subject or BNode()
        hints = get_type_hints(type(self), include_extras=True)
        triples: list[tuple[Identifier, URIRef, Identifier]] = []

        # Emit rdf:type triple
        rdf_type = type(self).rdf_type
        if rdf_type is not None:
            triples.append((subj, RDF.type, rdf_type))

        for field_name, field_info in type(self).model_fields.items():
            pred = get_predicate(field_info)
            if pred is None:
                continue

            value = getattr(self, field_name)
            if value is None:
                continue

            raw_annotation = hints[field_name]
            sh = get_sh_constraints(raw_annotation)
            dt_override = sh.datatype if sh else None
            inner_type, _, is_multi = unwrap_type(raw_annotation)
            is_nested = _is_graph_model(inner_type)

            if is_multi:
                for item in value:
                    if is_nested:
                        nested_triples = item.to_triples()
                        if nested_triples:
                            # Use the nested subject as the object link
                            nested_subj = nested_triples[0][0]
                            triples.append((subj, pred, nested_subj))
                            triples.extend(nested_triples)
                    else:
                        triples.append(
                            (
                                subj,
                                pred,
                                python_value_to_rdf(
                                    item, inner_type, datatype=dt_override
                                ),
                            )
                        )
            elif is_nested:
                nested_triples = value.to_triples()
                if nested_triples:
                    nested_subj = nested_triples[0][0]
                    triples.append((subj, pred, nested_subj))
                    triples.extend(nested_triples)
            else:
                triples.append(
                    (
                        subj,
                        pred,
                        python_value_to_rdf(value, inner_type, datatype=dt_override),
                    )
                )

        return triples

    def to_graph(
        self,
        graph: Graph | None = None,
        subject: URIRef | BNode | None = None,
    ) -> Graph:
        """Serialize this instance into an rdflib Graph.

        Args:
            graph: An existing graph to add triples to. Creates a new one if None.
            subject: The subject IRI to use.

        Returns:
            The graph with the model's triples added.
        """
        if graph is None:
            graph = Graph()
        for triple in self.to_triples(subject=subject):
            graph.add(triple)
        return graph

    def merge_into_graph(
        self,
        graph: Graph,
        subject: URIRef | BNode | None = None,
    ) -> Graph:
        """Replace the view-declared triples for a subject, then write new ones.

        Removes all triples whose predicates are declared by this model
        (plus ``rdf:type`` if the model declares one), then adds the
        current instance's triples.  Triples with predicates *not*
        declared by the model are left untouched.

        Args:
            graph: The graph to update in place.
            subject: The subject IRI.  Falls back to ``self.subject``.

        Returns:
            The updated graph.
        """
        subj = subject or self.subject
        if subj is None:
            msg = "merge_into_graph requires a subject"
            raise ValueError(msg)

        self.remove_from_graph(graph, subject=subj)
        for triple in self.to_triples(subject=subj):
            graph.add(triple)
        return graph

    @classmethod
    def remove_from_graph(
        cls,
        graph: Graph,
        subject: URIRef | BNode,
    ) -> Graph:
        """Remove all triples for a subject whose predicates this model declares.

        Predicates *not* declared by the model are left untouched.

        Args:
            graph: The graph to modify in place.
            subject: The subject node to clean.

        Returns:
            The modified graph.
        """
        preds_to_remove: list[URIRef] = []
        for field_info in cls.model_fields.values():
            pred = get_predicate(field_info)
            if pred is not None:
                preds_to_remove.append(pred)

        if cls.rdf_type is not None:
            graph.remove((subject, RDF.type, cls.rdf_type))

        for pred in preds_to_remove:
            graph.remove((subject, pred, None))

        return graph

    # ------------------------------------------------------------------
    # SHACL: model → shape graph
    # ------------------------------------------------------------------

    @classmethod
    def to_shacl(cls, shape_uri: URIRef | None = None) -> Graph:
        """Generate a SHACL NodeShape graph from this model's field declarations.

        The generated shape describes constraints derived from the model's
        type hints: datatype, cardinality (minCount/maxCount), and nested shapes.

        Args:
            shape_uri: Optional URI for the shape node. Auto-generated if None.

        Returns:
            An rdflib Graph containing the SHACL shape triples.
        """
        from rdfantic.shacl import model_to_shacl

        return model_to_shacl(cls, shape_uri=shape_uri)

    # ------------------------------------------------------------------
    # SPARQL: model → CONSTRUCT query
    # ------------------------------------------------------------------

    @classmethod
    def sparql_construct(cls, subject_var: str = "s") -> str:
        """Generate a SPARQL CONSTRUCT query that retrieves data for this model.

        The query constructs triples for every predicate declared by the model,
        with optional patterns for optional fields and multi-valued fields.

        Args:
            subject_var: Variable name for the subject (without ``?`` prefix).

        Returns:
            A SPARQL CONSTRUCT query string.
        """
        from rdfantic.sparql import model_to_construct

        return model_to_construct(cls, subject_var=subject_var)

    # ------------------------------------------------------------------
    # Remote SPARQL: endpoint → model
    # ------------------------------------------------------------------

    @classmethod
    def from_endpoint(
        cls,
        endpoint: str,
        subject: URIRef,
        *,
        max_depth: int | None = None,
        timeout: float = 30.0,
    ) -> Self:
        """Read a node from a remote SPARQL endpoint.

        Generates a CONSTRUCT query from the model, executes it against
        the endpoint, and reads the resulting graph with ``from_graph``.

        Args:
            endpoint: The SPARQL endpoint URL.
            subject: The subject node to retrieve.
            max_depth: Maximum nesting depth (forwarded to ``from_graph``).
            timeout: HTTP request timeout in seconds. Defaults to 30.

        Returns:
            A validated instance of this model.
        """
        from rdfantic.sparql import model_to_construct_for_subject

        query = model_to_construct_for_subject(cls, subject)
        result_graph = Graph()
        result_graph.parse(
            data=_sparql_query(endpoint, query, timeout=timeout),
            format="xml",
        )
        return cls.from_graph(result_graph, subject, max_depth=max_depth)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _is_graph_model(tp: type) -> bool:
    """Check if a type is a GraphModel subclass."""
    try:
        return isinstance(tp, type) and issubclass(tp, GraphModel)
    except TypeError:
        return False


def _collection_origin(annotation: Any) -> type | None:
    """Get the collection constructor for a multi-valued type."""
    from typing import get_origin

    origin = get_origin(annotation)
    # Handle Optional[set[X]] by unwrapping first
    if origin is None:
        return None
    if origin in (set, frozenset):
        return origin
    if origin is list:
        return list
    return None


def _sparql_query(endpoint: str, query: str, *, timeout: float = 30.0) -> bytes:
    """Execute a SPARQL query against a remote endpoint via HTTP.

    Uses urllib to avoid adding httpx/requests as a required dependency.

    Args:
        endpoint: The SPARQL endpoint URL.
        query: The SPARQL query string.
        timeout: HTTP request timeout in seconds.

    Raises:
        EndpointError: If the URL is invalid or the request fails.
    """
    from urllib.error import URLError
    from urllib.parse import urlencode, urlparse
    from urllib.request import Request, urlopen

    from rdfantic.exceptions import EndpointError

    parsed = urlparse(endpoint)
    if parsed.scheme not in ("http", "https"):
        msg = f"Endpoint URL must use http or https scheme, got {parsed.scheme!r}"
        raise EndpointError(msg)

    data = urlencode({"query": query}).encode()
    req = Request(
        endpoint,
        data=data,
        headers={"Accept": "application/rdf+xml"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except URLError as exc:
        msg = f"SPARQL endpoint request failed: {exc}"
        raise EndpointError(msg) from exc
