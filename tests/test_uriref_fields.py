"""URIRef-typed field edge cases (#13).

Probes the read/write behavior when a field is annotated as URIRef rather
than a scalar type.  rdf_value_to_python preserves URIRef when the target
type is URIRef.
"""

from __future__ import annotations

from rdflib import Graph, Namespace, URIRef

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class HomepageView(GraphModel):
    homepage: URIRef | None = predicate(SCHEMA["url"])


class TestURIRefRead:
    def test_uriref_read(self) -> None:
        """Reading a URIRef object should work for a URIRef-typed field."""
        g = Graph()
        g.add((EX["x"], SCHEMA["url"], URIRef("http://example.org/homepage")))

        view = HomepageView.from_graph(g, EX["x"])
        assert view.homepage == URIRef("http://example.org/homepage")
        assert isinstance(view.homepage, URIRef)

    def test_uriref_read_preserves_type(self) -> None:
        """After reading from graph, URIRef field retains the URIRef type."""
        g = Graph()
        g.add((EX["x"], SCHEMA["url"], URIRef("http://example.org/page")))

        view = HomepageView.from_graph(g, EX["x"])
        assert isinstance(view.homepage, URIRef)


class TestURIRefWrite:
    def test_uriref_round_trip_type(self) -> None:
        """Writing a URIRef field should produce a URIRef object, not a Literal."""
        view = HomepageView(homepage=URIRef("http://example.org/homepage"))
        triples = view.to_triples(subject=EX["x"])
        url_triples = [(s, p, o) for s, p, o in triples if p == SCHEMA["url"]]
        assert len(url_triples) == 1
        obj = url_triples[0][2]
        assert isinstance(obj, URIRef), f"Expected URIRef, got {type(obj)}"
