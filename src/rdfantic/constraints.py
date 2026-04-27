"""SHACL constraint descriptors for use with ``typing.Annotated``.

Allows attaching explicit SHACL constraints to GraphModel fields::

    from typing import Annotated
    from rdfantic.constraints import SHConstraint

    class MovieView(GraphModel):
        genres: Annotated[
            set[str], SHConstraint(min_count=1)
        ] = predicate(SCHEMA["genre"])
        budget: Annotated[
            int | None,
            SHConstraint(datatype=XSD.nonNegativeInteger),
        ] = predicate(SCHEMA["budget"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rdflib import URIRef


@dataclass(frozen=True, slots=True)
class SHConstraint:
    """A bag of explicit SHACL property-shape constraints.

    Any field left as ``None`` means "use the default inferred from the type hint".
    Providing a value *overrides* the default.
    """

    min_count: int | None = None
    max_count: int | None = None
    datatype: URIRef | None = None
    pattern: str | None = None
    min_inclusive: int | float | None = None
    max_inclusive: int | float | None = None
    min_exclusive: int | float | None = None
    max_exclusive: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    node_kind: URIRef | None = None
    has_value: Any = None
    class_: URIRef | None = None
    name: str | None = None
    description: str | None = None
    extra: dict[URIRef, Any] = field(default_factory=dict)


def get_sh_constraints(annotation: Any) -> SHConstraint | None:
    """Extract the first ``SHConstraint`` from a ``typing.Annotated`` type, if any."""
    import typing
    from typing import get_args, get_origin

    if get_origin(annotation) is typing.Annotated:
        for arg in get_args(annotation)[1:]:
            if isinstance(arg, SHConstraint):
                return arg

    # Also check unwrapped optionals: Optional[Annotated[...]] or Annotated[...] | None
    import types as _types

    origin = get_origin(annotation)
    if origin is _types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            result = get_sh_constraints(arg)
            if result is not None:
                return result

    return None
