"""Pydantic views for RDF graphs."""

from rdfantic._version import __version__
from rdfantic.constraints import SHConstraint
from rdfantic.fields import predicate
from rdfantic.model import GraphModel
from rdfantic.namespace import bind_namespace

__all__ = [
    "GraphModel",
    "SHConstraint",
    "__version__",
    "bind_namespace",
    "predicate",
]
