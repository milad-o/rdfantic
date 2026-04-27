# SHACL Constraints

rdfantic generates SHACL shapes from model type hints automatically. Use `SHConstraint` with `Annotated` to override or extend the defaults.

## Basic shape generation

```python
from rdflib import Namespace
from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")

class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    age: int | None = predicate(SCHEMA["age"])

shacl_graph = PersonView.to_shacl()
```

This generates a SHACL NodeShape with:

- `sh:targetClass schema:Person`
- `sh:property` for `schema:name` — `sh:datatype xsd:string`, `sh:minCount 1`, `sh:maxCount 1`
- `sh:property` for `schema:age` — `sh:datatype xsd:integer`, `sh:maxCount 1` (no `minCount` since optional)

## Using `SHConstraint`

Wrap a type in `Annotated` with an `SHConstraint` to add or override SHACL metadata:

```python
from typing import Annotated
from rdflib import XSD
from rdfantic import SHConstraint

class StrictPerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: Annotated[str, SHConstraint(
        min_length=1,
        max_length=200,
        name="Full Name",
        description="The person's full legal name",
    )] = predicate(SCHEMA["name"])
    age: Annotated[int, SHConstraint(
        min_inclusive=0,
        max_inclusive=150,
    )] = predicate(SCHEMA["age"])
```

## Supported constraint fields

| Field | SHACL property | Example |
|-------|---------------|---------|
| `min_count` | `sh:minCount` | `SHConstraint(min_count=1)` |
| `max_count` | `sh:maxCount` | `SHConstraint(max_count=5)` |
| `datatype` | `sh:datatype` | `SHConstraint(datatype=XSD.nonNegativeInteger)` |
| `pattern` | `sh:pattern` | `SHConstraint(pattern=r"^\d{4}-\d{2}-\d{2}$")` |
| `min_inclusive` | `sh:minInclusive` | `SHConstraint(min_inclusive=0)` |
| `max_inclusive` | `sh:maxInclusive` | `SHConstraint(max_inclusive=100)` |
| `min_exclusive` | `sh:minExclusive` | `SHConstraint(min_exclusive=0)` |
| `max_exclusive` | `sh:maxExclusive` | `SHConstraint(max_exclusive=1000)` |
| `min_length` | `sh:minLength` | `SHConstraint(min_length=1)` |
| `max_length` | `sh:maxLength` | `SHConstraint(max_length=255)` |
| `node_kind` | `sh:nodeKind` | `SHConstraint(node_kind=SH.IRI)` |
| `has_value` | `sh:hasValue` | `SHConstraint(has_value=Literal("active"))` |
| `class_` | `sh:class` | `SHConstraint(class_=SCHEMA.Organization)` |
| `name` | `sh:name` | `SHConstraint(name="Full Name")` |
| `description` | `sh:description` | `SHConstraint(description="...")` |
| `extra` | *(any URI)* | `SHConstraint(extra={SH.order: Literal(1)})` |

Any field left as `None` uses the default inferred from the Python type hint.

## Datatype overrides

`SHConstraint.datatype` overrides both the SHACL shape *and* the XSD datatype used when writing triples with `to_triples()`:

```python
class Movie(GraphModel):
    rdf_type = SCHEMA["Movie"]
    year: Annotated[int, SHConstraint(datatype=XSD.nonNegativeInteger)] = predicate(SCHEMA["year"])
```

When serializing, `year=2010` produces `Literal(2010, datatype=XSD.nonNegativeInteger)` instead of the default `XSD.integer`.

## Extra constraints

The `extra` dict allows arbitrary SHACL properties not covered by the named fields:

```python
from rdflib import SH, Literal

class OrderedPerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: Annotated[str, SHConstraint(extra={
        SH.order: Literal(1),
        SH.group: SCHEMA["BasicInfo"],
    })] = predicate(SCHEMA["name"])
```

## Validating data with pyshacl

The generated SHACL graph works directly with pyshacl:

```python
from pyshacl import validate

data_graph = person.to_graph(subject=EX["alice"])
shacl_graph = StrictPerson.to_shacl()

conforms, results_graph, results_text = validate(
    data_graph,
    shacl_graph=shacl_graph,
)
```
