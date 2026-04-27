"""Pagination with mixed node types (#24).

sorted() on a mix of URIRef and BNode subjects — verifies that rdflib's
comparison operators handle the mixed case without crashing.
"""

from __future__ import annotations

from rdflib import RDF, XSD, BNode, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate
from rdfantic.pagination import paginate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class SimpleView(GraphModel):
    rdf_type = SCHEMA["Thing"]
    name: str = predicate(SCHEMA["name"])


class TestPaginationMixedNodes:
    def test_mixed_bnode_uriref_pagination(self) -> None:
        """paginate() with both URIRef and BNode subjects."""
        g = Graph()
        for i in range(3):
            subj = EX[f"thing{i}"]
            g.add((subj, RDF.type, SCHEMA["Thing"]))
            g.add((subj, SCHEMA["name"], Literal(f"URI-{i}", datatype=XSD.string)))

        for i in range(2):
            subj = BNode()
            g.add((subj, RDF.type, SCHEMA["Thing"]))
            g.add((subj, SCHEMA["name"], Literal(f"BNode-{i}", datatype=XSD.string)))

        page = paginate(SimpleView, g, offset=0, limit=10)
        assert page.total == 5
        assert len(page.items) == 5
