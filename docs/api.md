# API Reference

Complete signatures for all public classes and functions in rdfantic.

## `GraphModel`

Base class for typed RDF graph views. Subclass this and declare fields with `predicate()`.

### Class variables

| Variable | Type | Description |
|----------|------|-------------|
| `rdf_type` | `ClassVar[URIRef \| None]` | The `rdf:type` for matching/writing nodes. Optional. |

### Fields

#### `subject`

```python
subject: URIRef | BNode | None = Field(default=None, exclude=True)
```

The RDF subject this instance was read from, or `None` if constructed directly. Excluded from `model_dump()` and JSON Schema output. Survives `model_copy()`.

### Methods

#### `from_graph`

```python
@classmethod
def from_graph(
    cls,
    graph: Graph,
    subject: URIRef | BNode,
    *,
    max_depth: int | None = None,
) -> Self
```

Read a node from the graph and validate it into this model. Only extracts predicates declared by the model's fields.

- `max_depth=None` — unlimited recursion into nested models.
- `max_depth=0` — no nested models traversed (optional nested fields become `None`, multi-valued become empty).
- Raises `ValidationError` if extracted data doesn't satisfy type constraints.

#### `to_triples`

```python
def to_triples(
    self,
    subject: URIRef | BNode | None = None,
) -> list[tuple[Identifier, URIRef, Identifier]]
```

Serialize this instance to RDF triples. Falls back to `self.subject`, then generates a blank node.

#### `to_graph`

```python
def to_graph(
    self,
    graph: Graph | None = None,
    subject: URIRef | BNode | None = None,
) -> Graph
```

Serialize into an rdflib `Graph`. Creates a new graph if none provided.

#### `merge_into_graph`

```python
def merge_into_graph(
    self,
    graph: Graph,
    subject: URIRef | BNode | None = None,
) -> Graph
```

Replace model-declared predicates on a subject, then write new ones. Predicates not declared by the model are left untouched. Falls back to `self.subject`.

#### `remove_from_graph`

```python
@classmethod
def remove_from_graph(
    cls,
    graph: Graph,
    subject: URIRef | BNode,
) -> Graph
```

Remove all triples for a subject whose predicates this model declares. Other predicates are left untouched.

#### `to_shacl`

```python
@classmethod
def to_shacl(cls, shape_uri: URIRef | None = None) -> Graph
```

Generate a SHACL NodeShape graph from the model's field declarations.

#### `sparql_construct`

```python
@classmethod
def sparql_construct(cls, subject_var: str = "s") -> str
```

Generate a SPARQL CONSTRUCT query for the model's shape. Required fields become required patterns; optional/multi-valued fields become `OPTIONAL` blocks.

#### `from_endpoint`

```python
@classmethod
def from_endpoint(
    cls,
    endpoint: str,
    subject: URIRef,
    *,
    max_depth: int | None = None,
    timeout: float = 30.0,
) -> Self
```

Read a node from a remote SPARQL endpoint. Generates a CONSTRUCT query, executes it via HTTP POST, and parses the result with `from_graph`. Only `http` and `https` endpoints are accepted. Raises `EndpointError` on HTTP failures or malformed responses.

---

## `predicate`

```python
def predicate(uri: URIRef | str, **kwargs: Any) -> FieldInfo
```

Declare a field that maps to an RDF predicate. `**kwargs` are forwarded to `pydantic.Field()`. The predicate URI is stored in field metadata and excluded from JSON Schema output.

## `get_predicate`

```python
def get_predicate(field_info: FieldInfo) -> URIRef | None
```

Extract the RDF predicate URI from a field's metadata. Returns `None` if no predicate is set.

---

## `Page`

```python
class Page[T](BaseModel):
    items: list[T]
    total: int
    offset: int
    limit: int
```

A paginated response containing a slice of results and total count. Works as a `response_model` in FastAPI.

## `paginate`

```python
def paginate(
    model_cls: type,
    graph: Graph,
    *,
    offset: int = 0,
    limit: int = 10,
    max_depth: int | None = None,
) -> Page
```

Find all subjects matching the model's `rdf_type` and return the requested slice. Raises `ValueError` if the model has no `rdf_type`.

