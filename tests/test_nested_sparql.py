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


class SharedNameView(GraphModel):
    """Parent and child both have a field named 'name'."""

    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    director: InnerView = predicate(SCHEMA["director"])


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

    def test_nested_field_variables_are_scoped(self) -> None:
        """Shared field names across parent/child get distinct SPARQL variables."""
        query = SharedNameView.sparql_construct()
        # Parent's name → ?name, child's name → ?director_name
        assert "?name" in query
        assert "?director_name" in query
        # ?name should NOT appear as the director's object (that would be a collision)
        lines = query.splitlines()
        director_name_lines = [
            ln for ln in lines if "?director" in ln and "schema/name" in ln
        ]
        for ln in director_name_lines:
            assert "?director_name" in ln
