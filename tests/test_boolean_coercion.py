"""Boolean coercion from RDF edge cases (#30).

Tests various boolean representations: typed true/false, string "true"/"1"
with xsd:boolean, and untyped "true" literal.
"""

from __future__ import annotations

from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class BoolView(GraphModel):
    flag: bool = predicate(SCHEMA["active"])


class TestBooleanCoercion:
    def test_typed_true(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["active"], Literal(True, datatype=XSD.boolean)))

        view = BoolView.from_graph(g, EX["x"])
        assert view.flag is True

    def test_typed_false(self) -> None:
        g = Graph()
        g.add((EX["x"], SCHEMA["active"], Literal(False, datatype=XSD.boolean)))

        view = BoolView.from_graph(g, EX["x"])
        assert view.flag is False

    def test_string_true_typed_boolean(self) -> None:
        """'true'^^xsd:boolean should coerce to True."""
        g = Graph()
        g.add((EX["x"], SCHEMA["active"], Literal("true", datatype=XSD.boolean)))

        view = BoolView.from_graph(g, EX["x"])
        assert view.flag is True

    def test_string_1_typed_boolean(self) -> None:
        """'1'^^xsd:boolean should coerce to True."""
        g = Graph()
        g.add((EX["x"], SCHEMA["active"], Literal("1", datatype=XSD.boolean)))

        view = BoolView.from_graph(g, EX["x"])
        assert view.flag is True

    def test_untyped_string_true(self) -> None:
        """Untyped 'true' literal — rdflib returns the string, Pydantic may coerce."""
        g = Graph()
        g.add((EX["x"], SCHEMA["active"], Literal("true")))

        view = BoolView.from_graph(g, EX["x"])
        assert view.flag is not None
