# Getting Started

This guide walks through defining models, reading and writing graph data, and using the main features of rdfantic.

## Installation

```bash
pip install rdfantic
```

For SHACL validation support:

```bash
pip install rdfantic[shacl]
```

## Defining a model

A `GraphModel` maps Python fields to RDF predicates. Each field uses `predicate()` to declare which predicate it corresponds to.

```python
from rdflib import Namespace
from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")

class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    email: str | None = predicate(SCHEMA["email"])
    knows: list[str] = predicate(SCHEMA["knows"])
```

Key conventions:

- `rdf_type` (optional) sets the `rdf:type` used when matching, writing, and generating SHACL/SPARQL.
- `str` — required scalar field.
- `str | None` — optional field. Missing triples produce `None`.
- `list[str]` or `set[str]` — multi-valued field. Collects all matching triples.

## Reading from a graph

```python
from rdflib import Graph

g = Graph().parse("people.ttl")
person = PersonView.from_graph(g, SCHEMA["alice"])

person.name   # "Alice"
person.email  # "alice@example.org" or None
person.knows  # ["Bob", "Carol"]
```

`from_graph` extracts only the predicates declared by the model. Extra triples on the node are ignored — this is the "view" semantics.

## Nested models

A field typed as another `GraphModel` follows the object link and recursively reads the target node:

```python
class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    director: PersonView = predicate(SCHEMA["director"])
```

```python
movie = MovieView.from_graph(g, EX["inception"])
movie.director.name  # "Christopher Nolan"
```

### Depth control

Deep graphs can cause excessive recursion. Use `max_depth` to limit traversal:

```python
# Don't follow any nested models
movie = MovieView.from_graph(g, EX["inception"], max_depth=0)
movie.director  # None

# Follow one level
movie = MovieView.from_graph(g, EX["inception"], max_depth=1)
movie.director.name  # "Christopher Nolan"
```

## Writing to a graph

```python
person = PersonView(name="Dave", email="dave@example.org", knows=[])

# As a list of triples
triples = person.to_triples(subject=EX["dave"])

# Directly into a graph
g = person.to_graph(subject=EX["dave"])
```

If no subject is provided, `to_triples` falls back to the subject the instance was read from, or generates a blank node.

## Updating a node

`merge_into_graph` replaces only the predicates declared by the model. Other triples on the node are left untouched:

```python
updated = PersonView(name="Dave Smith", email=None, knows=["Eve"])
updated.merge_into_graph(g, subject=EX["dave"])
```

After this call:
- `schema:name` is now `"Dave Smith"`
- `schema:email` is removed (value is `None`)
- `schema:knows` is `["Eve"]`
- Any other predicates on `EX["dave"]` (e.g. `foaf:age`) are unchanged

## Deleting model-declared predicates

`remove_from_graph` removes only the predicates the model declares:

```python
PersonView.remove_from_graph(g, subject=EX["dave"])
```

This deletes `schema:name`, `schema:email`, `schema:knows`, and the `rdf:type` triple, but leaves any other predicates on the node.

## Remote SPARQL endpoints

Query a node directly from a SPARQL endpoint:

```python
person = PersonView.from_endpoint("https://dbpedia.org/sparql", EX["alice"])
```

This generates a CONSTRUCT query, executes it against the endpoint, and parses the result with `from_graph`.

## Pagination

`paginate()` finds all subjects matching a model's `rdf_type` and returns a paginated slice:

```python
from rdfantic import paginate

page = paginate(PersonView, g, offset=0, limit=20)
page.items   # list[PersonView]
page.total   # total matching subjects
```

See [FastAPI integration](fastapi.md) for using `Page[Model]` in REST APIs.

## SHACL validation

Generate a SHACL NodeShape from the model:

```python
shacl_graph = PersonView.to_shacl()
```

For fine-grained constraints, use `SHConstraint` with `Annotated`:

```python
from typing import Annotated
from rdfantic import SHConstraint

class StrictPerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: Annotated[str, SHConstraint(min_length=1, max_length=200)] = predicate(SCHEMA["name"])
    age: Annotated[int, SHConstraint(min_inclusive=0, max_inclusive=150)] = predicate(SCHEMA["age"])
```

See [SHACL constraints](shacl.md) for the full list of supported constraint fields.

## SPARQL query generation

Generate a CONSTRUCT query matching the model's shape:

```python
query = PersonView.sparql_construct()
```

The generated query uses required triple patterns for required fields and `OPTIONAL` blocks for optional/multi-valued fields.

## Next steps

- [SHACL Constraints](shacl.md) — fine-grained SHACL metadata with `SHConstraint`
- [FastAPI Integration](fastapi.md) — `Page[Model]` for REST APIs
- [API Reference](api.md) — complete method signatures
