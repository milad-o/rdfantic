"""Scalar field ambiguity edge cases (#16, #17).

#16 — Multiple RDF objects for a scalar field: from_graph silently picks
objects[0] with no warning and no deterministic ordering.

#17 — Two fields mapped to the same predicate URI: no guard against this,
causes duplicate triples on write and ambiguous reads.
"""

from __future__ import annotations

from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class LabelView(GraphModel):
    label: str = predicate(SCHEMA["name"])


class DuplicatePredView(GraphModel):
    name_a: str = predicate(SCHEMA["name"])
    name_b: str = predicate(SCHEMA["name"])


class TestMultipleObjectsScalarField:
    def test_scalar_picks_one_silently(self) -> None:
        """Multiple values for a scalar field — first one wins, no warning."""
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
        g.add((EX["x"], SCHEMA["name"], Literal("Bob", datatype=XSD.string)))
        g.add((EX["x"], SCHEMA["name"], Literal("Carol", datatype=XSD.string)))

        view = LabelView.from_graph(g, EX["x"])
        assert view.label in {"Alice", "Bob", "Carol"}


class TestDuplicatePredicateFields:
    def test_read_same_predicate_two_fields(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("Hello", datatype=XSD.string)))

        view = DuplicatePredView.from_graph(g, EX["x"])
        assert view.name_a == "Hello"
        assert view.name_b == "Hello"

    def test_write_same_predicate_duplicates(self) -> None:
        """Writing two fields with same predicate emits duplicate triples."""
        view = DuplicatePredView(name_a="A", name_b="B")
        triples = view.to_triples(subject=EX["x"])
        name_triples = [(s, p, o) for s, p, o in triples if p == SCHEMA["name"]]
        assert len(name_triples) == 2
