"""Field descriptors for mapping Pydantic fields to RDF predicates."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic.fields import FieldInfo
from rdflib import URIRef

PREDICATE_KEY = "rdf_predicate"


def _schema_extra_filter(schema: dict[str, Any]) -> None:
    """Remove internal RDF metadata from the JSON Schema output."""
    schema.pop(PREDICATE_KEY, None)


def predicate(uri: URIRef | str, **kwargs: Any) -> FieldInfo:
    """Declare a field that maps to an RDF predicate.

    Args:
        uri: The RDF predicate URI this field corresponds to.
        **kwargs: Additional keyword arguments forwarded to ``pydantic.Field``.

    Returns:
        A Pydantic ``FieldInfo`` with the predicate URI stored in metadata.
    """
    if isinstance(uri, str):
        uri = URIRef(uri)

    field_info = Field(json_schema_extra=_schema_extra_filter, **kwargs)
    field_info.metadata.append({PREDICATE_KEY: uri})
    return field_info


def get_predicate(field_info: FieldInfo) -> URIRef | None:
    """Extract the RDF predicate URI from a field's metadata."""
    for item in field_info.metadata:
        if isinstance(item, dict) and PREDICATE_KEY in item:
            return item[PREDICATE_KEY]
    return None
