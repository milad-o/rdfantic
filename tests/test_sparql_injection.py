"""SPARQL injection edge case (#21).

_sparql_uri rejects URIs containing characters illegal in SPARQL IRI
references, preventing query structure breakage.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef

from rdfantic.sparql import _sparql_uri


class TestSparqlUriSanitization:
    def test_malformed_uri_raises(self) -> None:
        """A URI containing '>' is rejected with ValueError."""
        malicious = URIRef("http://example.org/foo> . DROP ALL #")
        with pytest.raises(ValueError, match="illegal in SPARQL IRI"):
            _sparql_uri(malicious)

    def test_backslash_rejected(self) -> None:
        with pytest.raises(ValueError, match="illegal in SPARQL IRI"):
            _sparql_uri(URIRef("http://example.org/a\\b"))

    def test_pipe_rejected(self) -> None:
        with pytest.raises(ValueError, match="illegal in SPARQL IRI"):
            _sparql_uri(URIRef("http://example.org/a|b"))

    def test_whitespace_rejected(self) -> None:
        with pytest.raises(ValueError, match="illegal in SPARQL IRI"):
            _sparql_uri(URIRef("http://example.org/a b"))

    def test_valid_uri_passes(self) -> None:
        result = _sparql_uri(URIRef("http://example.org/valid"))
        assert result == "<http://example.org/valid>"
