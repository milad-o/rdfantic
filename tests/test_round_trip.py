"""Round-trip fidelity tests — write → read → compare for every supported type.

Proves Claims 1 + 2 (read/write) produce lossless, type-stable results.
"""

from __future__ import annotations

from rdflib import Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class TestScalarRoundTrips:
    """Each Python scalar type survives a write → read cycle without drift."""

    def test_str_round_trip(self) -> None:
        class M(GraphModel):
            val: str = predicate(SCHEMA["val"])

        original = M(val="hello world")
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.val == original.val
        assert type(restored.val) is str

    def test_int_round_trip(self) -> None:
        class M(GraphModel):
            val: int = predicate(SCHEMA["val"])

        original = M(val=42)
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.val == original.val
        assert type(restored.val) is int

    def test_float_round_trip(self) -> None:
        class M(GraphModel):
            val: float = predicate(SCHEMA["val"])

        original = M(val=3.14)
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.val == original.val
        assert type(restored.val) is float

    def test_bool_round_trip(self) -> None:
        class M(GraphModel):
            val: bool = predicate(SCHEMA["val"])

        for v in (True, False):
            original = M(val=v)
            g = original.to_graph(subject=EX["x"])
            restored = M.from_graph(g, EX["x"])

            assert restored.val == original.val
            assert type(restored.val) is bool

    def test_large_int_round_trip(self) -> None:
        class M(GraphModel):
            val: int = predicate(SCHEMA["val"])

        original = M(val=10**18)
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.val == original.val

    def test_negative_values_round_trip(self) -> None:
        class M(GraphModel):
            i: int = predicate(SCHEMA["i"])
            f: float = predicate(SCHEMA["f"])

        original = M(i=-99, f=-2.5)
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.i == -99
        assert restored.f == -2.5

    def test_empty_string_round_trip(self) -> None:
        class M(GraphModel):
            val: str = predicate(SCHEMA["val"])

        original = M(val="")
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.val == ""

    def test_zero_values_round_trip(self) -> None:
        class M(GraphModel):
            i: int = predicate(SCHEMA["i"])
            f: float = predicate(SCHEMA["f"])

        original = M(i=0, f=0.0)
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.i == 0
        assert restored.f == 0.0


class TestOptionalRoundTrips:
    """Optional fields survive round-trips in both present and absent states."""

    def test_optional_present(self) -> None:
        class M(GraphModel):
            val: int | None = predicate(SCHEMA["val"])

        original = M(val=7)
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.val == 7

    def test_optional_absent(self) -> None:
        class M(GraphModel):
            val: int | None = predicate(SCHEMA["val"])

        original = M(val=None)
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.val is None


class TestCollectionRoundTrips:
    """Multi-valued fields survive round-trips."""

    def test_set_str_round_trip(self) -> None:
        class M(GraphModel):
            tags: set[str] = predicate(SCHEMA["tag"])

        original = M(tags={"alpha", "beta", "gamma"})
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.tags == original.tags

    def test_list_int_round_trip(self) -> None:
        class M(GraphModel):
            scores: list[int] = predicate(SCHEMA["score"])

        original = M(scores=[10, 20, 30])
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        # Lists lose ordering in RDF (unordered triples), but values should match
        assert sorted(restored.scores) == sorted(original.scores)

    def test_empty_set_round_trip(self) -> None:
        class M(GraphModel):
            tags: set[str] = predicate(SCHEMA["tag"])

        original = M(tags=set())
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.tags == set()

    def test_single_element_set_round_trip(self) -> None:
        class M(GraphModel):
            tags: set[str] = predicate(SCHEMA["tag"])

        original = M(tags={"solo"})
        g = original.to_graph(subject=EX["x"])
        restored = M.from_graph(g, EX["x"])

        assert restored.tags == {"solo"}


# -- Module-level models for nested/composite tests (get_type_hints needs these) --


class _Inner(GraphModel):
    rdf_type = SCHEMA["Inner"]
    label: str = predicate(SCHEMA["label"])


class _Outer(GraphModel):
    rdf_type = SCHEMA["Outer"]
    name: str = predicate(SCHEMA["name"])
    child: _Inner = predicate(SCHEMA["child"])


class _OuterOptional(GraphModel):
    rdf_type = SCHEMA["Outer"]
    name: str = predicate(SCHEMA["name"])
    child: _Inner | None = predicate(SCHEMA["child"])


class _Tag(GraphModel):
    rdf_type = SCHEMA["Tag"]
    label: str = predicate(SCHEMA["label"])


class _Article(GraphModel):
    rdf_type = SCHEMA["Article"]
    title: str = predicate(SCHEMA["title"])
    tags: list[_Tag] = predicate(SCHEMA["tag"])


class _CompositePerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])


class _CompositeMovie(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    year: int | None = predicate(SCHEMA["year"])
    rating: float | None = predicate(SCHEMA["rating"])
    genres: set[str] = predicate(SCHEMA["genre"])
    director: _CompositePerson = predicate(SCHEMA["director"])


class TestNestedRoundTrips:
    """Nested GraphModel fields survive round-trips."""

    def test_nested_model_round_trip(self) -> None:
        original = _Outer(name="parent", child=_Inner(label="kid"))
        g = original.to_graph(subject=EX["p"])
        restored = _Outer.from_graph(g, EX["p"])

        assert restored.name == original.name
        assert restored.child.label == original.child.label

    def test_nested_optional_present(self) -> None:
        original = _OuterOptional(name="parent", child=_Inner(label="kid"))
        g = original.to_graph(subject=EX["p"])
        restored = _OuterOptional.from_graph(g, EX["p"])

        assert restored.child is not None
        assert restored.child.label == "kid"

    def test_nested_optional_absent(self) -> None:
        original = _OuterOptional(name="lonely", child=None)
        g = original.to_graph(subject=EX["p"])
        restored = _OuterOptional.from_graph(g, EX["p"])

        assert restored.child is None

    def test_nested_set_round_trip(self) -> None:
        original = _Article(
            title="Test",
            tags=[_Tag(label="a"), _Tag(label="b")],
        )
        g = original.to_graph(subject=EX["art"])
        restored = _Article.from_graph(g, EX["art"])

        assert restored.title == "Test"
        assert {t.label for t in restored.tags} == {"a", "b"}


class TestCompositeRoundTrips:
    """Models with multiple field types survive round-trips together."""

    def test_full_model_round_trip(self) -> None:
        original = _CompositeMovie(
            name="Inception",
            year=2010,
            rating=8.8,
            genres={"Sci-Fi", "Thriller"},
            director=_CompositePerson(name="Christopher Nolan"),
        )
        g = original.to_graph(subject=EX["inception"])
        restored = _CompositeMovie.from_graph(g, EX["inception"])

        assert restored.name == original.name
        assert restored.year == original.year
        assert restored.rating == original.rating
        assert restored.genres == original.genres
        assert restored.director.name == original.director.name
