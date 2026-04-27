# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.3] — 2026-04-27

### Added

- `LangStr` type — string subclass that preserves BCP 47 language tags through read → write round-trips
- Recursive SPARQL CONSTRUCT — `model_to_construct` now includes triple patterns for nested `GraphModel` fields
- Recursive SHACL generation — `model_to_shacl` now generates NodeShapes for nested `GraphModel` fields
- Cycle detection for both SPARQL and SHACL generation (prevents infinite recursion on self-referencing models)
- Edge-case test suite — 16 new test files covering language tags, XSD mappings, URIRef fields, union types, nested SPARQL, scalar ambiguity, merge orphans, SPARQL injection, SHACL recursion, JSON round-trip, mixed pagination, deep nesting, special floats, inheritance, forward refs, boolean coercion
- `date`, `datetime`, `time`, `Decimal` added to `_PYTHON_TO_XSD` type mappings
- SPARQL URI sanitization — `_sparql_uri` rejects URIs with illegal IRI characters

### Fixed

- `rdf_value_to_python` now preserves `URIRef` when the target field type is `URIRef` instead of converting to `str`

## [0.2.1] — 2026-04-27

### Changed

- Lower minimum Python from 3.14 to 3.12 — opens the package to 3.12 and 3.13 users
- Remove Mermaid diagram from README (redundant with tagline)
- Add PydanticRDF to comparison table

## [0.2.0] — 2026-04-27

### Added

- Exception hierarchy: `RdfanticError`, `GraphReadError`, `SubjectNotFoundError`, `EndpointError`
- `timeout` parameter on `from_endpoint()` (default 30s)
- Endpoint URL scheme validation (http/https only)
- Testing guide at `docs/testing.md`

### Changed

- `subject` is now a proper Pydantic field (`Field(exclude=True)`) instead of a private `_subject` attribute — survives `model_copy()` and round-trips
- SPARQL subject binding uses direct generation instead of brittle string replacement
- HTTP errors from `from_endpoint()` are now wrapped in `EndpointError`

### Removed

- `bind_namespace()` — it wrapped `Namespace()` and silently ignored the prefix argument
- `namespace` ClassVar on `GraphModel` — was declared but never used by any logic

## [0.1.3] — 2026-04-27

### Added

- Circular reference tests — self-referencing models, direct/indirect data cycles, depth-limited termination
- Endpoint edge case tests — empty results, HTTP 404/500, connection errors, malformed responses
- Wider competitor survey — evaluated PydanticRDF (Omegaice/pydantic-rdf) and updated gap analysis

## [0.1.2] — 2026-04-27

### Added

- Multi-view stress tests — 3+ views on same node with interleaved read/write
- Round-trip fidelity tests for every supported type (str, int, float, bool, set, list, Optional, nested)
- SHACL integration tests — generated shapes validate own output, reject bad data
- Error-path tests — missing required fields, empty graphs, wrong subjects
- Bulk benchmark tests — 1k node read/write/round-trip

## [0.1.1] — 2026-04-27

### Added

- Getting-started guide, SHACL reference, FastAPI integration, design doc, and API reference
- Runnable example scripts for all main features
- Live 4-step LLM extraction pipeline in `llm_bridge` example

### Changed

- Bump minimum Python to 3.14
- Convert example scripts from `.py` to Jupyter notebooks with stored outputs
- Add `ipykernel` to dev dependencies
- Switch to dynamic versioning (hatchling reads `_version.py`)

### Fixed

- Use static Python version badge in README

## [0.1.0] — 2026-04-27

### Added

- `GraphModel` base class — typed Pydantic views over RDF graph data
- `predicate()` field descriptor mapping Python fields to RDF predicates
- `from_graph()` — read a node from an rdflib `Graph` into a validated model
- `to_triples()` / `to_graph()` — serialize model instances back to RDF triples
- `merge_into_graph()` — update a node by replacing only model-declared predicates
- `remove_from_graph()` — delete model-declared predicates from a node
- `to_shacl()` — generate SHACL NodeShape from model definition
- `SHConstraint` — fine-grained SHACL metadata via `Annotated` types
- `sparql_construct()` — generate SPARQL CONSTRUCT queries from model shape
- `from_endpoint()` — query a remote SPARQL endpoint directly
- `max_depth` parameter on `from_graph()` for bounded recursion into nested models
- `Page[Model]` and `paginate()` — generic paginated response for REST APIs
- Clean JSON Schema output for LLM extraction pipelines (no RDF metadata leaks)
- CI workflow (lint + test) and release workflow (PyPI via OIDC trusted publisher)

[0.2.1]: https://github.com/milad-o/rdfantic/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/milad-o/rdfantic/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/milad-o/rdfantic/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/milad-o/rdfantic/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/milad-o/rdfantic/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/milad-o/rdfantic/releases/tag/v0.1.0
