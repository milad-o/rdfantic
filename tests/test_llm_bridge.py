"""Tests for the LLM extraction bridge pipeline.

Verifies that one GraphModel definition serves as both an LLM extraction schema
(via Pydantic's model_json_schema) and a graph schema (via to_triples + to_shacl).
"""

from __future__ import annotations

from typing import Annotated

import pytest
from rdflib import XSD, Graph, Namespace

from rdfantic import GraphModel, SHConstraint, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class PersonExtract(GraphModel):
    rdf_type = SCHEMA["Person"]

    name: str = predicate(SCHEMA["name"])
    age: int | None = predicate(SCHEMA["age"])


class MovieExtract(GraphModel):
    rdf_type = SCHEMA["Movie"]

    name: str = predicate(SCHEMA["name"])
    genres: set[str] = predicate(SCHEMA["genre"])
    year: Annotated[int | None, SHConstraint(datatype=XSD.nonNegativeInteger)] = (
        predicate(SCHEMA["year"])
    )


class TestJSONSchema:
    """model_json_schema() should produce clean JSON Schema without RDF internals."""

    def test_schema_has_properties(self) -> None:
        schema = MovieExtract.model_json_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "genres" in schema["properties"]
        assert "year" in schema["properties"]

    def test_schema_has_no_rdf_predicate(self) -> None:
        """Internal rdf_predicate metadata must not leak into JSON Schema."""
        schema = MovieExtract.model_json_schema()
        schema_str = str(schema)
        assert "rdf_predicate" not in schema_str

    def test_schema_types_correct(self) -> None:
        schema = MovieExtract.model_json_schema()
        props = schema["properties"]
        assert props["name"]["type"] == "string"

    def test_required_fields_listed(self) -> None:
        schema = MovieExtract.model_json_schema()
        assert "name" in schema.get("required", [])
        assert "genres" in schema.get("required", [])


class TestLLMPipeline:
    """End-to-end: simulate LLM JSON → validate → triples → SHACL check."""

    def test_validate_and_write(self) -> None:
        """Simulate an LLM returning JSON, validate it, write to graph."""
        llm_response = {
            "name": "Inception",
            "genres": ["Sci-Fi", "Thriller"],
            "year": 2010,
        }

        movie = MovieExtract.model_validate(llm_response)
        assert movie.name == "Inception"
        assert movie.genres == {"Sci-Fi", "Thriller"}

        g = movie.to_graph(subject=EX["inception"])
        assert len(g) > 0

    def test_full_pipeline_with_shacl(self) -> None:
        """Full loop: LLM JSON → Pydantic → Graph → SHACL validation."""
        pyshacl = pytest.importorskip("pyshacl")

        llm_response = {
            "name": "Inception",
            "genres": ["Sci-Fi", "Thriller"],
            "year": 2010,
        }

        movie = MovieExtract.model_validate(llm_response)
        data_graph = movie.to_graph(subject=EX["inception"])
        shacl_graph = MovieExtract.to_shacl()

        conforms, _, _ = pyshacl.validate(
            data_graph,
            shacl_graph=shacl_graph,
        )
        assert conforms

    def test_invalid_data_fails_shacl(self) -> None:
        """Graph with missing required field should fail SHACL validation."""
        pyshacl = pytest.importorskip("pyshacl")

        from rdflib import RDF, Literal

        # Build a graph manually missing the required 'name' field
        data_graph = Graph()
        data_graph.add((EX["bad"], RDF.type, SCHEMA["Movie"]))
        data_graph.add((EX["bad"], SCHEMA["genre"], Literal("Drama")))

        shacl_graph = MovieExtract.to_shacl()
        conforms, _, _ = pyshacl.validate(
            data_graph,
            shacl_graph=shacl_graph,
        )
        assert not conforms

    def test_nested_model_pipeline(self) -> None:
        """Nested models in LLM extraction still round-trip correctly."""

        class DirectedMovieExtract(GraphModel):
            rdf_type = SCHEMA["Movie"]

            name: str = predicate(SCHEMA["name"])
            director: PersonExtract = predicate(SCHEMA["director"])

        llm_response = {
            "name": "Inception",
            "director": {"name": "Christopher Nolan", "age": 55},
        }

        movie = DirectedMovieExtract.model_validate(llm_response)
        assert movie.director.name == "Christopher Nolan"

        g = movie.to_graph(subject=EX["inception"])
        assert len(g) > 0

        # Read it back
        restored = DirectedMovieExtract.from_graph(g, EX["inception"])
        assert restored.name == "Inception"
        assert restored.director.name == "Christopher Nolan"
        assert restored.director.age == 55
