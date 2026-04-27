"""LLM extraction bridge — the full pipeline from the design doc:

1. Generate JSON Schema from GraphModel → send to LLM as response_format
2. LLM extracts structured data from unstructured text
3. Validate with Pydantic → write to RDF graph
4. Validate the graph with SHACL shapes generated from the same model

One model definition drives the entire pipeline. No glue code.

Requires:
    pip install rdfantic[shacl] openai python-dotenv
    Set OPENAI_API_KEY in .env or environment.
"""

import json
import os
from typing import Annotated

from dotenv import load_dotenv
from openai import OpenAI
from rdflib import Namespace

from rdfantic import GraphModel, SHConstraint, predicate

load_dotenv()

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")

# -- Step 0: Define the model (once) ----------------------------------


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: Annotated[str, SHConstraint(min_length=1, max_length=200)] = predicate(
        SCHEMA["name"]
    )
    email: str | None = predicate(SCHEMA["email"])
    job_title: str | None = predicate(SCHEMA["jobTitle"])
    employer: str | None = predicate(SCHEMA["worksFor"])


# -- Step 1: JSON Schema for the LLM ----------------------------------

schema = PersonView.model_json_schema()

# Verify no RDF metadata leaked into the schema
schema_str = json.dumps(schema)
assert "rdf_predicate" not in schema_str
assert "schema.org" not in schema_str

print("JSON Schema (sent to LLM):")
print(json.dumps(schema, indent=2))
print()

# -- Step 2: Live LLM extraction --------------------------------------

TEXT = """
Dr. Sarah Chen is a principal research scientist at DeepMind, where she leads
the protein folding team. She can be reached at s.chen@deepmind.com.
"""

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

response = client.responses.parse(
    model="gpt-4o-mini",
    input=[
        {
            "role": "system",
            "content": "Extract structured person data from the text. "
            "Return a JSON object matching the provided schema.",
        },
        {"role": "user", "content": TEXT.strip()},
    ],
    text_format=PersonView,
)

person = response.output_parsed
print(f"LLM extracted: {person}")
print()

# -- Step 3: Write to RDF graph ---------------------------------------

g = person.to_graph(subject=EX["sarah-chen"])

print(f"Triples written to graph ({len(g)}):")
for _s, p, o in sorted(g):
    local = p.split("/")[-1] if "/" in p else str(p)
    print(f"  {local} = {o}")
print()

# -- Step 4: SHACL validation -----------------------------------------

shacl_graph = PersonView.to_shacl()

try:
    from pyshacl import validate

    conforms, _, report = validate(g, shacl_graph=shacl_graph)
    print(f"SHACL validation: {'PASS' if conforms else 'FAIL'}")
    if not conforms:
        print(report)
except ImportError:
    print("pyshacl not installed — skipping SHACL validation")
    print("Install with: pip install rdfantic[shacl]")

# -- Round-trip check --------------------------------------------------

person2 = PersonView.from_graph(g, EX["sarah-chen"])
assert person2.name == person.name
assert person2.email == person.email
assert person2.job_title == person.job_title
print("\n✓ Full pipeline: Text → LLM → Pydantic → RDF graph → SHACL ✓")
