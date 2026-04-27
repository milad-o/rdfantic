"""SHACL shape generation from GraphModel definitions."""

from __future__ import annotations

from typing import get_type_hints

from rdflib import RDF, SH, XSD, BNode, Graph, Literal, URIRef

from rdfantic.constraints import get_sh_constraints
from rdfantic.fields import get_predicate
from rdfantic.types import python_type_to_xsd, unwrap_type


def model_to_shacl(
    model_cls: type,
    shape_uri: URIRef | None = None,
) -> Graph:
    """Generate a SHACL NodeShape graph from a GraphModel subclass.

    Constraints are derived from type hints by default and can be overridden
    or extended with ``Annotated[..., SHConstraint(...)]``.

    Recursively generates shapes for nested GraphModel fields.

    Args:
        model_cls: A GraphModel subclass.
        shape_uri: Optional URI for the top-level shape node.

    Returns:
        An rdflib Graph containing all SHACL shapes.
    """
    g = Graph()
    g.bind("sh", SH)
    _build_shape(model_cls, g, shape_uri=shape_uri, _visited=set())
    return g


def _build_shape(
    model_cls: type,
    g: Graph,
    *,
    shape_uri: URIRef | None = None,
    _visited: set[type],
) -> None:
    """Build a single SHACL NodeShape and recurse into nested models."""
    from rdfantic.model import GraphModel

    if model_cls in _visited:
        return
    _visited.add(model_cls)

    shape = shape_uri or BNode()
    g.add((shape, RDF.type, SH.NodeShape))

    rdf_type = getattr(model_cls, "rdf_type", None)
    if rdf_type is not None:
        g.add((shape, SH.targetClass, rdf_type))

    hints = get_type_hints(model_cls, include_extras=True)

    for field_name, field_info in model_cls.model_fields.items():
        pred = get_predicate(field_info)
        if pred is None:
            continue

        raw_annotation = hints[field_name]
        sh = get_sh_constraints(raw_annotation)
        inner_type, is_optional, is_multi = unwrap_type(raw_annotation)
        is_nested = isinstance(inner_type, type) and issubclass(inner_type, GraphModel)

        prop = BNode()
        g.add((shape, SH.property, prop))
        g.add((prop, SH.path, pred))

        # --- Cardinality (defaults, then override) ---
        if sh and sh.min_count is not None:
            _add_int(g, prop, SH.minCount, sh.min_count)
        elif (not is_multi and not is_optional) or (is_multi and not is_optional):
            _add_int(g, prop, SH.minCount, 1)

        if sh and sh.max_count is not None:
            _add_int(g, prop, SH.maxCount, sh.max_count)
        elif not is_multi:
            _add_int(g, prop, SH.maxCount, 1)

        # --- Datatype / class (override, then default) ---
        if sh and sh.datatype is not None:
            g.add((prop, SH.datatype, sh.datatype))
        elif sh and sh.class_ is not None:
            g.add((prop, SH["class"], sh.class_))
        elif is_nested:
            nested_rdf_type = getattr(inner_type, "rdf_type", None)
            if nested_rdf_type is not None:
                g.add((prop, SH["class"], nested_rdf_type))
            # Recursively generate shape for the nested model
            _build_shape(inner_type, g, _visited=_visited)
        else:
            xsd = python_type_to_xsd(inner_type)
            if xsd is not None:
                g.add((prop, SH.datatype, xsd))

        # --- Extra SHConstraint fields ---
        if sh:
            if sh.pattern is not None:
                g.add((prop, SH.pattern, Literal(sh.pattern)))
            if sh.min_inclusive is not None:
                g.add((prop, SH.minInclusive, Literal(sh.min_inclusive)))
            if sh.max_inclusive is not None:
                g.add((prop, SH.maxInclusive, Literal(sh.max_inclusive)))
            if sh.min_exclusive is not None:
                g.add((prop, SH.minExclusive, Literal(sh.min_exclusive)))
            if sh.max_exclusive is not None:
                g.add((prop, SH.maxExclusive, Literal(sh.max_exclusive)))
            if sh.min_length is not None:
                _add_int(g, prop, SH.minLength, sh.min_length)
            if sh.max_length is not None:
                _add_int(g, prop, SH.maxLength, sh.max_length)
            if sh.node_kind is not None:
                g.add((prop, SH.nodeKind, sh.node_kind))
            if sh.has_value is not None:
                g.add((prop, SH.hasValue, Literal(sh.has_value)))
            if sh.name is not None:
                g.add((prop, SH.name, Literal(sh.name)))
            if sh.description is not None:
                g.add((prop, SH.description, Literal(sh.description)))
            for extra_pred, extra_val in sh.extra.items():
                if isinstance(extra_val, URIRef):
                    g.add((prop, extra_pred, extra_val))
                else:
                    g.add((prop, extra_pred, Literal(extra_val)))


def _add_int(g: Graph, subject: BNode, pred: URIRef, value: int) -> None:
    """Add an xsd:integer literal triple."""
    g.add((subject, pred, Literal(value, datatype=XSD.integer)))
