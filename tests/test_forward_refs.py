"""Forward reference resolution edge cases (#29).

get_type_hints(cls) must resolve string annotations.  This tests
self-referencing models that use forward refs within the same module.
"""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class ChainView(GraphModel):
    rdf_type = SCHEMA["Node"]
    name: str = predicate(SCHEMA["name"])
    next_node: ChainView | None = predicate(SCHEMA["next"])


class TestForwardRefs:
    def test_string_forward_ref_same_module(self) -> None:
        """Forward reference within the same module resolves fine."""
        g = Graph()
        g.add((EX["a"], RDF.type, SCHEMA["Node"]))
        g.add((EX["a"], SCHEMA["name"], Literal("A", datatype=XSD.string)))

        view = ChainView.from_graph(g, EX["a"])
        assert view.name == "A"
        assert view.next_node is None
