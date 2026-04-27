"""Remote SPARQL endpoint edge case tests.

Extends the base endpoint tests with error handling, empty results,
and malformed responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from xml.sax import SAXParseException

import pytest
from pydantic import ValidationError
from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import EndpointError, GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    age: int | None = predicate(SCHEMA["age"])


def _mock_response(content: bytes) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = content
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestEndpointEmptyResult:
    """Endpoint returns valid RDF but no matching triples."""

    def test_empty_graph_raises_validation_error(self) -> None:
        """Empty CONSTRUCT result → no triples → required field missing."""
        empty_graph = Graph()
        rdf_xml = empty_graph.serialize(format="xml").encode()

        with (
            patch("urllib.request.urlopen", return_value=_mock_response(rdf_xml)),
            pytest.raises(ValidationError),
        ):
            PersonView.from_endpoint("http://example.org/sparql", EX["nobody"])

    def test_partial_data_optional_none(self) -> None:
        """Endpoint returns only some fields — optional ones are None."""
        g = Graph()
        g.add((EX["alice"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
        rdf_xml = g.serialize(format="xml").encode()

        with patch("urllib.request.urlopen", return_value=_mock_response(rdf_xml)):
            person = PersonView.from_endpoint("http://example.org/sparql", EX["alice"])

        assert person.name == "Alice"
        assert person.age is None


class TestEndpointHTTPErrors:
    """Network and HTTP error conditions."""

    def test_http_404_raises(self) -> None:
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=HTTPError(
                    "http://example.org/sparql", 404, "Not Found", {}, None
                ),
            ),
            pytest.raises(EndpointError),
        ):
            PersonView.from_endpoint("http://example.org/sparql", EX["alice"])

    def test_http_500_raises(self) -> None:
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=HTTPError(
                    "http://example.org/sparql",
                    500,
                    "Internal Server Error",
                    {},
                    None,
                ),
            ),
            pytest.raises(EndpointError),
        ):
            PersonView.from_endpoint("http://example.org/sparql", EX["alice"])

    def test_connection_refused_raises(self) -> None:
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=URLError("Connection refused"),
            ),
            pytest.raises(EndpointError),
        ):
            PersonView.from_endpoint("http://localhost:9999/sparql", EX["alice"])


class TestEndpointMalformedResponse:
    """Endpoint returns non-RDF content."""

    def test_html_response_raises(self) -> None:
        html = b"<html><body>Not SPARQL</body></html>"
        with (
            patch("urllib.request.urlopen", return_value=_mock_response(html)),
            pytest.raises(ValidationError),
        ):
            PersonView.from_endpoint("http://example.org/sparql", EX["alice"])

    def test_empty_bytes_raises(self) -> None:
        with (
            patch("urllib.request.urlopen", return_value=_mock_response(b"")),
            pytest.raises(SAXParseException),
        ):
            PersonView.from_endpoint("http://example.org/sparql", EX["alice"])
