"""Tests for SHACL shape generation."""

from __future__ import annotations

from typing import Annotated

from rdflib import RDF, SH, XSD, Namespace, URIRef

from rdfantic import GraphModel, SHConstraint, predicate

SCHEMA = Namespace("http://schema.org/")
_CUSTOM_PRED = URIRef("http://example.org/custom")


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]

    name: str = predicate(SCHEMA["name"])


class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]

    name: str = predicate(SCHEMA["name"])
    director: PersonView = predicate(SCHEMA["director"])
    genres: set[str] = predicate(SCHEMA["genre"])
    year: int | None = predicate(SCHEMA["year"])


class _ExtraCustomView(GraphModel):
    val: Annotated[str, SHConstraint(extra={_CUSTOM_PRED: "custom-value"})] = predicate(
        SCHEMA["val"]
    )


class TestSHACLGeneration:
    def test_shape_has_node_shape_type(self) -> None:
        g = MovieView.to_shacl()
        shapes = list(g.subjects(RDF.type, SH.NodeShape))
        # MovieView + nested PersonView
        assert len(shapes) == 2

    def test_target_class_set(self) -> None:
        g = MovieView.to_shacl()
        targets = set(g.objects(predicate=SH.targetClass))
        assert SCHEMA["Movie"] in targets

    def test_required_field_cardinality(self) -> None:
        """Required str field → minCount 1, maxCount 1."""
        g = MovieView.to_shacl()
        prop = _find_property(g, SCHEMA["name"])
        assert prop is not None
        assert _literal_value(g, prop, SH.minCount) == 1
        assert _literal_value(g, prop, SH.maxCount) == 1

    def test_optional_field_cardinality(self) -> None:
        """Optional int field → maxCount 1, no minCount."""
        g = MovieView.to_shacl()
        prop = _find_property(g, SCHEMA["year"])
        assert prop is not None
        mins = list(g.objects(prop, SH.minCount))
        assert len(mins) == 0
        assert _literal_value(g, prop, SH.maxCount) == 1

    def test_multi_valued_field(self) -> None:
        """set[str] → minCount 1, no maxCount."""
        g = MovieView.to_shacl()
        prop = _find_property(g, SCHEMA["genre"])
        assert prop is not None
        assert _literal_value(g, prop, SH.minCount) == 1
        maxes = list(g.objects(prop, SH.maxCount))
        assert len(maxes) == 0

    def test_datatype_for_scalar(self) -> None:
        g = MovieView.to_shacl()
        prop = _find_property(g, SCHEMA["name"])
        assert prop is not None
        datatypes = list(g.objects(prop, SH.datatype))
        assert XSD.string in datatypes

    def test_nested_model_has_class_constraint(self) -> None:
        g = MovieView.to_shacl()
        prop = _find_property(g, SCHEMA["director"])
        assert prop is not None
        classes = list(g.objects(prop, SH["class"]))
        assert SCHEMA["Person"] in classes

    def test_custom_shape_uri(self) -> None:
        shape_uri = URIRef("http://example.org/shapes/MovieShape")
        g = MovieView.to_shacl(shape_uri=shape_uri)
        assert (shape_uri, RDF.type, SH.NodeShape) in g


