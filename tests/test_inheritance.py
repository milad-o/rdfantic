"""Inheritance edge cases (#28).

Verifies that subclass model_fields includes parent fields, ClassVar
rdf_type can be overridden independently, and read/write works with
inherited + new fields.
"""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class BasePersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])


class ExtendedPersonView(BasePersonView):
    rdf_type = SCHEMA["Employee"]
    employee_id: int = predicate(SCHEMA["employeeId"])


class TestInheritance:
    def test_subclass_has_parent_fields(self) -> None:
        """Subclass model_fields should include parent's fields."""
        assert "name" in ExtendedPersonView.model_fields
        assert "employee_id" in ExtendedPersonView.model_fields

    def test_subclass_rdf_type_override(self) -> None:
        """Subclass overrides rdf_type without affecting parent."""
        assert ExtendedPersonView.rdf_type == SCHEMA["Employee"]
        assert BasePersonView.rdf_type == SCHEMA["Person"]

    def test_subclass_read_write(self) -> None:
        """Subclass can read and write with inherited + new fields."""
        g = Graph()
        g.add((EX["emp1"], RDF.type, SCHEMA["Employee"]))
        g.add((EX["emp1"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
        g.add((EX["emp1"], SCHEMA["employeeId"], Literal(42, datatype=XSD.integer)))

        view = ExtendedPersonView.from_graph(g, EX["emp1"])
        assert view.name == "Alice"
        assert view.employee_id == 42

        g2 = view.to_graph(subject=EX["emp1"])
        assert (EX["emp1"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)) in g2
        assert (EX["emp1"], RDF.type, SCHEMA["Employee"]) in g2
