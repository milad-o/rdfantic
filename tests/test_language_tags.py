"""Language-tagged literal edge cases (#11).

str fields still lose the language tag on round-trip (expected — str has
no language slot).  Use LangStr to preserve language tags through the
read → write cycle.
"""

from __future__ import annotations

from rdflib import Graph, Literal, Namespace

from rdfantic import GraphModel, LangStr, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class LabelView(GraphModel):
    label: str = predicate(SCHEMA["name"])


class LangLabelView(GraphModel):
    label: LangStr = predicate(SCHEMA["name"])


class TestStrFieldLanguageTags:
    def test_language_tag_survives_read_as_string(self) -> None:
        """Reading a language-tagged literal into str produces the string value."""
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("Hello", lang="en")))

        view = LabelView.from_graph(g, EX["x"])
        assert view.label == "Hello"

    def test_language_tag_lost_on_round_trip_with_str(self) -> None:
        """Round-tripping through str field loses the lang tag (expected)."""
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("Bonjour", lang="fr")))

        view = LabelView.from_graph(g, EX["x"])
        g2 = view.to_graph(subject=EX["x"])

        objs = list(g2.objects(EX["x"], SCHEMA["name"]))
        assert len(objs) == 1
        obj = objs[0]
        assert isinstance(obj, Literal)
        assert obj.language is None


class TestLangStrField:
    def test_langstr_preserves_language_tag_on_read(self) -> None:
        """LangStr field preserves the language tag from the graph."""
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("Bonjour", lang="fr")))

        view = LangLabelView.from_graph(g, EX["x"])
        assert view.label == "Bonjour"
        assert isinstance(view.label, LangStr)
        assert view.label.language == "fr"

    def test_langstr_round_trip_preserves_tag(self) -> None:
        """LangStr survives a full read → write → read round-trip."""
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("Hello", lang="en")))

        view = LangLabelView.from_graph(g, EX["x"])
        g2 = view.to_graph(subject=EX["x"])

        objs = list(g2.objects(EX["x"], SCHEMA["name"]))
        assert len(objs) == 1
        obj = objs[0]
        assert isinstance(obj, Literal)
        assert obj.language == "en"
        assert str(obj) == "Hello"

    def test_langstr_without_language(self) -> None:
        """LangStr works for plain literals too (language is None)."""
        g = Graph()
        g.add((EX["x"], SCHEMA["name"], Literal("Plain")))

        view = LangLabelView.from_graph(g, EX["x"])
        assert view.label == "Plain"
        assert isinstance(view.label, LangStr)
        assert view.label.language is None

    def test_langstr_constructed_directly(self) -> None:
        """LangStr can be constructed directly and written to graph."""
        view = LangLabelView(label=LangStr("Hola", language="es"))
        g = view.to_graph(subject=EX["x"])

        objs = list(g.objects(EX["x"], SCHEMA["name"]))
        assert len(objs) == 1
        obj = objs[0]
        assert isinstance(obj, Literal)
        assert obj.language == "es"
        assert str(obj) == "Hola"
