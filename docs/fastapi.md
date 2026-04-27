# FastAPI Integration

rdfantic provides `Page[Model]` — a generic paginated response model that works as a FastAPI `response_model` out of the box.

## Basic setup

```python
from fastapi import FastAPI
from rdflib import Graph, Namespace
from rdfantic import GraphModel, Page, paginate, predicate

SCHEMA = Namespace("http://schema.org/")

class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    year: int | None = predicate(SCHEMA["year"])

# Load your graph (from file, triplestore, etc.)
graph = Graph().parse("movies.ttl")

app = FastAPI()

@app.get("/movies", response_model=Page[MovieView])
def list_movies(offset: int = 0, limit: int = 10):
    return paginate(MovieView, graph, offset=offset, limit=limit)
```

The response looks like:

```json
{
  "items": [
    {"name": "Inception", "year": 2010},
    {"name": "The Matrix", "year": 1999}
  ],
  "total": 42,
  "offset": 0,
  "limit": 10
}
```

## How `paginate` works

1. Finds all subjects with `rdf:type` matching the model's `rdf_type`.
2. Sorts them (deterministic ordering).
3. Slices by `offset` and `limit`.
4. Calls `from_graph` on each subject in the slice.
5. Returns a `Page` with the items, total count, offset, and limit.

## Depth control

Pass `max_depth` to control how deeply nested models are resolved:

```python
@app.get("/movies", response_model=Page[MovieView])
def list_movies(offset: int = 0, limit: int = 10, depth: int = 1):
    return paginate(MovieView, graph, offset=offset, limit=limit, max_depth=depth)
```

## Single-item endpoints

For fetching a single resource, use `from_graph` directly:

```python
from rdflib import URIRef

@app.get("/movies/{movie_id}", response_model=MovieView)
def get_movie(movie_id: str):
    subject = URIRef(f"http://example.org/movies/{movie_id}")
    return MovieView.from_graph(graph, subject)
```

## Clean JSON Schema

`GraphModel` produces clean JSON Schema for OpenAPI docs — RDF predicate URIs are stored in field metadata and excluded from the schema output. FastAPI's auto-generated `/docs` page shows only the Python field names and types.

## No FastAPI dependency

rdfantic does not depend on FastAPI. `Page` is a standard Pydantic `BaseModel`, so it works with any framework that consumes Pydantic models (Litestar, Django Ninja, plain Pydantic serialization, etc.).