class TestAnnotatedSHACLConstraints:
    """Tests for Annotated[..., SHConstraint(...)] overrides."""

    def test_datatype_override(self) -> None:
        """SHConstraint(datatype=...) overrides the default XSD type."""

        class BudgetView(GraphModel):
            budget: Annotated[
                int | None, SHConstraint(datatype=XSD.nonNegativeInteger)
            ] = predicate(SCHEMA["budget"])

        g = BudgetView.to_shacl()
        prop = _find_property(g, SCHEMA["budget"])
        assert prop is not None
        datatypes = list(g.objects(prop, SH.datatype))
        assert XSD.nonNegativeInteger in datatypes
        assert XSD.integer not in datatypes

    def test_min_count_override(self) -> None:
        """SHConstraint(min_count=2) overrides the default."""

        class TagView(GraphModel):
            tags: Annotated[set[str], SHConstraint(min_count=2)] = predicate(
                SCHEMA["tag"]
            )

        g = TagView.to_shacl()
        prop = _find_property(g, SCHEMA["tag"])
        assert prop is not None
        assert _literal_value(g, prop, SH.minCount) == 2

    def test_max_count_override(self) -> None:
        """SHConstraint(max_count=5) on a multi-valued field."""

        class TagView(GraphModel):
            tags: Annotated[set[str], SHConstraint(max_count=5)] = predicate(
                SCHEMA["tag"]
            )

        g = TagView.to_shacl()
        prop = _find_property(g, SCHEMA["tag"])
        assert prop is not None
        assert _literal_value(g, prop, SH.maxCount) == 5

    def test_pattern_constraint(self) -> None:
        class EmailView(GraphModel):
            email: Annotated[str, SHConstraint(pattern=r"^.+@.+\..+$")] = predicate(
                SCHEMA["email"]
            )

        g = EmailView.to_shacl()
        prop = _find_property(g, SCHEMA["email"])
        assert prop is not None
        patterns = list(g.objects(prop, SH.pattern))
        assert len(patterns) == 1
        assert str(patterns[0]) == r"^.+@.+\..+$"

    def test_min_max_inclusive(self) -> None:
        class RatingView(GraphModel):
            rating: Annotated[int, SHConstraint(min_inclusive=1, max_inclusive=10)] = (
                predicate(SCHEMA["rating"])
            )

        g = RatingView.to_shacl()
        prop = _find_property(g, SCHEMA["rating"])
        assert prop is not None
        assert _literal_value(g, prop, SH.minInclusive) == 1
        assert _literal_value(g, prop, SH.maxInclusive) == 10

    def test_min_max_length(self) -> None:
        class CodeView(GraphModel):
            code: Annotated[str, SHConstraint(min_length=3, max_length=10)] = predicate(
                SCHEMA["code"]
            )

        g = CodeView.to_shacl()
        prop = _find_property(g, SCHEMA["code"])
        assert prop is not None
        assert _literal_value(g, prop, SH.minLength) == 3
        assert _literal_value(g, prop, SH.maxLength) == 10

    def test_name_and_description(self) -> None:
        class LabeledView(GraphModel):
            title: Annotated[
                str, SHConstraint(name="Title", description="The title of the thing")
            ] = predicate(SCHEMA["title"])

        g = LabeledView.to_shacl()
        prop = _find_property(g, SCHEMA["title"])
        assert prop is not None
        names = [str(v) for v in g.objects(prop, SH.name)]
        assert "Title" in names
        descs = [str(v) for v in g.objects(prop, SH.description)]
        assert "The title of the thing" in descs

    def test_node_kind(self) -> None:
        class LinkView(GraphModel):
            url: Annotated[str, SHConstraint(node_kind=SH.IRI)] = predicate(
                SCHEMA["url"]
            )

        g = LinkView.to_shacl()
        prop = _find_property(g, SCHEMA["url"])
        assert prop is not None
        kinds = list(g.objects(prop, SH.nodeKind))
        assert SH.IRI in kinds

    def test_class_override(self) -> None:
        """SHConstraint(class_=...) overrides nested model inference."""

        class RefView(GraphModel):
            related: Annotated[str, SHConstraint(class_=SCHEMA["Thing"])] = predicate(
                SCHEMA["related"]
            )

        g = RefView.to_shacl()
        prop = _find_property(g, SCHEMA["related"])
        assert prop is not None
        classes = list(g.objects(prop, SH["class"]))
        assert SCHEMA["Thing"] in classes
        # Should NOT have the default xsd:string datatype
        datatypes = list(g.objects(prop, SH.datatype))
        assert len(datatypes) == 0

    def test_extra_dict_constraints(self) -> None:
        """SHConstraint(extra={...}) adds arbitrary SHACL triples."""
        g = _ExtraCustomView.to_shacl()
        prop = _find_property(g, SCHEMA["val"])
        assert prop is not None
        vals = [str(v) for v in g.objects(prop, _CUSTOM_PRED)]
        assert "custom-value" in vals


# -- Helpers ---------------------------------------------------------------


def _find_property(g, path_uri):
    """Find the sh:property blank node for a given sh:path."""
    for shape in g.subjects(RDF.type, SH.NodeShape):
        for prop in g.objects(shape, SH.property):
            paths = list(g.objects(prop, SH.path))
            if path_uri in paths:
                return prop
    return None


def _literal_value(g, subject, pred):
    """Get a single literal's Python value for a subject+predicate."""
    vals = list(g.objects(subject, pred))
    if vals:
        return vals[0].toPython()
    return None
