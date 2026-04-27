"""Shared fixtures for rdfantic tests."""

from __future__ import annotations

import pytest
from rdflib import XSD, Graph, Literal, Namespace, URIRef

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


@pytest.fixture
def movie_graph() -> Graph:
    """A small graph with one movie and one person."""
    g = Graph()
    movie = EX["inception"]
    director = EX["nolan"]

    g.add((movie, URIRef(str(SCHEMA["type"])), SCHEMA["Movie"]))
    g.add((movie, SCHEMA["name"], Literal("Inception", datatype=XSD.string)))
    g.add((movie, SCHEMA["director"], director))
    g.add((movie, SCHEMA["genre"], Literal("Sci-Fi", datatype=XSD.string)))
    g.add((movie, SCHEMA["genre"], Literal("Thriller", datatype=XSD.string)))
    g.add((movie, SCHEMA["year"], Literal(2010, datatype=XSD.integer)))

    g.add((director, SCHEMA["name"], Literal("Christopher Nolan", datatype=XSD.string)))

    return g
