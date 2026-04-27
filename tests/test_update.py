"""Tests for update/delete semantics (merge_into_graph, remove_from_graph)."""

from __future__ import annotations

import pytest
from rdflib import RDF, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    age: int | None = predicate(SCHEMA["age"])


class TestRemoveFromGraph:
    def test_removes_declared_predicates(self) -> None:
        g = Graph()
        g.add((EX["alice"], RDF.type, SCHEMA["Person"]))
        g.add((EX["alice"], SCHEMA["name"], Literal("Alice")))
        g.add((EX["alice"], SCHEMA["age"], Literal(30)))
        g.add((EX["alice"], SCHEMA["email"], Literal("alice@example.com")))

        PersonView.remove_from_graph(g, EX["alice"])

        # Declared predicates removed
        assert (EX["alice"], SCHEMA["name"], None) not in g
        assert (EX["alice"], SCHEMA["age"], None) not in g
        assert (EX["alice"], RDF.type, SCHEMA["Person"]) not in g

        # Undeclared predicates preserved
        assert (EX["alice"], SCHEMA["email"], Literal("alice@example.com")) in g

    def test_remove_is_safe_on_missing_subject(self) -> None:
        g = Graph()
        PersonView.remove_from_graph(g, EX["nobody"])
        assert len(g) == 0


class TestMergeIntoGraph:
    def test_replaces_declared_triples(self) -> None:
        g = Graph()
        g.add((EX["bob"], RDF.type, SCHEMA["Person"]))
        g.add((EX["bob"], SCHEMA["name"], Literal("Robert")))
        g.add((EX["bob"], SCHEMA["age"], Literal(25)))
        g.add((EX["bob"], SCHEMA["email"], Literal("bob@example.com")))

        updated = PersonView(name="Bob", age=26)
        updated.merge_into_graph(g, subject=EX["bob"])

        # Updated values
        names = list(g.objects(EX["bob"], SCHEMA["name"]))
        assert len(names) == 1
        assert str(names[0]) == "Bob"

        ages = list(g.objects(EX["bob"], SCHEMA["age"]))
        assert len(ages) == 1
        assert ages[0].toPython() == 26

        # rdf:type restored
        assert (EX["bob"], RDF.type, SCHEMA["Person"]) in g

        # Undeclared predicates untouched
        assert (EX["bob"], SCHEMA["email"], Literal("bob@example.com")) in g

    def test_merge_uses_instance_subject(self) -> None:
        g = Graph()
        g.add((EX["carol"], SCHEMA["name"], Literal("Carol Old")))

        carol = PersonView.from_graph(g, EX["carol"])
        updated = PersonView(name="Carol New", age=None)
        updated._subject = carol.subject
        updated.merge_into_graph(g)

        names = list(g.objects(EX["carol"], SCHEMA["name"]))
        assert len(names) == 1
        assert str(names[0]) == "Carol New"

    def test_merge_requires_subject(self) -> None:
        p = PersonView(name="Nobody", age=None)
        with pytest.raises(ValueError, match="requires a subject"):
            p.merge_into_graph(Graph())

    def test_merge_optional_none_removes_old(self) -> None:
        """Setting an optional field to None should remove the old triple."""
        g = Graph()
        g.add((EX["dan"], SCHEMA["name"], Literal("Dan")))
        g.add((EX["dan"], SCHEMA["age"], Literal(40)))

        updated = PersonView(name="Dan", age=None)
        updated.merge_into_graph(g, subject=EX["dan"])

        ages = list(g.objects(EX["dan"], SCHEMA["age"]))
        assert len(ages) == 0
