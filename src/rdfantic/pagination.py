"""Pagination support for SPARQL-backed queries.

Provides a generic ``Page[Model]`` wrapper for paginated results,
designed for use with FastAPI or any framework that consumes Pydantic models.

Usage with FastAPI::

    from fastapi import FastAPI
    from rdfantic.pagination import Page, paginate

    app = FastAPI()

    @app.get("/movies", response_model=Page[MovieView])
    def list_movies(offset: int = 0, limit: int = 10):
        return paginate(MovieView, graph, offset=offset, limit=limit)
"""

from pydantic import BaseModel
from rdflib import RDF, Graph


class Page[T](BaseModel):
    """A paginated response containing a slice of results and total count.

    Attributes:
        items: The current page of model instances.
        total: Total number of matching subjects in the graph.
        offset: The starting index of this page.
        limit: Maximum number of items per page.
    """

    items: list[T]
    total: int
    offset: int
    limit: int


def paginate(
    model_cls: type,
    graph: Graph,
    *,
    offset: int = 0,
    limit: int = 10,
    max_depth: int | None = None,
) -> Page:
    """Read paginated model instances from a graph.

    Finds all subjects matching the model's ``rdf_type`` and returns
    a ``Page`` containing the requested slice.

    .. note::

        All matching subjects are collected into a sorted list before slicing.
        This is fine for small-to-medium graphs but will use proportional memory
        on very large ones.

    Args:
        model_cls: A GraphModel subclass.
        graph: The rdflib Graph to query.
        offset: Number of subjects to skip.
        limit: Maximum number of subjects to return.
        max_depth: Forwarded to ``from_graph``.

    Returns:
        A ``Page`` with the matching instances, total count, and pagination metadata.

    Raises:
        ValueError: If the model has no ``rdf_type`` defined.
    """
    rdf_type = getattr(model_cls, "rdf_type", None)
    if rdf_type is None:
        msg = "paginate requires a model with rdf_type defined"
        raise ValueError(msg)

    subjects = sorted(set(graph.subjects(RDF.type, rdf_type)))
    total = len(subjects)
    page_subjects = subjects[offset : offset + limit]

    items = [
        model_cls.from_graph(graph, subj, max_depth=max_depth) for subj in page_subjects
    ]

    return Page(items=items, total=total, offset=offset, limit=limit)
