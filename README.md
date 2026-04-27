# rdfantic

Pydantic views for RDF graphs — read, write, validate, and query graph data with typed Python models.

## The idea

RDF doesn't have tables. Every attempt at an Object-RDF Mapper copied the SQL pattern and hit the same walls: open-world data, multi-typed nodes, optional/multi-valued everything.

rdfantic takes a different approach: **the model is a view, not a table**. A `GraphModel` is a typed lens that projects data out of a graph. Multiple views can describe the same node. The graph stays the source of truth.

One model definition gives you:

- **Read** — `from_graph()` extracts matching triples into a validated Pydantic object
- **Write** — `to_triples()` / `to_graph()` serializes back with proper XSD datatypes
- **SHACL** — `to_shacl()` generates a SHACL NodeShape for graph validation
- **SPARQL** — `sparql_construct()` generates a CONSTRUCT query for the model's shape

## Install

```bash
pip install rdfantic
```

Or with SHACL validation support:

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


# Read from a graph
g = Graph().parse("movies.ttl")
movie = MovieView.from_graph(g, EX["inception"])

print(movie.name)            # "Inception"
print(movie.genres)          # {"Sci-Fi", "Thriller"}
print(movie.director.name)   # "Christopher Nolan"

# Write back to triples
for triple in movie.to_triples(subject=EX["inception"]):
    g.add(triple)

# Generate SHACL shape
shacl_graph = MovieView.to_shacl()

# Generate SPARQL CONSTRUCT
query = MovieView.sparql_construct()
```

## Key design choices

- **View semantics**: Extra triples on a node are silently ignored. Two different `GraphModel` subclasses can read the same node with different projections.
- **Pydantic-native**: `int | None` means optional. `set[str]` means multi-valued. Validation happens through Pydantic's standard machinery.
- **rdflib-first**: Works directly with rdflib `Graph` objects. No special store required.
- **Nested models**: A field typed as another `GraphModel` subclass follows the object link and recursively reads the target node.

## License

MIT