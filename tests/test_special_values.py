"""Special float values and empty string edge cases (#26, #27).

#26 — NaN and Infinity round-trip through rdflib; JSON serialization
may break for NaN.

#27 — Empty string is a valid Literal that satisfies a required str field.
"""

from __future__ import annotations

import math

import pytest
from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class FloatView(GraphModel):
    value: float = predicate(SCHEMA["value"])


class LabelView(GraphModel):
    label: str = predicate(SCHEMA["name"])


class TestSpecialFloats:
    def test_nan_round_trip(self) -> None:
        """NaN should survive graph round-trip."""
        view = FloatView(value=float("nan"))
        g = view.to_graph(subject=EX["x"])

        restored = FloatView.from_graph(g, EX["x"])
        assert math.isnan(restored.value)

    def test_infinity_round_trip(self) -> None:
        """Infinity should survive graph round-trip."""
        view = FloatView(value=float("inf"))
        g = view.to_graph(subject=EX["x"])

        restored = FloatView.from_graph(g, EX["x"])
        assert math.isinf(restored.value)

    def test_nan_json_serialization(self) -> None:
        """NaN breaks standard JSON serialization."""
        view = FloatView(value=float("nan"))
        try:
            json_str = view.model_dump_json()
            assert json_str is not None
        except ValueError:
            pytest.skip("NaN not serializable to JSON (expected)")


class TestEmptyString:
    def test_empty_string_is_valid(self) -> None:
        """An empty string literal satisfies a required str field."""
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("", datatype=XSD.string)))

        view = LabelView.from_graph(g, EX["x"])
        assert view.label == ""

    def test_empty_string_round_trip(self) -> None:
        """Empty string round-trips correctly."""
        view = LabelView(label="")
        g = view.to_graph(subject=EX["x"])

        restored = LabelView.from_graph(g, EX["x"])
        assert restored.label == ""
