"""Banned-claim linter and generated pytest count."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_banned_list_covers_p0_phrases() -> None:
    text = (ROOT / "docs" / "BANNED_CLAIMS.txt").read_text(encoding="utf-8")
    for phrase in (
        "до 40% планов",
        "подтверждённая технология",
        "первые в нише",
        "в реальном времени",
        "с первого раза",
        "3/3 автотестов",
        "нормы непрерывного отдыха",
        "Минтруд",
        "СНиП",
    ):
        assert phrase in text


def test_live_pack_has_no_banned_claim_hits() -> None:
    lint = _load("gridplan_lint_claims", "scripts/lint_claims.py")
    assert lint.main() == 0


def test_linter_flags_unnegated_phrase() -> None:
    lint = _load("gridplan_lint_claims", "scripts/lint_claims.py")
    hits = lint.find_hits("GREED режет до 40% планов на типичном РЭС.", lint.load_phrases())
    assert any(phrase == "до 40% планов" for _, phrase in hits)
    clean = lint.find_hits("Не копировать «до 40% планов» в слайд.", lint.load_phrases())
    assert not any(phrase == "до 40% планов" for _, phrase in clean)


def test_linter_skips_historical_catalog_and_pdf() -> None:
    lint = _load("gridplan_lint_claims", "scripts/lint_claims.py")
    assert lint.skip_path(ROOT / "docs" / "00_README.md")
    assert lint.skip_path(ROOT / "_SUBMIT_MIK_2026_08_18" / "README.md")
    assert lint.skip_path(
        ROOT / "_SUBMIT_MIK_2026_08_18" / "SynAPS-GridPlan-marathon-0.1.4.pdf"
    )
    assert not lint.skip_path(ROOT / "README.md")


def test_test_count_snapshot_matches_collect_only() -> None:
    export = _load("gridplan_export_test_count", "scripts/export_test_count.py")
    expected = export.render(export.collected_count())
    actual = (ROOT / "docs" / "TEST_COUNT.txt").read_text(encoding="utf-8")
    assert actual == expected
