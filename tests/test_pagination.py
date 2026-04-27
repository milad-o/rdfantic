"""Tests for pagination (Page[Model] and paginate)."""

from __future__ import annotations

import pytest
from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, Page, paginate, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class _PaginationCityView(GraphModel):
    rdf_type = SCHEMA["City"]
    name: str = predicate(SCHEMA["name"])


class _PersonWithCity(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    birthPlace: _PaginationCityView | None = predicate(SCHEMA["birthPlace"])


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])


def _people_graph(count: int) -> Graph:
    """Create a graph with N Person nodes."""
    g = Graph()
    for i in range(count):
        subj = EX[f"person{i}"]
        g.add((subj, RDF.type, SCHEMA["Person"]))
        g.add((subj, SCHEMA["name"], Literal(f"Person {i}", datatype=XSD.string)))
    return g


class TestPaginate:
    def test_basic_pagination(self) -> None:
        g = _people_graph(5)
        page = paginate(PersonView, g, offset=0, limit=3)

        assert isinstance(page, Page)
        assert page.total == 5
        assert page.offset == 0
        assert page.limit == 3
        assert len(page.items) == 3

    def test_second_page(self) -> None:
        g = _people_graph(5)
        page = paginate(PersonView, g, offset=3, limit=3)

        assert page.total == 5
        assert len(page.items) == 2  # Only 2 remaining

    def test_empty_graph(self) -> None:
        g = Graph()
        page = paginate(PersonView, g, offset=0, limit=10)

        assert page.total == 0
        assert page.items == []

    def test_offset_beyond_total(self) -> None:
        g = _people_graph(3)
        page = paginate(PersonView, g, offset=10, limit=5)

        assert page.total == 3
        assert page.items == []

    def test_items_are_model_instances(self) -> None:
        g = _people_graph(2)
        page = paginate(PersonView, g, offset=0, limit=10)

        for item in page.items:
            assert isinstance(item, PersonView)
            assert item.name.startswith("Person ")

    def test_requires_rdf_type(self) -> None:
        class NoTypeModel(GraphModel):
            name: str = predicate(SCHEMA["name"])

        with pytest.raises(ValueError, match="rdf_type"):
            paginate(NoTypeModel, Graph())

    def test_page_serializes_to_dict(self) -> None:
        """Page should serialize cleanly for FastAPI JSON responses."""
        g = _people_graph(2)
        page = paginate(PersonView, g, offset=0, limit=10)

        data = page.model_dump()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_max_depth_forwarded(self) -> None:
        """max_depth is forwarded to from_graph."""
        PersonWithCity = _PersonWithCity

        g = Graph()
        g.add((EX["p1"], RDF.type, SCHEMA["Person"]))
        g.add((EX["p1"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
        g.add((EX["p1"], SCHEMA["birthPlace"], EX["c1"]))
        g.add((EX["c1"], RDF.type, SCHEMA["City"]))
        g.add((EX["c1"], SCHEMA["name"], Literal("NYC", datatype=XSD.string)))

        page = paginate(PersonWithCity, g, max_depth=0)
        assert page.items[0].birthPlace is None

        page = paginate(PersonWithCity, g, max_depth=1)
        assert page.items[0].birthPlace is not None
        assert page.items[0].birthPlace.name == "NYC"
