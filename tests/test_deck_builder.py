"""Deck facts come from jury_report.md / versions.py / git describe."""

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


def test_git_describe_is_nonempty() -> None:
    desc = _load("gridplan_repo_describe", "scripts/repo_describe.py")
    value = desc.git_describe()
    assert value
    assert " " not in value


def test_deck_facts_match_committed_jury_and_versions() -> None:
    facts_mod = _load("gridplan_deck_facts", "scripts/deck_facts.py")
    facts = facts_mod.build_facts()
    from synaps_gridplan.versions import GRIDPLAN_VERSION, ISO16290_TRL, SYNAPS_COMMIT

    assert facts["gridplan_version"] == GRIDPLAN_VERSION
    assert facts["iso16290_trl"] == ISO16290_TRL
    assert facts["synaps_commit"] == SYNAPS_COMMIT
    assert facts["author"] == "Коньков Д.В."
    assert facts["company"] == "SynAPS"
    assert facts["budget_status"] == "assumption"
    jury = facts["jury"]
    assert jury["jobs"] == 55
    assert jury["fifo_hard"] == 107
    assert jury["greed_hard"] == 0
    assert jury["cpsat_status"] == "optimal"
    assert jury["cpsat_hard"] == 0


def test_committed_deck_text_matches_submission_pptx() -> None:
    extract = _load("gridplan_extract_deck", "scripts/extract_deck_text.py")
    deck = ROOT / "SynAPS_GridPlan.pptx"
    assert deck.is_file()
    assert not (ROOT / "SynAPS_v8_Evidence.pptx").exists()
    text = extract.render(deck)
    committed = (ROOT / "docs" / "DECK_TEXT.txt").read_text(encoding="utf-8")
    assert text == committed
    assert "CPSAT-30" in text
    assert "0.1.8" in text
    assert "107" in text
    assert "etechhubspb.ru/accelerator" in text
