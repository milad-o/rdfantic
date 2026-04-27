"""Tests for SPARQL CONSTRUCT query generation."""

from __future__ import annotations

from rdflib import Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]

    name: str = predicate(SCHEMA["name"])


class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]

    name: str = predicate(SCHEMA["name"])
    director: PersonView = predicate(SCHEMA["director"])
    genres: set[str] = predicate(SCHEMA["genre"])
    year: int | None = predicate(SCHEMA["year"])


class TestSPARQLConstruct:
    def test_construct_contains_keyword(self) -> None:
        query = MovieView.sparql_construct()
        assert "CONSTRUCT" in query
        assert "WHERE" in query

    def test_rdf_type_in_query(self) -> None:
        query = MovieView.sparql_construct()
        assert str(SCHEMA["Movie"]) in query

    def test_required_field_not_optional(self) -> None:
        query = MovieView.sparql_construct()
        # name is required — should appear in WHERE but not wrapped in OPTIONAL
        lines = query.split("\n")
        where_start = next(i for i, line in enumerate(lines) if "WHERE" in line)
        where_lines = lines[where_start:]
        name_lines = [
            line
            for line in where_lines
            if "name" in line.lower() and "schema.org" in line
        ]
        assert len(name_lines) > 0
        # Required fields should NOT be in OPTIONAL blocks
        for line in name_lines:
            assert "OPTIONAL" not in line

    def test_optional_field_in_optional_block(self) -> None:
        query = MovieView.sparql_construct()
        assert "OPTIONAL" in query
        # year is optional — should be in OPTIONAL
        lines = query.split("\n")
        optional_lines = [
            line for line in lines if "OPTIONAL" in line and "year" in line
        ]
        assert len(optional_lines) > 0

    def test_multi_valued_field_in_optional_block(self) -> None:
        query = MovieView.sparql_construct()
        lines = query.split("\n")
        optional_lines = [
            line for line in lines if "OPTIONAL" in line and "genre" in line
        ]
        assert len(optional_lines) > 0

    def test_custom_subject_variable(self) -> None:
        query = MovieView.sparql_construct(subject_var="movie")
        assert "?movie" in query
        assert "?s " not in query
