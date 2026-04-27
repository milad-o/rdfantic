# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
