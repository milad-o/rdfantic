"""Pydantic views for RDF graphs."""

from rdfantic._version import __version__
from rdfantic.constraints import SHConstraint
from rdfantic.fields import predicate
from rdfantic.model import GraphModel
from rdfantic.namespace import bind_namespace
from rdfantic.pagination import Page, paginate

__all__ = [
    "GraphModel",
    "Page",
    "SHConstraint",
    "__version__",
    "bind_namespace",
    "paginate",
    "predicate",
]
