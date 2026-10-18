"""The decree note stays an analogy of deadlines, not a compliance claim."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pp86_note_is_an_analogy_for_dispatch_objects() -> None:
    text = (ROOT / "docs" / "pp86_horizon_analogy.md").read_text(encoding="utf-8")
    assert "постановлению не соответствует" in text
    assert "объектах диспетчеризации" in text
    assert "31 августа" in text
    assert "24-го числа" in text
    assert "слово «неделя» не найдено" in text
    assert "FrozenAssignment" in text
