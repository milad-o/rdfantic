"""XSD type mapping edge cases (#12).

Verifies datetime, date, and Decimal types map to correct XSD datatypes.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from rdflib import XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class DateView(GraphModel):
    born: date | None = predicate(SCHEMA["birthDate"])


class DateTimeView(GraphModel):
    created: datetime | None = predicate(SCHEMA["dateCreated"])


class DecimalView(GraphModel):
    price: Decimal | None = predicate(SCHEMA["price"])


class TestDateRoundTrip:
    def test_date_read_from_typed_literal(self) -> None:
        """date fields should round-trip if rdflib handles xsd:date."""
        g = Graph()
        g.add(
            (
                EX["x"],
                SCHEMA["birthDate"],
                Literal(date(1990, 1, 15), datatype=XSD.date),
            )
        )

        view = DateView.from_graph(g, EX["x"])
        assert view.born == date(1990, 1, 15)

        g2 = view.to_graph(subject=EX["x"])
        objs = list(g2.objects(EX["x"], SCHEMA["birthDate"]))
        assert len(objs) == 1

    def test_date_write_produces_xsd_date(self) -> None:
        """Writing a date value should produce xsd:date datatype."""
        view = DateView(born=date(2000, 6, 1))
        triples = view.to_triples(subject=EX["x"])
        date_triples = [(s, p, o) for s, p, o in triples if p == SCHEMA["birthDate"]]
        assert len(date_triples) == 1
        obj = date_triples[0][2]
        assert isinstance(obj, Literal)
        assert obj.datatype == XSD.date


class TestDateTimeRoundTrip:
    def test_datetime_write_produces_xsd_dateTime(self) -> None:
        """Writing a datetime value should produce xsd:dateTime datatype."""
        view = DateTimeView(created=datetime(2025, 3, 15, 10, 30, 0))
        triples = view.to_triples(subject=EX["x"])
        dt_triples = [(s, p, o) for s, p, o in triples if p == SCHEMA["dateCreated"]]
        assert len(dt_triples) == 1
        obj = dt_triples[0][2]
        assert isinstance(obj, Literal)
        assert obj.datatype == XSD.dateTime

    def test_datetime_round_trip(self) -> None:
        """datetime values should round-trip through the graph."""
        ts = datetime(2025, 3, 15, 10, 30, 0)
        view = DateTimeView(created=ts)
        g = view.to_graph(subject=EX["x"])

        restored = DateTimeView.from_graph(g, EX["x"])
        assert restored.created == ts


class TestDecimalPrecision:
    def test_decimal_preserves_precision(self) -> None:
        """Decimal values should preserve precision."""
        g = Graph()
        g.add(
            (EX["x"], SCHEMA["price"], Literal(Decimal("19.99"), datatype=XSD.decimal))
        )

        view = DecimalView.from_graph(g, EX["x"])
        assert view.price == Decimal("19.99")

    def test_decimal_write_produces_xsd_decimal(self) -> None:
        """Writing a Decimal should produce xsd:decimal datatype."""
        view = DecimalView(price=Decimal("42.00"))
        triples = view.to_triples(subject=EX["x"])
        price_triples = [(s, p, o) for s, p, o in triples if p == SCHEMA["price"]]
        assert len(price_triples) == 1
        obj = price_triples[0][2]
        assert isinstance(obj, Literal)
        assert obj.datatype == XSD.decimal
