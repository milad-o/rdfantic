"""SPARQL CONSTRUCT query generation from GraphModel definitions."""

from __future__ import annotations

from typing import get_type_hints

from rdflib import URIRef

from rdfantic.fields import get_predicate
from rdfantic.types import unwrap_type


def model_to_construct(model_cls: type, subject_var: str = "s") -> str:
    """Generate a SPARQL CONSTRUCT query from a GraphModel subclass.

    Required fields become required triple patterns in WHERE.
    Optional/multi-valued fields become OPTIONAL blocks.

    Args:
        model_cls: A GraphModel subclass.
        subject_var: The SPARQL variable name for the subject (without ``?``).

    Returns:
        A SPARQL CONSTRUCT query string.
    """
    hints = get_type_hints(model_cls)
    rdf_type = getattr(model_cls, "rdf_type", None)

    construct_patterns: list[str] = []
    required_patterns: list[str] = []
    optional_patterns: list[str] = []

    s = f"?{subject_var}"

    # rdf:type pattern
    if rdf_type is not None:
        type_uri = _sparql_uri(rdf_type)
        construct_patterns.append(f"  {s} a {type_uri} .")
        required_patterns.append(f"  {s} a {type_uri} .")

    for field_name, field_info in model_cls.model_fields.items():
        pred = get_predicate(field_info)
        if pred is None:
            continue

        annotation = hints[field_name]
        _, is_optional, is_multi = unwrap_type(annotation)

        pred_uri = _sparql_uri(pred)
        var = f"?{field_name}"
        pattern = f"  {s} {pred_uri} {var} ."

        construct_patterns.append(pattern)

        if is_optional or is_multi:
            optional_patterns.append(f"  OPTIONAL {{ {pattern.strip()} }}")
        else:
            required_patterns.append(pattern)

    # Build query
    construct_block = "\n".join(construct_patterns)
    where_lines = required_patterns + optional_patterns
    where_block = "\n".join(where_lines)

    return f"CONSTRUCT {{\n{construct_block}\n}} WHERE {{\n{where_block}\n}}"


def model_to_construct_for_subject(model_cls: type, subject: URIRef) -> str:
    """Generate a CONSTRUCT query bound to a specific subject IRI.

    Like ``model_to_construct`` but replaces the variable with a concrete
    IRI, suitable for querying a remote endpoint for one node.
    """
    query = model_to_construct(model_cls, subject_var="s")
    return query.replace("?s ", f"{_sparql_uri(subject)} ")


def _sparql_uri(uri: URIRef) -> str:
    """Format a URI for SPARQL (full IRI in angle brackets)."""
    return f"<{uri}>"
