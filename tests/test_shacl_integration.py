"""SHACL integration tests — generate shapes, write data, validate with pySHACL.

Proves Claim 3 (SHACL generation) produces shapes that actually validate real data
across all supported type combinations.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, SHConstraint, predicate

pyshacl = pytest.importorskip("pyshacl")

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


# -- Module-level models for nested tests (get_type_hints needs these) ------


class _ShaclInner(GraphModel):
    rdf_type = SCHEMA["Inner"]
    label: str = predicate(SCHEMA["label"])


class _ShaclOuter(GraphModel):
    rdf_type = SCHEMA["Outer"]
    name: str = predicate(SCHEMA["name"])
    child: _ShaclInner = predicate(SCHEMA["child"])


class _ShaclPerson(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])


class _ShaclMovie(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    year: int | None = predicate(SCHEMA["year"])
    genres: set[str] = predicate(SCHEMA["genre"])
    director: _ShaclPerson = predicate(SCHEMA["director"])


def _validate(data: Graph, model_cls: type) -> bool:
    """Helper: generate SHACL from model, validate data graph, return conforms."""
    shacl_graph = model_cls.to_shacl()
    conforms, _, _ = pyshacl.validate(data, shacl_graph=shacl_graph)
    return conforms


class TestSHACLValidatesOwnOutput:
    """Data written by to_graph() should always pass SHACL from the same model."""

    def test_scalar_str(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            name: str = predicate(SCHEMA["name"])

        g = M(name="hello").to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_scalar_int(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            count: int = predicate(SCHEMA["count"])

        g = M(count=42).to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_scalar_float(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            score: float = predicate(SCHEMA["score"])

        g = M(score=9.5).to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_scalar_bool(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            active: bool = predicate(SCHEMA["active"])

        g = M(active=True).to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_optional_present(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            name: str = predicate(SCHEMA["name"])
            note: str | None = predicate(SCHEMA["note"])

        g = M(name="a", note="b").to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_optional_absent(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            name: str = predicate(SCHEMA["name"])
            note: str | None = predicate(SCHEMA["note"])

        g = M(name="a", note=None).to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_multi_valued(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            tags: set[str] = predicate(SCHEMA["tag"])

        g = M(tags={"x", "y", "z"}).to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_nested_model(self) -> None:
        g = _ShaclOuter(name="p", child=_ShaclInner(label="c")).to_graph(
            subject=EX["p"]
        )
        assert _validate(g, _ShaclOuter)

    def test_annotated_constraint(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            rating: Annotated[int, SHConstraint(min_inclusive=1, max_inclusive=10)] = (
                predicate(SCHEMA["rating"])
            )

        g = M(rating=5).to_graph(subject=EX["x"])
        assert _validate(g, M)

    def test_full_composite_model(self) -> None:
        movie = _ShaclMovie(
            name="Inception",
            year=2010,
            genres={"Sci-Fi", "Thriller"},
            director=_ShaclPerson(name="Nolan"),
        )
        g = movie.to_graph(subject=EX["inception"])
        assert _validate(g, _ShaclMovie)


class TestSHACLRejectsBadData:
    """Manually crafted bad data should fail SHACL validation."""

    def test_missing_required_field(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            name: str = predicate(SCHEMA["name"])

        g = Graph()
        g.add((EX["x"], RDF.type, SCHEMA["Thing"]))
        # No name triple — should fail

        assert not _validate(g, M)

    def test_wrong_datatype(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            count: int = predicate(SCHEMA["count"])

        g = Graph()
        g.add((EX["x"], RDF.type, SCHEMA["Thing"]))
        g.add((EX["x"], SCHEMA["count"], Literal("not-a-number", datatype=XSD.string)))

        assert not _validate(g, M)

    def test_too_many_values_for_scalar(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            name: str = predicate(SCHEMA["name"])

        g = Graph()
        g.add((EX["x"], RDF.type, SCHEMA["Thing"]))
        g.add((EX["x"], SCHEMA["name"], Literal("first", datatype=XSD.string)))
        g.add((EX["x"], SCHEMA["name"], Literal("second", datatype=XSD.string)))

        assert not _validate(g, M)

    def test_constraint_violation(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            rating: Annotated[int, SHConstraint(min_inclusive=1, max_inclusive=10)] = (
                predicate(SCHEMA["rating"])
            )

        g = Graph()
        g.add((EX["x"], RDF.type, SCHEMA["Thing"]))
        g.add((EX["x"], SCHEMA["rating"], Literal(99, datatype=XSD.integer)))

        assert not _validate(g, M)

    def test_pattern_violation(self) -> None:
        class M(GraphModel):
            rdf_type = SCHEMA["Thing"]
            email: Annotated[str, SHConstraint(pattern=r"^.+@.+\..+$")] = predicate(
                SCHEMA["email"]
            )

        g = Graph()
        g.add((EX["x"], RDF.type, SCHEMA["Thing"]))
        g.add((EX["x"], SCHEMA["email"], Literal("not-an-email", datatype=XSD.string)))

        assert not _validate(g, M)