---

## `SHConstraint`

```python
@dataclass(frozen=True, slots=True)
class SHConstraint:
    min_count: int | None = None
    max_count: int | None = None
    datatype: URIRef | None = None
    pattern: str | None = None
    min_inclusive: int | float | None = None
    max_inclusive: int | float | None = None
    min_exclusive: int | float | None = None
    max_exclusive: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    node_kind: URIRef | None = None
    has_value: Any = None
    class_: URIRef | None = None
    name: str | None = None
    description: str | None = None
    extra: dict[URIRef, Any] = field(default_factory=dict)
```

SHACL property-shape constraints for use with `Annotated` types. Any field left as `None` means "use the default inferred from the type hint."

## `get_sh_constraints`

```python
def get_sh_constraints(annotation: Any) -> SHConstraint | None
```

Extract the first `SHConstraint` from a `typing.Annotated` type. Returns `None` if none found.

---

## `LangStr`

```python
class LangStr(str):
    language: str | None

    def __new__(cls, value: str = "", language: str | None = None) -> LangStr
```

A string subclass that preserves an optional BCP 47 language tag. Use as a field type when language-tagged RDF literals must survive read → write round-trips. Behaves identically to `str` for all normal operations.

```python
class LabelView(GraphModel):
    label: LangStr = predicate(SCHEMA["name"])
```

With `str`, `Literal("Bonjour", lang="fr")` round-trips to `Literal("Bonjour", datatype=xsd:string)` — the tag is lost. With `LangStr`, it round-trips to `Literal("Bonjour", lang="fr")`.

---

## SPARQL utilities

### `model_to_construct`

```python
def model_to_construct(model_cls: type, subject_var: str = "s") -> str
```

Generate a SPARQL CONSTRUCT query from a `GraphModel` subclass. Recursively includes triple patterns for nested `GraphModel` fields. Called internally by `GraphModel.sparql_construct()`.

### `model_to_construct_for_subject`

```python
def model_to_construct_for_subject(model_cls: type, subject: URIRef) -> str
```

Generate a CONSTRUCT query bound to a specific subject IRI. Used by `from_endpoint()`.

---

## SHACL utilities

### `model_to_shacl`

```python
def model_to_shacl(model_cls: type, shape_uri: URIRef | None = None) -> Graph
```

Generate a SHACL NodeShape graph. Recursively generates shapes for nested `GraphModel` fields. Called internally by `GraphModel.to_shacl()`. Respects `SHConstraint` overrides from `Annotated` types.

---

## Type utilities

### `python_type_to_xsd`

```python
def python_type_to_xsd(py_type: type) -> URIRef | None
```

Map a Python type to its XSD datatype URI. Returns `None` for types without a direct mapping.

| Python type | XSD datatype |
|-------------|-------------|
| `str` | `xsd:string` |
| `int` | `xsd:integer` |
| `float` | `xsd:double` |
| `bool` | `xsd:boolean` |

### `unwrap_type`

```python
def unwrap_type(annotation: Any) -> tuple[type, bool, bool]
```

Unwrap a type annotation into `(inner_type, is_optional, is_multi)`. Handles `Annotated`, `Optional`, `X | None`, `set[T]`, `list[T]`, `frozenset[T]`.

### `python_value_to_rdf`

```python
def python_value_to_rdf(value: Any, py_type: type, datatype: URIRef | None = None) -> Node
```

Convert a Python value to an rdflib term. `datatype` overrides the default XSD mapping.

### `rdf_value_to_python`

```python
def rdf_value_to_python(node: Node, py_type: type) -> Any
```

Convert an rdflib term to a Python value.

---

## Exceptions

All exceptions inherit from `RdfanticError`, which inherits from `Exception`.

| Exception | Parent | When raised |
|-----------|--------|-------------|
| `RdfanticError` | `Exception` | Base class for all rdfantic errors. |
| `GraphReadError` | `RdfanticError` | Reading from a graph fails for structural reasons. |
| `SubjectNotFoundError` | `GraphReadError` | No triples match the requested subject. |
| `EndpointError` | `RdfanticError` | Remote SPARQL endpoint request fails (HTTP error, timeout, connection refused). |
