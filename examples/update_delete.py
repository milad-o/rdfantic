"""Update and delete — modify a node's model-declared predicates without
touching other triples on that node."""

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    email: str | None = predicate(SCHEMA["email"])


# -- Set up a graph with extra triples we don't want to lose -----------

g = Graph()
g.add((EX["alice"], RDF.type, SCHEMA["Person"]))
g.add((EX["alice"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
g.add((EX["alice"], SCHEMA["email"], Literal("alice@old.com", datatype=XSD.string)))

# This triple is NOT part of PersonView — it should survive updates
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
g.add((EX["alice"], FOAF["age"], Literal(30, datatype=XSD.integer)))

print(f"Before update: {len(g)} triples")
for _s, p, o in sorted(g):
    print(f"  {p.split('/')[-1] if '/' in p else p.split('#')[-1]} = {o}")

# -- Update: change name and remove email ------------------------------

updated = PersonView(name="Alice Smith", email=None)
updated.merge_into_graph(g, subject=EX["alice"])

print(f"\nAfter update: {len(g)} triples")
for _s, p, o in sorted(g):
    print(f"  {p.split('/')[-1] if '/' in p else p.split('#')[-1]} = {o}")

# foaf:age should still be there
assert any(p == FOAF["age"] for _, p, _ in g.triples((EX["alice"], None, None)))
print("\n✓ foaf:age survived the update")

# -- Delete: remove only PersonView predicates -------------------------

PersonView.remove_from_graph(g, subject=EX["alice"])

print(f"\nAfter delete: {len(g)} triples")
for _s, p, o in sorted(g):
    print(f"  {p.split('/')[-1] if '/' in p else p.split('#')[-1]} = {o}")

# foaf:age should STILL be there
assert any(p == FOAF["age"] for _, p, _ in g.triples((EX["alice"], None, None)))
print("\n✓ foaf:age survived the delete — open-world safety works")
