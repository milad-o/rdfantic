"""Error-path tests — missing fields, wrong types, empty graphs.

Proves the library handles error conditions gracefully rather than crashing
with opaque errors.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class StrictModel(GraphModel):
    rdf_type = SCHEMA["Thing"]
    name: str = predicate(SCHEMA["name"])
    count: int = predicate(SCHEMA["count"])


class OptionalModel(GraphModel):
    rdf_type = SCHEMA["Thing"]
    name: str = predicate(SCHEMA["name"])
    note: str | None = predicate(SCHEMA["note"])


class TestMissingRequiredFields:
    """Missing required fields should raise Pydantic ValidationError."""

    def test_all_fields_missing(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["other"], Literal("irrelevant")))

        with pytest.raises(ValidationError):
            StrictModel.from_graph(g, EX["x"])

    def test_one_required_missing(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("hello", datatype=XSD.string)))
        # count is missing

        with pytest.raises(ValidationError):
            StrictModel.from_graph(g, EX["x"])

    def test_optional_missing_is_fine(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("hello", datatype=XSD.string)))

        m = OptionalModel.from_graph(g, EX["x"])
        assert m.name == "hello"
        assert m.note is None


class TestEmptyGraph:
    """Reading from an empty graph should fail for required fields."""

    def test_empty_graph_required(self) -> None:
        g = Graph()
        with pytest.raises(ValidationError):
            StrictModel.from_graph(g, EX["x"])

    def test_empty_graph_all_optional(self) -> None:
        class AllOptional(GraphModel):
            a: str | None = predicate(SCHEMA["a"])
            b: int | None = predicate(SCHEMA["b"])

        g = Graph()
        m = AllOptional.from_graph(g, EX["x"])
        assert m.a is None
        assert m.b is None


class TestSubjectNotInGraph:
    """Subject URI not present in graph — same as empty for that subject."""

    def test_wrong_subject(self) -> None:
        g = Graph()
        g.add((EX["y"], SCHEMA["name"], Literal("hello", datatype=XSD.string)))
        g.add((EX["y"], SCHEMA["count"], Literal(5, datatype=XSD.integer)))

        # EX["x"] has no triples
        with pytest.raises(ValidationError):
            StrictModel.from_graph(g, EX["x"])


class TestWriteEdgeCases:
    """Edge cases in to_triples / to_graph / merge."""

    def test_merge_requires_subject(self) -> None:
        m = StrictModel(name="test", count=1)
        with pytest.raises(ValueError, match="requires a subject"):
            m.merge_into_graph(Graph())

    def test_to_triples_with_empty_collection(self) -> None:
        class M(GraphModel):
            tags: set[str] = predicate(SCHEMA["tag"])

        m = M(tags=set())
        triples = m.to_triples(subject=EX["x"])

        # No tag triples should be emitted for empty set
        tag_triples = [(s, p, o) for s, p, o in triples if p == SCHEMA["tag"]]
        assert len(tag_triples) == 0

    def test_to_graph_creates_new_graph(self) -> None:
        m = StrictModel(name="test", count=1)
        g = m.to_graph(subject=EX["x"])

        assert isinstance(g, Graph)
        assert len(g) > 0

    def test_to_graph_adds_to_existing(self) -> None:
        existing = Graph()
        existing.add((EX["other"], SCHEMA["unrelated"], Literal("data")))

        m = StrictModel(name="test", count=1)
        g = m.to_graph(graph=existing, subject=EX["x"])

        assert g is existing
        # Both old and new triples present
        assert (EX["other"], SCHEMA["unrelated"], Literal("data")) in g
        assert len(list(g.objects(EX["x"], SCHEMA["name"]))) == 1
