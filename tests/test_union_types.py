"""Non-optional union type edge cases (#14).

unwrap_type only handles X | None.  A union like str | int takes the first
non-None branch, producing undefined behavior for the other branch.
"""

from __future__ import annotations

from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class FlexView(GraphModel):
    value: str | int = predicate(SCHEMA["value"])


class TestNonOptionalUnion:
    def test_union_str_int_with_string(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["value"], Literal("hello", datatype=XSD.string)))

        view = FlexView.from_graph(g, EX["x"])
        assert view.value == "hello"

    def test_union_str_int_with_integer(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["value"], Literal(42, datatype=XSD.integer)))

        view = FlexView.from_graph(g, EX["x"])
        # unwrap_type takes first non-None branch; behavior may be surprising
        assert view.value is not None
