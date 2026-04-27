"""Utilities for RDF namespace handling."""

from __future__ import annotations

from rdflib import Namespace, URIRef


def bind_namespace(prefix: str, uri: str | URIRef) -> Namespace:
    """Create an rdflib Namespace from a prefix and URI.

    Convenience wrapper so users don't need to import ``rdflib.Namespace``
    separately.

    Args:
        prefix: Short namespace prefix (for documentation; not bound to a graph here).
        uri: Base URI for the namespace.

    Returns:
        An rdflib ``Namespace`` object.
    """
    return Namespace(str(uri))
