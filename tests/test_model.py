"""Tests for GraphModel read/write round-tripping."""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


# -- Test models ----------------------------------------------------------


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    namespace = EX

    name: str = predicate(SCHEMA["name"])


class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    namespace = EX

    name: str = predicate(SCHEMA["name"])
    director: PersonView = predicate(SCHEMA["director"])
    genres: set[str] = predicate(SCHEMA["genre"])
    year: int | None = predicate(SCHEMA["year"])


# -- Tests: from_graph (read) ---------------------------------------------


class TestFromGraph:
    def test_read_scalar_fields(self, movie_graph: Graph) -> None:
        movie = MovieView.from_graph(movie_graph, EX["inception"])

        assert movie.name == "Inception"
        assert movie.year == 2010

    def test_read_multi_valued_field(self, movie_graph: Graph) -> None:
        movie = MovieView.from_graph(movie_graph, EX["inception"])

        assert movie.genres == {"Sci-Fi", "Thriller"}

    def test_read_nested_model(self, movie_graph: Graph) -> None:
        movie = MovieView.from_graph(movie_graph, EX["inception"])

        assert isinstance(movie.director, PersonView)
        assert movie.director.name == "Christopher Nolan"

    def test_subject_preserved(self, movie_graph: Graph) -> None:
        movie = MovieView.from_graph(movie_graph, EX["inception"])

        assert movie.subject == EX["inception"]

    def test_optional_field_missing(self) -> None:
        g = Graph()
        g.add((EX["m1"], SCHEMA["name"], Literal("No Year", datatype=XSD.string)))
        g.add((EX["m1"], SCHEMA["genre"], Literal("Drama", datatype=XSD.string)))
        g.add((EX["m1"], SCHEMA["director"], EX["someone"]))
        g.add((EX["someone"], SCHEMA["name"], Literal("Someone", datatype=XSD.string)))

        movie = MovieView.from_graph(g, EX["m1"])
        assert movie.year is None

    def test_extra_triples_ignored(self, movie_graph: Graph) -> None:
        """Open World: extra predicates on the node don't cause errors."""
        movie_graph.add((EX["inception"], SCHEMA["budget"], Literal(160_000_000)))

        movie = MovieView.from_graph(movie_graph, EX["inception"])
        assert movie.name == "Inception"

    def test_multi_view_same_node(self, movie_graph: Graph) -> None:
        """Two different views can project the same node differently."""

        class MinimalMovieView(GraphModel):
            name: str = predicate(SCHEMA["name"])

        movie = MinimalMovieView.from_graph(movie_graph, EX["inception"])
        assert movie.name == "Inception"
        assert not hasattr(movie, "director")


# -- Tests: to_triples / to_graph (write) ---------------------------------


class TestToTriples:
    def test_round_trip(self, movie_graph: Graph) -> None:
        """Read from graph, write back, read again — should produce same data."""
        original = MovieView.from_graph(movie_graph, EX["inception"])
        triples = original.to_triples(subject=EX["inception"])

        new_graph = Graph()
        for t in triples:
            new_graph.add(t)

        restored = MovieView.from_graph(new_graph, EX["inception"])

        assert restored.name == original.name
        assert restored.year == original.year
        assert restored.genres == original.genres
        assert restored.director.name == original.director.name

    def test_rdf_type_triple_emitted(self) -> None:
        person = PersonView(name="Alice")
        triples = person.to_triples(subject=EX["alice"])

        type_triples = [(s, p, o) for s, p, o in triples if p == RDF.type]
        assert len(type_triples) == 1
        assert type_triples[0][2] == SCHEMA["Person"]

    def test_to_graph_returns_graph(self) -> None:
        person = PersonView(name="Bob")
        g = person.to_graph(subject=EX["bob"])

        assert isinstance(g, Graph)
        assert (EX["bob"], SCHEMA["name"], Literal("Bob", datatype=XSD.string)) in g

    def test_optional_none_omitted(self) -> None:
        class OptModel(GraphModel):
            val: int | None = predicate(SCHEMA["val"])

        m = OptModel(val=None)
        triples = m.to_triples(subject=EX["x"])
        pred_triples = [(s, p, o) for s, p, o in triples if p == SCHEMA["val"]]
        assert len(pred_triples) == 0

    def test_blank_node_subject_when_none(self) -> None:
        from rdflib import BNode

        person = PersonView(name="Anon")
        triples = person.to_triples()

        assert len(triples) > 0
        assert isinstance(triples[0][0], BNode)
