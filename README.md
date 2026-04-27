# rdfantic

Pydantic views for RDF graphs — read, write, validate, and query graph data with typed Python models.

## The idea

RDF doesn't have tables. Every attempt at an Object-RDF Mapper copied the SQL pattern and hit the same walls: open-world data, multi-typed nodes, optional/multi-valued everything.

rdfantic takes a different approach: **the model is a view, not a table**. A `GraphModel` is a typed lens that projects data out of a graph. Multiple views can describe the same node. The graph stays the source of truth.

One model definition gives you:

- **Read** — `from_graph()` extracts matching triples into a validated Pydantic object
- **Write** — `to_triples()` / `to_graph()` serializes back with proper XSD datatypes
- **Update** — `merge_into_graph()` replaces declared predicates while preserving the rest
- **Delete** — `remove_from_graph()` removes only model-declared predicates from a node
- **SHACL** — `to_shacl()` generates a SHACL NodeShape for graph validation
- **SPARQL** — `sparql_construct()` generates a CONSTRUCT query for the model's shape
- **Remote** — `from_endpoint()` queries a remote SPARQL endpoint directly
- **Pagination** — `Page[Model]` wraps paginated graph reads for REST APIs

## Install

```bash
pip install rdfantic
```

With SHACL validation support:

```bash
pip install rdfantic[shacl]
```

Requires Python 3.13+.

## Quick start

```python
from rdflib import Graph, Namespace
from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])


class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    director: PersonView = predicate(SCHEMA["director"])
    genres: set[str] = predicate(SCHEMA["genre"])
    year: int | None = predicate(SCHEMA["year"])
```

### Read from a graph

```python
g = Graph().parse("movies.ttl")
movie = MovieView.from_graph(g, EX["inception"])

movie.name            # "Inception"
movie.genres          # {"Sci-Fi", "Thriller"}
movie.director.name   # "Christopher Nolan"
```

### Write back

```python
for triple in movie.to_triples(subject=EX["inception"]):
    g.add(triple)

# or add to a graph directly
movie.to_graph(g, subject=EX["inception"])
```

### Update and delete

`merge_into_graph` replaces the predicates declared by the model while leaving other triples on the node untouched:

```python
updated = MovieView(name="Inception (2010)", genres={"Sci-Fi"}, director=director, year=2010)
updated.merge_into_graph(g, subject=EX["inception"])
```

`remove_from_graph` deletes only the model-declared predicates:

```python
MovieView.remove_from_graph(g, subject=EX["inception"])
```

### Depth control

Nested models are traversed recursively by default. Use `max_depth` to bound traversal:

```python
# depth 0 — skip nested models entirely (set to None)
movie = MovieView.from_graph(g, EX["inception"], max_depth=0)
movie.director  # None

# depth 1 — resolve one level of nesting
movie = MovieView.from_graph(g, EX["inception"], max_depth=1)
movie.director.name  # "Christopher Nolan"
```

### SHACL validation

Generate a SHACL NodeShape directly from the model:

```python
shacl_graph = MovieView.to_shacl()
```

Use `SHConstraint` with `Annotated` types for fine-grained SHACL metadata:

```python
from typing import Annotated
from rdflib import XSD
from rdfantic import SHConstraint

class StrictMovie(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: Annotated[str, SHConstraint(min_length=1, max_length=200)] = predicate(SCHEMA["name"])
    year: Annotated[int, SHConstraint(
        datatype=XSD.nonNegativeInteger,
        min_inclusive=1888,
    )] = predicate(SCHEMA["year"])
```

### SPARQL query generation

```python
query = MovieView.sparql_construct()
# Returns a CONSTRUCT query matching the model's shape
```

### Remote SPARQL endpoints

Query a node directly from a SPARQL endpoint without a local graph:

```python
movie = MovieView.from_endpoint("https://dbpedia.org/sparql", EX["inception"])
```

### Pagination

`Page[Model]` provides a generic paginated response, designed for use with FastAPI or any Pydantic-consuming framework:

```python
from rdfantic import Page, paginate

page = paginate(MovieView, g, offset=0, limit=10)
page.items   # list[MovieView] — current page
page.total   # int — total matching subjects
page.offset  # int
page.limit   # int
```

In a FastAPI app:

```python
from fastapi import FastAPI
from rdfantic import Page, paginate

app = FastAPI()

@app.get("/movies", response_model=Page[MovieView])
def list_movies(offset: int = 0, limit: int = 10):
    return paginate(MovieView, graph, offset=offset, limit=limit)
```

## Documentation

- [Getting Started](docs/getting-started.md) — models, reading, writing, and all main features
- [SHACL Constraints](docs/shacl.md) — fine-grained SHACL metadata with `SHConstraint`
- [FastAPI Integration](docs/fastapi.md) — `Page[Model]` for REST APIs
- [Design](docs/design.md) — architecture and trade-offs
- [API Reference](docs/api.md) — complete method signatures

## Key design choices

- **View semantics**: Extra triples on a node are silently ignored. Two different `GraphModel` subclasses can read the same node with different projections.
- **Pydantic-native**: `int | None` means optional. `set[str]` means multi-valued. Validation happens through Pydantic's standard machinery.
- **rdflib-first**: Works directly with rdflib `Graph` objects. No special store required.
- **Nested models**: A field typed as another `GraphModel` subclass follows the object link and recursively reads the target node.
- **Open-world safe**: Models declare what they care about. Predicates outside the model are never touched by reads, updates, or deletes.

## License

MIT