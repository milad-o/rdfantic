"""Tests for remote SPARQL endpoint support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate
from rdfantic.sparql import model_to_construct_for_subject

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    age: int | None = predicate(SCHEMA["age"])


class _EndpointCityView(GraphModel):
    name: str = predicate(SCHEMA["name"])


class _DeepPerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    birthPlace: _EndpointCityView | None = predicate(SCHEMA["birthPlace"])


class TestConstructForSubject:
    def test_binds_subject_iri(self) -> None:
        query = model_to_construct_for_subject(PersonView, EX["alice"])
        assert f"<{EX['alice']}>" in query
        # No unbound ?s variable should remain
        assert "?s " not in query

    def test_still_valid_construct(self) -> None:
        query = model_to_construct_for_subject(PersonView, EX["alice"])
        assert "CONSTRUCT" in query
        assert "WHERE" in query


class TestFromEndpoint:
    def test_from_endpoint_round_trip(self) -> None:
        """Mock the HTTP call and verify from_endpoint reads the result."""
        # Build the RDF/XML that a SPARQL endpoint would return
        g = Graph()
        g.add((EX["alice"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
        g.add((EX["alice"], SCHEMA["age"], Literal(30, datatype=XSD.integer)))
        rdf_xml = g.serialize(format="xml").encode()

        mock_response = MagicMock()
        mock_response.read.return_value = rdf_xml
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            person = PersonView.from_endpoint("http://example.org/sparql", EX["alice"])

        assert person.name == "Alice"
        assert person.age == 30
        assert person.subject == EX["alice"]

    def test_from_endpoint_with_depth(self) -> None:
        """max_depth is forwarded to from_graph."""
        DeepPerson = _DeepPerson

        g = Graph()
        g.add((EX["bob"], SCHEMA["name"], Literal("Bob", datatype=XSD.string)))
        g.add((EX["bob"], SCHEMA["birthPlace"], EX["nyc"]))
        g.add((EX["nyc"], SCHEMA["name"], Literal("NYC", datatype=XSD.string)))
        rdf_xml = g.serialize(format="xml").encode()

        mock_response = MagicMock()
        mock_response.read.return_value = rdf_xml
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            person = DeepPerson.from_endpoint(
                "http://example.org/sparql", EX["bob"], max_depth=0
            )

        assert person.name == "Bob"
        assert person.birthPlace is None
