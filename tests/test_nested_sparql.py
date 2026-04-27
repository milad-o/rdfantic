"""Nested SPARQL CONSTRUCT (#15).

model_to_construct recursively includes triple patterns for nested
GraphModel fields so that the CONSTRUCT query retrieves their data too.
"""

from __future__ import annotations

from rdflib import Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")


class InnerView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])


class OuterView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    title: str = predicate(SCHEMA["name"])
    director: InnerView = predicate(SCHEMA["director"])


class SelfRefView(GraphModel):
    rdf_type = SCHEMA["Node"]
    label: str = predicate(SCHEMA["label"])
    next_node: SelfRefView | None = predicate(SCHEMA["next"])


class TestNestedSparqlConstruct:
    def test_construct_includes_nested_fields(self) -> None:
        """CONSTRUCT query includes patterns for the nested model's fields."""
        query = OuterView.sparql_construct()
        # The nested model's name pattern should appear, using ?director as subject
        assert "?director" in query
        # The nested model's rdf:type should appear
        assert SCHEMA["Person"] in query

    def test_self_referencing_model_terminates(self) -> None:
        """Self-referencing model doesn't cause infinite recursion."""
        query = SelfRefView.sparql_construct()
        assert "?next_node" in query
        assert SCHEMA["Node"] in query
