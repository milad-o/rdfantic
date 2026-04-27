"""Deep nesting without cycles (#25).

Tests long chains of nested models to probe recursion depth limits
when max_depth is None.
"""

from __future__ import annotations

import sys

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class ChainView(GraphModel):
    rdf_type = SCHEMA["Node"]
    name: str = predicate(SCHEMA["name"])
    next_node: ChainView | None = predicate(SCHEMA["next"])


def _chain_graph(depth: int) -> Graph:
    g = Graph()
    for i in range(depth):
        subj = EX[f"node{i}"]
        g.add((subj, RDF.type, SCHEMA["Node"]))
        g.add((subj, SCHEMA["name"], Literal(f"Node-{i}", datatype=XSD.string)))
        if i < depth - 1:
            g.add((subj, SCHEMA["next"], EX[f"node{i + 1}"]))
    return g


class TestDeepNesting:
    def test_deep_chain_with_depth_limit(self) -> None:
        """Deep chain with explicit depth limit should work fine."""
        g = _chain_graph(50)
        view = ChainView.from_graph(g, EX["node0"], max_depth=10)
        assert view.name == "Node-0"

    def test_deep_chain_unlimited_depth(self) -> None:
        """200-level chain with unlimited depth — may approach recursion limit."""
        g = _chain_graph(200)

        old_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(1000)
            view = ChainView.from_graph(g, EX["node0"])
            assert view.name == "Node-0"
        finally:
            sys.setrecursionlimit(old_limit)
