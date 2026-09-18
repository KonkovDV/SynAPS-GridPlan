"""Guards for the evidence-first truth pass (18 Sep 2026)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_claims_registry_exists_and_uses_allowed_statuses() -> None:
    text = (ROOT / "docs" / "CLAIMS_REGISTRY.md").read_text(encoding="utf-8")
    assert "0.1.8" in text
    assert "6178c93b705ff58be21fa74a98651883a2da1169" in text
    assert "187-ФЗ" in text
    assert "ГОСТ Р 58048-2017" in text
    assert "ISO 16290" in text
    assert "withdrawn как «партнёр/заказчик GridPlan»" in text
    for status in ("verified", "assumption", "target", "withdrawn"):
        assert f"`{status}`" in text or status in text


def test_application_is_marked_historical_and_not_a_rosseti_partnership() -> None:
    text = (ROOT / "APPLICATION.md").read_text(encoding="utf-8")
    assert "Исторический пакет" in text
    assert "не партнёр" in text
    assert "0.1.8" in text
    assert "187-ФЗ" in text
    assert "APPLICATION_TOIR_SCENARIO.md" in text


def test_academy_does_not_point_at_open_draft_prs() -> None:
    text = (ROOT / "ACADEMY_APPLICATION.md").read_text(encoding="utf-8")
    assert "draft PR #12" not in text
    assert "14 сентября" in text
    assert "внутренний freeze" in text
    assert "0.1.8" in text
    assert "ГОСТ Р 58048-2017" in text


def test_readme_points_at_claims_registry() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/CLAIMS_REGISTRY.md" in text
    assert "scripts/evidence_bundle.py" in text
    assert "ГОСТ Р 58048" in text
