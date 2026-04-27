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
    return _build_construct(model_cls, subject_term=f"?{subject_var}")


def model_to_construct_for_subject(model_cls: type, subject: URIRef) -> str:
    """Generate a CONSTRUCT query bound to a specific subject IRI.

    Like ``model_to_construct`` but uses a concrete IRI instead of a variable,
    suitable for querying a remote endpoint for one node.
    """
    return _build_construct(model_cls, subject_term=_sparql_uri(subject))


def _build_construct(model_cls: type, subject_term: str) -> str:
    """Build a SPARQL CONSTRUCT query with the given subject term.

    Recursively includes triple patterns for nested GraphModel fields.

    Args:
        model_cls: A GraphModel subclass.
        subject_term: Either a SPARQL variable (``?s``) or a bound IRI (``<...>``).
    """
    construct_patterns: list[str] = []
    required_patterns: list[str] = []
    optional_patterns: list[str] = []

    _collect_patterns(
        model_cls,
        subject_term,
        construct_patterns,
        required_patterns,
        optional_patterns,
        _visited=set(),
    )

    construct_block = "\n".join(construct_patterns)
    where_lines = required_patterns + optional_patterns
    where_block = "\n".join(where_lines)

    return f"CONSTRUCT {{\n{construct_block}\n}} WHERE {{\n{where_block}\n}}"


def _collect_patterns(
    model_cls: type,
    subject_term: str,
    construct_patterns: list[str],
    required_patterns: list[str],
    optional_patterns: list[str],
    *,
    _visited: set[type],
    _var_prefix: str = "",
) -> None:
    """Collect SPARQL patterns for a model, recursing into nested GraphModels."""
    from rdfantic.model import GraphModel

    if model_cls in _visited:
        return
    _visited.add(model_cls)

    hints = get_type_hints(model_cls)
    rdf_type = getattr(model_cls, "rdf_type", None)
    s = subject_term

    if rdf_type is not None:
        type_uri = _sparql_uri(rdf_type)
        construct_patterns.append(f"  {s} a {type_uri} .")
        required_patterns.append(f"  {s} a {type_uri} .")

    for field_name, field_info in model_cls.model_fields.items():
        pred = get_predicate(field_info)
        if pred is None:
            continue

        annotation = hints[field_name]
        inner_type, is_optional, is_multi = unwrap_type(annotation)
        is_nested = isinstance(inner_type, type) and issubclass(inner_type, GraphModel)

        pred_uri = _sparql_uri(pred)
        var = f"?{_var_prefix}{field_name}"
        pattern = f"  {s} {pred_uri} {var} ."

        construct_patterns.append(pattern)

        if is_optional or is_multi:
            optional_patterns.append(f"  OPTIONAL {{ {pattern.strip()} }}")
        else:
            required_patterns.append(pattern)

        if is_nested:
            _collect_patterns(
                inner_type,
                var,
                construct_patterns,
                required_patterns,
                optional_patterns,
                _visited=_visited,
                _var_prefix=f"{_var_prefix}{field_name}_",
            )


def _sparql_uri(uri: URIRef) -> str:
    """Format a URI for SPARQL (full IRI in angle brackets).

    Raises:
        ValueError: If the URI contains characters illegal in a SPARQL IRI
            reference (``<``, ``>``, ``{``, ``}``, ``|``, ``\\``, ``^``,
            backtick, or whitespace).
    """
    _ILLEGAL = set("<>{}|\\^`")
    uri_str = str(uri)
    bad = _ILLEGAL.intersection(uri_str)
    if bad or any(c.isspace() for c in uri_str):
        msg = f"URI contains characters illegal in SPARQL IRI: {uri_str!r}"
        raise ValueError(msg)
    return f"<{uri_str}>"
