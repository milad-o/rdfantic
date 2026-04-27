"""JSON / model_dump round-trip edge cases (#23).

subject has exclude=True so it disappears from model_dump output.
After model_dump → model_validate, the subject is lost.
"""

from __future__ import annotations

from rdflib import Namespace

from rdfantic import GraphModel, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class LabelView(GraphModel):
    label: str = predicate(SCHEMA["name"])


class TestModelDumpSubject:
    def test_subject_excluded_from_dump(self) -> None:
        """Subject field has exclude=True so it shouldn't appear in dump."""
        view = LabelView(label="Test", subject=EX["x"])
        data = view.model_dump()
        assert "subject" not in data

    def test_subject_lost_after_validate(self) -> None:
        """After model_dump → model_validate, subject is gone."""
        view = LabelView(label="Test", subject=EX["x"])
        data = view.model_dump()
        restored = LabelView.model_validate(data)
        assert restored.subject is None
