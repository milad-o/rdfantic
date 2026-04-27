"""rdfantic-specific exceptions."""

from __future__ import annotations


class RdfanticError(Exception):
    """Base exception for all rdfantic errors."""


class GraphReadError(RdfanticError):
    """Raised when reading from a graph fails for structural reasons."""


class EndpointError(RdfanticError):
    """Raised when a remote SPARQL endpoint request fails."""


class SubjectNotFoundError(GraphReadError):
    """Raised when no triples match the requested subject."""
