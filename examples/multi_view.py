"""Multi-view — two different models reading the same RDF node,
demonstrating that a GraphModel is a lens, not a table."""

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


# -- Two different views of a Person -----------------------------------


class ContactCard(GraphModel):
    """Minimal view: just name and email."""

    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    email: str | None = predicate(SCHEMA["email"])


class SocialProfile(GraphModel):
    """Different view: name and social connections."""

    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    knows: list[str] = predicate(SCHEMA["knows"])


# -- Build a graph with data for both views ----------------------------

g = Graph()
g.add((EX["alice"], RDF.type, SCHEMA["Person"]))
g.add((EX["alice"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
g.add((EX["alice"], SCHEMA["email"], Literal("alice@example.org", datatype=XSD.string)))
g.add((EX["alice"], SCHEMA["knows"], Literal("Bob", datatype=XSD.string)))
g.add((EX["alice"], SCHEMA["knows"], Literal("Carol", datatype=XSD.string)))
# Extra triple that neither view declares — silently ignored by both
g.add((EX["alice"], SCHEMA["birthDate"], Literal("1990-01-15", datatype=XSD.date)))

# -- Read the same node through both views -----------------------------

card = ContactCard.from_graph(g, EX["alice"])
profile = SocialProfile.from_graph(g, EX["alice"])

print("ContactCard view:")
print(f"  name:  {card.name}")
print(f"  email: {card.email}")
print()
print("SocialProfile view:")
print(f"  name:  {profile.name}")
print(f"  knows: {profile.knows}")
print()

# -- Each view only sees its own fields --------------------------------

assert not hasattr(card, "knows")
assert not hasattr(profile, "email")
print("✓ Each view only exposes its declared fields")
print("✓ schema:birthDate was ignored by both — open-world semantics")
