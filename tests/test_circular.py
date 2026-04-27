"""Circular / self-referencing model tests.

Proves that depth-limited traversal prevents infinite recursion when
a model references itself (directly or indirectly).
"""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


# -- Self-referencing model (direct cycle) ---------------------------------


class EmployeeView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    manager: EmployeeView | None = predicate(SCHEMA["manager"])


# -- Indirect cycle: A → B → A --------------------------------------------


class CityView(GraphModel):
    rdf_type = SCHEMA["City"]
    name: str = predicate(SCHEMA["name"])
    country: CountryView | None = predicate(SCHEMA["country"])


class CountryView(GraphModel):
    rdf_type = SCHEMA["Country"]
    name: str = predicate(SCHEMA["name"])
    capital: CityView | None = predicate(SCHEMA["capital"])


def _employee_graph() -> Graph:
    """Alice → Bob → Carol (no cycle in data, but model type is self-ref)."""
    g = Graph()
    for subj, name, mgr in [
        (EX["alice"], "Alice", EX["bob"]),
        (EX["bob"], "Bob", EX["carol"]),
        (EX["carol"], "Carol", None),
    ]:
        g.add((subj, RDF.type, SCHEMA["Person"]))
        g.add((subj, SCHEMA["name"], Literal(name, datatype=XSD.string)))
        if mgr is not None:
            g.add((subj, SCHEMA["manager"], mgr))
    return g


def _cyclic_employee_graph() -> Graph:
    """Alice → Bob → Alice (actual data cycle)."""
    g = Graph()
    g.add((EX["alice"], RDF.type, SCHEMA["Person"]))
    g.add((EX["alice"], SCHEMA["name"], Literal("Alice", datatype=XSD.string)))
    g.add((EX["alice"], SCHEMA["manager"], EX["bob"]))

    g.add((EX["bob"], RDF.type, SCHEMA["Person"]))
    g.add((EX["bob"], SCHEMA["name"], Literal("Bob", datatype=XSD.string)))
    g.add((EX["bob"], SCHEMA["manager"], EX["alice"]))
    return g


def _city_country_graph() -> Graph:
    """Paris → France → Paris (indirect cycle)."""
    g = Graph()
    g.add((EX["paris"], RDF.type, SCHEMA["City"]))
    g.add((EX["paris"], SCHEMA["name"], Literal("Paris", datatype=XSD.string)))
    g.add((EX["paris"], SCHEMA["country"], EX["france"]))

    g.add((EX["france"], RDF.type, SCHEMA["Country"]))
    g.add((EX["france"], SCHEMA["name"], Literal("France", datatype=XSD.string)))
    g.add((EX["france"], SCHEMA["capital"], EX["paris"]))
    return g


class TestSelfReferenceChain:
    """Self-referencing model with a non-cyclic data chain."""

    def test_unlimited_depth(self) -> None:
        g = _employee_graph()
        alice = EmployeeView.from_graph(g, EX["alice"])

        assert alice.name == "Alice"
        assert alice.manager is not None
        assert alice.manager.name == "Bob"
        assert alice.manager.manager is not None
        assert alice.manager.manager.name == "Carol"
        assert alice.manager.manager.manager is None

    def test_depth_0_stops_nesting(self) -> None:
        g = _employee_graph()
        alice = EmployeeView.from_graph(g, EX["alice"], max_depth=0)

        assert alice.name == "Alice"
        assert alice.manager is None

    def test_depth_1_one_level(self) -> None:
        g = _employee_graph()
        alice = EmployeeView.from_graph(g, EX["alice"], max_depth=1)

        assert alice.name == "Alice"
        assert alice.manager is not None
        assert alice.manager.name == "Bob"
        assert alice.manager.manager is None  # cut off at depth 1


class TestCyclicData:
    """Actual cycles in the data — must not infinite-loop."""

    def test_direct_cycle_with_depth_limit(self) -> None:
        """Alice → Bob → Alice cycle terminates via max_depth."""
        g = _cyclic_employee_graph()
        alice = EmployeeView.from_graph(g, EX["alice"], max_depth=2)

        assert alice.name == "Alice"
        assert alice.manager is not None
        assert alice.manager.name == "Bob"
        # depth 2: Bob's manager is read but *its* manager is cut
        assert alice.manager.manager is not None
        assert alice.manager.manager.name == "Alice"
        assert alice.manager.manager.manager is None

    def test_direct_cycle_depth_1(self) -> None:
        g = _cyclic_employee_graph()
        alice = EmployeeView.from_graph(g, EX["alice"], max_depth=1)

        assert alice.name == "Alice"
        assert alice.manager is not None
        assert alice.manager.name == "Bob"
        assert alice.manager.manager is None

    def test_write_self_ref_model(self) -> None:
        """Writing a self-referencing model produces correct triples."""
        carol = EmployeeView(name="Carol", manager=None)
        bob = EmployeeView(name="Bob", manager=carol)
        alice = EmployeeView(name="Alice", manager=bob)

        g = alice.to_graph(subject=EX["alice"])

        # Should have triples for Alice, Bob, and Carol
        names = {str(o) for o in g.objects(predicate=SCHEMA["name"])}
        assert names == {"Alice", "Bob", "Carol"}


class TestIndirectCycle:
    """A → B → A cycle through different model types."""

    def test_indirect_cycle_with_depth_limit(self) -> None:
        g = _city_country_graph()
        paris = CityView.from_graph(g, EX["paris"], max_depth=2)

        assert paris.name == "Paris"
        assert paris.country is not None
        assert paris.country.name == "France"
        # depth 2: capital is read but *its* country is cut
        assert paris.country.capital is not None
        assert paris.country.capital.name == "Paris"
        assert paris.country.capital.country is None

    def test_indirect_write_round_trip(self) -> None:
        france = CountryView(name="France", capital=None)
        paris = CityView(name="Paris", country=france)

        g = paris.to_graph(subject=EX["paris"])
        restored = CityView.from_graph(g, EX["paris"], max_depth=2)

        assert restored.name == "Paris"
        assert restored.country is not None
        assert restored.country.name == "France"
