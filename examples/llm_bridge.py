"""LLM bridge — use GraphModel's clean JSON Schema to extract structured
RDF data from LLM output, then validate and write to a graph."""

import json

from rdflib import Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    email: str | None = predicate(SCHEMA["email"])
    job_title: str | None = predicate(SCHEMA["jobTitle"])


# -- JSON Schema for LLM function calling -----------------------------
# The schema has no RDF predicate URIs — clean for LLM consumption.

schema = PersonView.model_json_schema()

print("JSON Schema for LLM:")

print(json.dumps(schema, indent=2))
print()

# Verify no RDF metadata leaked
schema_str = json.dumps(schema)
assert "rdf_predicate" not in schema_str
assert "schema.org" not in schema_str
print("✓ No RDF metadata in JSON Schema — safe for LLM function calling")
print()

# -- Simulate LLM output → validate → write to graph ------------------
# In a real pipeline, this JSON would come from an LLM API response.

llm_output = {
    "name": "Alice Johnson",
    "email": "alice@example.org",
    "job_title": "Data Scientist",
}

# Validate with Pydantic (catches type errors, missing required fields)
person = PersonView.model_validate(llm_output)
print(f"Validated: {person.name} ({person.job_title})")

# Write to graph
g = person.to_graph(subject=EX["alice"])
print(f"\nTriples written: {len(g)}")
for _s, p, o in sorted(g):
    print(f"  {p} → {o}")

# -- Round-trip: read back from graph ----------------------------------

person2 = PersonView.from_graph(g, EX["alice"])
assert person2.name == person.name
assert person2.email == person.email
assert person2.job_title == person.job_title
print("\n✓ LLM output → Pydantic → RDF graph → Pydantic round-trip OK")
