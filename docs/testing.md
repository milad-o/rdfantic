# Testing

How the test suite is organized, what each file covers, and how to run it.

## Running tests

```bash
uv run pytest
```

Quick summary with no tracebacks:

```bash
uv run pytest --tb=short -q
```

Run a single file:

```bash
uv run pytest tests/test_model.py
```

SHACL integration tests require the optional `pyshacl` dependency. Install it with:

```bash
pip install rdfantic[shacl]
```

## Linting

```bash
uv run ruff check src/ tests/
```

## Test organization

All tests live in `tests/` and use pytest. Shared fixtures (a small movie graph, common namespaces) are in `conftest.py`.

The suite is split by capability — each file targets a specific claim or behavior.

### Core functionality

| File | Tests | What it covers |
|---|---|---|
| `test_model.py` | 12 | Read/write round-tripping — scalars, optionals, lists, sets, nested models |
| `test_depth.py` | 5 | Bounded recursion via `max_depth` on `from_graph()` |
| `test_update.py` | 6 | `merge_into_graph` and `remove_from_graph` — view-scoped updates and deletes |
| `test_pagination.py` | 8 | `Page[Model]` and `paginate()` for REST API responses |

### Schema generation

| File | Tests | What it covers |
|---|---|---|
| `test_shacl.py` | 18 | SHACL NodeShape generation from model definitions, `SHConstraint` overrides |
| `test_sparql.py` | 6 | SPARQL CONSTRUCT query generation from model shape |
| `test_llm_bridge.py` | 8 | JSON Schema output is clean (no RDF metadata leaks), usable as LLM extraction schema |

### Remote endpoints

| File | Tests | What it covers |
|---|---|---|
| `test_endpoint.py` | 4 | `from_endpoint()` against mocked SPARQL endpoints |
| `test_endpoint_edge.py` | 7 | HTTP 404/500, connection errors, malformed responses, empty results |

### Robustness

| File | Tests | What it covers |
|---|---|---|
| `test_round_trip.py` | 19 | Write → read → compare for every supported type (str, int, float, bool, list, set, Optional, nested) |
| `test_shacl_integration.py` | 15 | Generated SHACL shapes validate own output and reject bad data (requires `pyshacl`) |
| `test_errors.py` | 10 | Missing required fields, empty graphs, wrong subjects, type mismatches |
| `test_circular.py` | 8 | Self-referencing models, direct/indirect data cycles, depth-limited termination |
| `test_multi_view.py` | 9 | 3+ views projecting different slices of the same node with interleaved read/write |
| `test_benchmark.py` | 3 | 1k-node read, write, and round-trip — baseline performance, not pass/fail |

### Edge cases

| File | Tests | What it covers |
|---|---|---|
| `test_language_tags.py` | 6 | Language-tagged literals — str loses tag, LangStr preserves it |
| `test_xsd_mappings.py` | 6 | `date`, `datetime`, `Decimal` — correct XSD datatypes emitted |
| `test_uriref_fields.py` | 3 | `URIRef`-typed fields — read preserves type, write produces URIRef |
| `test_union_types.py` | 2 | Non-optional unions (`str \| int`) — `unwrap_type` behavior |
| `test_nested_sparql.py` | 2 | SPARQL CONSTRUCT recurses into nested model fields |
| `test_scalar_ambiguity.py` | 3 | Multiple objects for scalar field; duplicate predicate mappings |
| `test_merge_nested.py` | 3 | Merge orphans nested triples; BNode ID drift; Literal for nested field |
| `test_sparql_injection.py` | 5 | Illegal SPARQL IRI characters rejected with ValueError |
| `test_shacl_recursion.py` | 2 | SHACL generation recurses into nested models |
| `test_json_round_trip.py` | 2 | `model_dump` excludes subject; dump→validate loses it |
| `test_pagination_mixed.py` | 1 | `paginate()` with mixed URIRef and BNode subjects |
| `test_deep_nesting.py` | 2 | 50-level chain with depth limit; 200-level unlimited |
| `test_special_values.py` | 5 | NaN/Infinity round-trip; empty string as valid value |
| `test_inheritance.py` | 3 | Subclass inherits parent fields; `rdf_type` override; read/write |
| `test_forward_refs.py` | 1 | Self-referencing forward ref resolution |
| `test_boolean_coercion.py` | 5 | Typed true/false, `"true"`/`"1"` xsd:boolean, untyped literal |

## Conventions

- Each test file has a module docstring explaining what it proves.
- Test classes group related assertions (e.g., `TestFromGraph`, `TestMergeIntoGraph`).
- Models used only in tests are defined at module level with a `_` prefix when needed for forward-reference resolution.
- Remote endpoint tests use `unittest.mock.patch` on `urllib.request.urlopen` — no network calls.
- SHACL integration tests are the only ones that require the optional `pyshacl` extra.
