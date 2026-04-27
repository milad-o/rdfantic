# Design

The core idea behind rdfantic and the tradeoffs it makes.

## The model is a view, not a table

RDF graphs are open-world: any node can have any predicate, nodes can have multiple types, and there's no fixed schema. ORM patterns from SQL don't translate well — they assume closed-world tables with known columns.

rdfantic treats each `GraphModel` as a **typed projection** (a view) over graph data:

- The model declares which predicates it cares about.
- `from_graph` reads only those predicates from a node.
- Extra triples are silently ignored.
- Two different models can read the same node with different projections.

This matches how RDF actually works — different consumers need different slices of the same data.

## One model, many capabilities

A single `GraphModel` definition gives you read, write, update, delete, SHACL, SPARQL, and pagination. This is possible because the field declarations carry enough information to derive all of these:

| Capability | Derived from |
|-----------|-------------|
| Read (`from_graph`) | Field name → predicate mapping, type hints for deserialization |
| Write (`to_triples`) | Same mapping in reverse, type hints for XSD datatype selection |
| Update (`merge_into_graph`) | Set of declared predicates (to know what to remove before writing) |
| Delete (`remove_from_graph`) | Same set of declared predicates |
| SHACL (`to_shacl`) | Type hints → cardinality + datatype, `SHConstraint` for overrides |
| SPARQL (`sparql_construct`) | Predicate URIs + optionality → CONSTRUCT pattern |
| Pagination (`paginate`) | `rdf_type` → subject discovery, `from_graph` for each result |

## Pydantic as the validation layer

rdfantic delegates all validation to Pydantic. The type system maps naturally:

| Python type | RDF semantics |
|-------------|--------------|
| `str` | Required, single-valued literal |
| `int \| None` | Optional, single-valued literal |
| `set[str]` | Multi-valued literals (0 or more) |
| `NestedModel` | Object property (follows the link) |
| `NestedModel \| None` | Optional object property |

Pydantic's `ValidationError` fires when extracted data doesn't match — a required field has no triple, a value can't be coerced to the declared type, etc.

## Open-world safety

Operations that modify the graph (`merge_into_graph`, `remove_from_graph`) only touch predicates declared by the model. This is deliberate:

- A `PersonView` that declares `name` and `email` can update those fields without destroying `foaf:age` or `schema:birthDate` triples that another view manages.
- Delete means "remove the predicates I know about", not "remove the entire node."

This makes it safe for multiple models (or multiple services) to manage overlapping sets of predicates on the same node.

## No special store

rdfantic works with plain rdflib `Graph` objects. You can load data from Turtle files, SPARQL endpoints, in-memory construction, or any rdflib-compatible store. There's no connection pool, session, or unit-of-work pattern to manage.

## Trade-offs

- **No inverse navigation.** You can't query "all movies directed by this person" from the model — that requires a SPARQL query or graph traversal outside the model.
- **No lazy loading.** `from_graph` reads everything up front (bounded by `max_depth`). There's no proxy object that fetches on attribute access.
- **Sorted pagination.** `paginate()` sorts subjects by their URI for deterministic ordering, not by any property value. For custom ordering, write a SPARQL query.
- **No schema migration.** If you change a model's predicates, existing graph data isn't automatically updated. The view just reads different predicates.
