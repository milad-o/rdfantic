"""Simple benchmark — read/write 1000+ nodes to establish a baseline.

Not a pass/fail correctness test — measures that bulk operations complete
in a reasonable time and don't degrade catastrophically.
"""

from __future__ import annotations

import time

from rdflib import XSD, Graph, Literal, Namespace, URIRef

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class BenchPerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    age: int | None = predicate(SCHEMA["age"])
    tags: set[str] = predicate(SCHEMA["tag"])


NODE_COUNT = 1_000


def _build_graph(n: int) -> Graph:
    """Build a graph with n Person nodes, each with 3 tags."""
    g = Graph()
    for i in range(n):
        subj = URIRef(f"{EX}person/{i}")
        g.add((subj, URIRef(str(SCHEMA["type"])), SCHEMA["Person"]))
        g.add((subj, SCHEMA["name"], Literal(f"Person {i}", datatype=XSD.string)))
        g.add((subj, SCHEMA["age"], Literal(20 + (i % 60), datatype=XSD.integer)))
        for t in ("a", "b", "c"):
            g.add((subj, SCHEMA["tag"], Literal(f"tag-{t}", datatype=XSD.string)))
    return g


class TestBulkWrite:
    """Write 1000 model instances to a graph."""

    def test_bulk_write_completes(self) -> None:
        g = Graph()
        start = time.perf_counter()

        for i in range(NODE_COUNT):
            p = BenchPerson(name=f"Person {i}", age=20 + (i % 60), tags={"a", "b", "c"})
            p.to_graph(graph=g, subject=URIRef(f"{EX}person/{i}"))

        elapsed = time.perf_counter() - start

        # Sanity: all nodes written
        assert len(list(g.subjects(SCHEMA["name"]))) == NODE_COUNT
        # Should complete in under 30 seconds (generous — usually < 2s)
        assert elapsed < 30, f"Bulk write took {elapsed:.1f}s"


class TestBulkRead:
    """Read 1000 model instances from a pre-built graph."""

    def test_bulk_read_completes(self) -> None:
        g = _build_graph(NODE_COUNT)
        subjects = [URIRef(f"{EX}person/{i}") for i in range(NODE_COUNT)]

        start = time.perf_counter()
        results = [BenchPerson.from_graph(g, s) for s in subjects]
        elapsed = time.perf_counter() - start

        assert len(results) == NODE_COUNT
        assert all(r.name.startswith("Person") for r in results)
        assert all(len(r.tags) == 3 for r in results)
        assert elapsed < 30, f"Bulk read took {elapsed:.1f}s"


class TestBulkRoundTrip:
    """Write 1000 nodes, read them all back, verify fidelity."""

    def test_bulk_round_trip(self) -> None:
        g = Graph()
        originals = []

        for i in range(NODE_COUNT):
            p = BenchPerson(name=f"Person {i}", age=20 + (i % 60), tags={"x", "y"})
            p.to_graph(graph=g, subject=URIRef(f"{EX}person/{i}"))
            originals.append(p)

        for i, orig in enumerate(originals):
            restored = BenchPerson.from_graph(g, URIRef(f"{EX}person/{i}"))
            assert restored.name == orig.name
            assert restored.age == orig.age
            assert restored.tags == orig.tags
