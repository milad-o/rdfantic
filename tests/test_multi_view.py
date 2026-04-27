"""Multi-view stress tests — 3+ views on the same node, interleaved read/write.

Proves Claim 6 (view semantics) under realistic concurrent-view conditions.
"""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


# -- Three overlapping views on the same node type -------------------------


class FullMovieView(GraphModel):
    """Wide view: name, year, genres, director."""

    rdf_type = SCHEMA["Movie"]

    name: str = predicate(SCHEMA["name"])
    year: int | None = predicate(SCHEMA["year"])
    genres: set[str] = predicate(SCHEMA["genre"])
    director_name: str | None = predicate(SCHEMA["directorName"])


class TitleOnlyView(GraphModel):
    """Minimal view: just the name."""

    name: str = predicate(SCHEMA["name"])


class CatalogView(GraphModel):
    """Catalog view: name + genres, no year or director."""

    rdf_type = SCHEMA["Movie"]

    name: str = predicate(SCHEMA["name"])
    genres: set[str] = predicate(SCHEMA["genre"])


def _make_movie_graph() -> Graph:
    g = Graph()
    m = EX["inception"]
    g.add((m, RDF.type, SCHEMA["Movie"]))
    g.add((m, SCHEMA["name"], Literal("Inception", datatype=XSD.string)))
    g.add((m, SCHEMA["year"], Literal(2010, datatype=XSD.integer)))
    g.add((m, SCHEMA["genre"], Literal("Sci-Fi", datatype=XSD.string)))
    g.add((m, SCHEMA["genre"], Literal("Thriller", datatype=XSD.string)))
    g.add(
        (m, SCHEMA["directorName"], Literal("Christopher Nolan", datatype=XSD.string))
    )
    g.add((m, SCHEMA["budget"], Literal(160_000_000, datatype=XSD.integer)))
    return g


class TestMultiViewRead:
    """Three views read the same node independently."""

    def test_full_view_reads_all_declared(self) -> None:
        g = _make_movie_graph()
        movie = FullMovieView.from_graph(g, EX["inception"])

        assert movie.name == "Inception"
        assert movie.year == 2010
        assert movie.genres == {"Sci-Fi", "Thriller"}
        assert movie.director_name == "Christopher Nolan"

    def test_title_only_reads_just_name(self) -> None:
        g = _make_movie_graph()
        movie = TitleOnlyView.from_graph(g, EX["inception"])

        assert movie.name == "Inception"
        assert not hasattr(movie, "year")
        assert not hasattr(movie, "genres")

    def test_catalog_view_reads_name_and_genres(self) -> None:
        g = _make_movie_graph()
        movie = CatalogView.from_graph(g, EX["inception"])

        assert movie.name == "Inception"
        assert movie.genres == {"Sci-Fi", "Thriller"}
        assert not hasattr(movie, "year")

    def test_all_three_views_same_node_same_graph(self) -> None:
        """Read the same node with all three views — no interference."""
        g = _make_movie_graph()

        full = FullMovieView.from_graph(g, EX["inception"])
        title = TitleOnlyView.from_graph(g, EX["inception"])
        catalog = CatalogView.from_graph(g, EX["inception"])

        assert full.name == title.name == catalog.name == "Inception"
        assert full.genres == catalog.genres
        assert full.year == 2010


class TestMultiViewWrite:
    """Write through one view, read through another."""

    def test_write_full_read_catalog(self) -> None:
        """Write via FullMovieView, read via CatalogView — catalog fields intact."""
        movie = FullMovieView(
            name="Tenet",
            year=2020,
            genres={"Action", "Sci-Fi"},
            director_name="Christopher Nolan",
        )
        g = movie.to_graph(subject=EX["tenet"])

        catalog = CatalogView.from_graph(g, EX["tenet"])
        assert catalog.name == "Tenet"
        assert catalog.genres == {"Action", "Sci-Fi"}

    def test_write_catalog_read_full_optional_none(self) -> None:
        """Write via CatalogView — fields not in that view read as None/empty."""
        catalog = CatalogView(name="Dune", genres={"Sci-Fi", "Drama"})
        g = catalog.to_graph(subject=EX["dune"])

        full = FullMovieView.from_graph(g, EX["dune"])
        assert full.name == "Dune"
        assert full.genres == {"Sci-Fi", "Drama"}
        assert full.year is None
        assert full.director_name is None

    def test_write_title_only_preserves_nothing_else(self) -> None:
        """TitleOnlyView has no rdf_type, so to_triples emits only the name."""
        title = TitleOnlyView(name="Interstellar")
        triples = title.to_triples(subject=EX["interstellar"])

        preds = {p for _, p, _ in triples}
        assert SCHEMA["name"] in preds
        assert RDF.type not in preds  # no rdf_type on TitleOnlyView


class TestMultiViewMerge:
    """Merge through one view, verify other views' data is untouched."""

    def test_merge_catalog_preserves_year(self) -> None:
        """Merge via CatalogView should not touch year or directorName."""
        g = _make_movie_graph()

        updated_catalog = CatalogView(name="Inception (Updated)", genres={"Sci-Fi"})
        updated_catalog.merge_into_graph(g, subject=EX["inception"])

        # CatalogView fields updated
        catalog = CatalogView.from_graph(g, EX["inception"])
        assert catalog.name == "Inception (Updated)"
        assert catalog.genres == {"Sci-Fi"}

        # Non-catalog fields untouched
        years = list(g.objects(EX["inception"], SCHEMA["year"]))
        assert len(years) == 1
        assert years[0].toPython() == 2010

        director_names = list(g.objects(EX["inception"], SCHEMA["directorName"]))
        assert len(director_names) == 1
        assert str(director_names[0]) == "Christopher Nolan"

        # Budget (undeclared by all views) also untouched
        budgets = list(g.objects(EX["inception"], SCHEMA["budget"]))
        assert len(budgets) == 1

    def test_interleaved_merge_two_views(self) -> None:
        """Merge via two views — last write wins for overlapping fields."""
        g = _make_movie_graph()

        # First merge: update name via CatalogView
        cat = CatalogView(name="Inception v2", genres={"Sci-Fi"})
        cat.merge_into_graph(g, subject=EX["inception"])

        # Second merge: update name + year via FullMovieView
        full = FullMovieView(
            name="Inception v3",
            year=2011,
            genres={"Sci-Fi", "Action"},
            director_name="Nolan",
        )
        full.merge_into_graph(g, subject=EX["inception"])

        # FullMovieView's values win
        result = FullMovieView.from_graph(g, EX["inception"])
        assert result.name == "Inception v3"
        assert result.year == 2011
        assert result.genres == {"Sci-Fi", "Action"}
        assert result.director_name == "Nolan"
