"""GraphModel — Pydantic base class for RDF graph views."""

from __future__ import annotations

from typing import Any, ClassVar, Self, get_type_hints

from pydantic import BaseModel, ConfigDict
from rdflib import RDF, BNode, Graph, Namespace, URIRef
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
    * ``namespace``: Default namespace for subject IRIs.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rdf_type: ClassVar[URIRef | None] = None
    namespace: ClassVar[Namespace | None] = None

    _subject: URIRef | BNode | None = None

    @property
    def subject(self) -> URIRef | BNode | None:
        """The RDF subject this instance was read from, or None."""
        return self._subject

    # ------------------------------------------------------------------
    # Read: graph → Python
    # ------------------------------------------------------------------

    @classmethod
    def from_graph(cls, graph: Graph, subject: URIRef | BNode) -> Self:
        """Read a node from the graph and validate it into this model.

        Only extracts predicates declared by the model's fields.
        Extra triples on the node are silently ignored (Open World).

        Args:
            graph: An rdflib Graph to read from.
            subject: The subject node to extract data for.

        Returns:
            A validated instance of this model.

        Raises:
            ValidationError: If extracted data doesn't satisfy the model's
                type constraints (e.g. a required field has no matching triple).
        """
        hints = get_type_hints(cls)
        field_values: dict[str, Any] = {}

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
                if is_nested:
                    values = [
                        inner_type.from_graph(graph, obj)
                        for obj in objects
                        if isinstance(obj, (URIRef, BNode))
                    ]
                else:
                    values = [rdf_value_to_python(obj, inner_type) for obj in objects]
                # Preserve the declared collection type
                origin = _collection_origin(annotation)
                field_values[field_name] = origin(values) if origin else values
            elif objects:
                obj = objects[0]
                if is_nested:
                    if isinstance(obj, (URIRef, BNode)):
                        field_values[field_name] = inner_type.from_graph(graph, obj)
                else:
                    field_values[field_name] = rdf_value_to_python(obj, inner_type)
            elif is_optional:
                field_values[field_name] = None
            # else: missing required field — Pydantic validation will raise

        instance = cls.model_validate(field_values)
        instance._subject = subject
        return instance

    # ------------------------------------------------------------------
    # Write: Python → triples
    # ------------------------------------------------------------------

    def to_triples(
        self,
        subject: URIRef | BNode | None = None,
    ) -> list[tuple[Identifier, URIRef, Identifier]]:
        """Serialize this instance to a list of RDF triples.

        Args:
            subject: The subject IRI to use. Falls back to the subject
                this instance was read from, or generates a blank node.

        Returns:
            A list of (subject, predicate, object) triples.
        """
        subj = subject or self._subject or BNode()
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
