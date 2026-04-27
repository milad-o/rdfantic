"""Recursive SHACL generation (#22).

model_to_shacl recursively generates NodeShapes for nested GraphModel
fields so that pySHACL can validate nested data.
"""

from __future__ import annotations

from rdflib import RDF, SH, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")


class InnerView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])


class OuterView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    title: str = predicate(SCHEMA["name"])
    director: InnerView = predicate(SCHEMA["director"])


class SelfRefView(GraphModel):
    rdf_type = SCHEMA["Node"]
    label: str = predicate(SCHEMA["label"])
    next_node: SelfRefView | None = predicate(SCHEMA["next"])


class TestShaclRecursion:
    def test_nested_model_shape_generated(self) -> None:
        """Both OuterView and InnerView NodeShapes are generated."""
        shacl_graph = OuterView.to_shacl()

        node_shapes = list(shacl_graph.subjects(RDF.type, SH.NodeShape))
        assert len(node_shapes) == 2

        # Both target classes should be present
        targets = set(shacl_graph.objects(predicate=SH.targetClass))
        assert SCHEMA["Movie"] in targets
        assert SCHEMA["Person"] in targets

    def test_self_referencing_shacl_terminates(self) -> None:
        """Self-referencing model produces exactly one shape, no infinite loop."""
        shacl_graph = SelfRefView.to_shacl()

        node_shapes = list(shacl_graph.subjects(RDF.type, SH.NodeShape))
        assert len(node_shapes) == 1
