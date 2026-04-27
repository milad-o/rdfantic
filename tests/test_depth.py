"""Tests for depth control on from_graph."""

from __future__ import annotations

from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class CityView(GraphModel):
    rdf_type = SCHEMA["City"]
    name: str = predicate(SCHEMA["name"])


class _StudioView(GraphModel):
    rdf_type = SCHEMA["Organization"]
    name: str = predicate(SCHEMA["name"])


class _ProducerView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    studios: list[_StudioView] = predicate(SCHEMA["productionCompany"])


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    birthPlace: CityView | None = predicate(SCHEMA["birthPlace"])


class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    director: PersonView | None = predicate(SCHEMA["director"])


def _deep_graph() -> Graph:
    """Movie → director (Person) → birthPlace (City), 3 levels deep."""
    g = Graph()
    g.add((EX["inception"], SCHEMA["name"], Literal("Inception", datatype=XSD.string)))
    g.add((EX["inception"], SCHEMA["director"], EX["nolan"]))
    g.add(
        (EX["nolan"], SCHEMA["name"], Literal("Christopher Nolan", datatype=XSD.string))
    )
    g.add((EX["nolan"], SCHEMA["birthPlace"], EX["london"]))
    g.add((EX["london"], SCHEMA["name"], Literal("London", datatype=XSD.string)))
    return g


class TestDepthControl:
    def test_unlimited_depth(self) -> None:
        """Default (no max_depth) traverses all levels."""
        g = _deep_graph()
        movie = MovieView.from_graph(g, EX["inception"])
        assert movie.director is not None
        assert movie.director.birthPlace is not None
        assert movie.director.birthPlace.name == "London"

    def test_max_depth_zero_skips_nested(self) -> None:
        """max_depth=0 reads no nested models."""
        g = _deep_graph()
        movie = MovieView.from_graph(g, EX["inception"], max_depth=0)
        assert movie.name == "Inception"
        assert movie.director is None

    def test_max_depth_one_reads_first_level(self) -> None:
        """max_depth=1 reads one level of nesting."""
        g = _deep_graph()
        movie = MovieView.from_graph(g, EX["inception"], max_depth=1)
        assert movie.director is not None
        assert movie.director.name == "Christopher Nolan"
        assert movie.director.birthPlace is None

    def test_max_depth_two_reads_all(self) -> None:
        """max_depth=2 is enough for the full chain."""
        g = _deep_graph()
        movie = MovieView.from_graph(g, EX["inception"], max_depth=2)
        assert movie.director is not None
        assert movie.director.birthPlace is not None
        assert movie.director.birthPlace.name == "London"

    def test_depth_with_multi_valued(self) -> None:
        """Depth control works on multi-valued nested fields."""
        ProducerView = _ProducerView

        g = Graph()
        g.add((EX["m"], SCHEMA["name"], Literal("M", datatype=XSD.string)))
        g.add((EX["m"], SCHEMA["productionCompany"], EX["s1"]))
        g.add((EX["s1"], SCHEMA["name"], Literal("Studio One", datatype=XSD.string)))

        # Depth 0 → empty list for nested multi-valued
        movie = ProducerView.from_graph(g, EX["m"], max_depth=0)
        assert movie.studios == []

        # Depth 1 → studios populated
        movie = ProducerView.from_graph(g, EX["m"], max_depth=1)
        assert len(movie.studios) == 1
