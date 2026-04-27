"""Type analysis utilities for mapping Python types to RDF/XSD."""

from __future__ import annotations

import types
import typing
from typing import Any, Union, get_args, get_origin

from rdflib import XSD, Literal, URIRef
from rdflib.term import Node

# Python type → XSD datatype mapping
_PYTHON_TO_XSD: dict[type, URIRef] = {
    str: XSD.string,
    int: XSD.integer,
    float: XSD.double,
    bool: XSD.boolean,
}


def python_type_to_xsd(py_type: type) -> URIRef | None:
    """Map a Python scalar type to its XSD datatype URI.

    Returns None for types that don't have a direct XSD mapping (e.g. nested models).
    """
    return _PYTHON_TO_XSD.get(py_type)


def is_multi_valued(annotation: Any) -> bool:
    """Check whether a type annotation represents a multi-valued field.

    Recognizes ``set[T]``, ``list[T]``, ``frozenset[T]``.
    """
    origin = get_origin(annotation)
    return origin in (set, list, frozenset)


def unwrap_type(annotation: Any) -> tuple[type, bool, bool]:
    """Unwrap a type annotation into its core type and characteristics.

    Handles ``Annotated``, ``Optional``/``X | None``, and collection types.

    Returns:
        A tuple of (inner_type, is_optional, is_multi).

    Examples:
        ``str`` → (str, False, False)
        ``int | None`` → (int, True, False)
        ``set[str]`` → (str, False, True)
        ``Annotated[int | None, ...]`` → (int, True, False)
    """
    is_optional = False
    is_multi = False

    # Strip Annotated wrapper
    origin = get_origin(annotation)
    if origin is typing.Annotated:
        annotation = get_args(annotation)[0]
        origin = get_origin(annotation)

    # Handle Union / Optional (X | None)
    if origin is Union or origin is types.UnionType:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) > len(non_none):
            is_optional = True
            annotation = non_none[0]
            origin = get_origin(annotation)

    # Strip Annotated again (for Optional[Annotated[...]])
    if origin is typing.Annotated:
        annotation = get_args(annotation)[0]
        origin = get_origin(annotation)

    # Handle collection types
    if origin in (set, list, frozenset):
        is_multi = True
        args = get_args(annotation)
        annotation = args[0] if args else str

    return annotation, is_optional, is_multi


def python_value_to_rdf(
    value: Any,
    py_type: type,
    datatype: URIRef | None = None,
) -> Node:
    """Convert a Python value to an rdflib term.

    For scalar types with known XSD mappings, produces a typed Literal.
    For URIRef values, returns them directly.

    Args:
        value: The Python value to convert.
        py_type: The Python type of the value (used for default XSD mapping).
        datatype: Optional explicit XSD datatype URI override.
    """
    if isinstance(value, URIRef):
        return value
    if datatype is not None:
        return Literal(value, datatype=datatype)
    xsd_type = python_type_to_xsd(py_type)
    if xsd_type is not None:
        return Literal(value, datatype=xsd_type)
    return Literal(value)


def rdf_value_to_python(node: Node, py_type: type) -> Any:
    """Convert an rdflib term to a Python value.

    For Literals, uses rdflib's ``toPython()``.  For URIRefs, returns the
    string URI.  BNodes are stringified to their identifier — this is
    intentional for scalar fields; nested GraphModel fields are resolved
    by ``from_graph`` before this function is called.
    """
    if isinstance(node, Literal):
        return node.toPython()
    if isinstance(node, URIRef):
        return str(node)
    return str(node)
