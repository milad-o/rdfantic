"""SHACL validation — generate shapes from models and validate data with pyshacl."""

from typing import Annotated

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, SHConstraint, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class StrictPerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: Annotated[
        str,
        SHConstraint(
            min_length=1,
            max_length=200,
            name="Full Name",
        ),
    ] = predicate(SCHEMA["name"])
    age: Annotated[
        int,
        SHConstraint(
            min_inclusive=0,
            max_inclusive=150,
        ),
    ] = predicate(SCHEMA["age"])


# -- Generate SHACL shape ----------------------------------------------

shacl_graph = StrictPerson.to_shacl()

print("Generated SHACL shape:")
print(shacl_graph.serialize(format="turtle"))

# -- Valid data --------------------------------------------------------

valid = Graph()
valid.add((EX["alice"], RDF.type, SCHEMA["Person"]))
valid.add((EX["alice"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
valid.add((EX["alice"], SCHEMA["age"], Literal(30, datatype=XSD.integer)))

# -- Invalid data (age = -5) ------------------------------------------

invalid = Graph()
invalid.add((EX["bob"], RDF.type, SCHEMA["Person"]))
invalid.add((EX["bob"], SCHEMA["name"], Literal("Bob", datatype=XSD.string)))
invalid.add((EX["bob"], SCHEMA["age"], Literal(-5, datatype=XSD.integer)))

# -- Validate with pyshacl (requires: pip install rdfantic[shacl]) -----

try:
    from pyshacl import validate

    conforms, _, report = validate(valid, shacl_graph=shacl_graph)
    print(f"Valid data conforms: {conforms}")

    conforms, _, report = validate(invalid, shacl_graph=shacl_graph)
    print(f"Invalid data conforms: {conforms}")
    if not conforms:
        print(f"\nValidation report:\n{report}")
except ImportError:
    print("pyshacl not installed — run: pip install rdfantic[shacl]")
    print("Skipping validation, but the SHACL shape above is valid.")
