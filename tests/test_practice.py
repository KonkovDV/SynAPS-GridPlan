"""Lock the world-practice mapping: real citations, no overclaim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.cli import main
from synaps_gridplan.practice import (
    ALIGNMENT,
    APPLICABILITY_LIMITS,
    ELECTRICAL_SECURITY,
    OVERCLAIM_DENYLIST,
    PRACTICE_LAYER,
    REFS,
    practice_snapshot,
)
from synaps_gridplan.report import render_report
from synaps_gridplan.synthetic import synthesize_feeder

ROOT = Path(__file__).resolve().parents[1]
PRACTICE_MD = ROOT / "PRACTICE.md"


def test_refs_are_https_and_not_placeholder_arxiv() -> None:
    assert REFS
    keys = [r.key for r in REFS]
    assert len(keys) == len(set(keys))
    for ref in REFS:
        assert ref.url.startswith("https://")
        assert "2607." not in ref.url
        assert ref.year >= 2013
        assert ref.kind in {"paper", "operator", "industry", "analogue"}
        assert ref.citation.strip()


def test_alignment_covers_every_ref() -> None:
    assert {m.key for m in ALIGNMENT} == {r.key for r in REFS}


def test_electrical_security_is_out_of_scope() -> None:
    assert ELECTRICAL_SECURITY == "out_of_scope"
    assert PRACTICE_LAYER == "combinatorial_crew_window_mutex_freeze"
    snap = practice_snapshot()
    assert snap["electrical_security"] == "out_of_scope"
    assert snap["layer"] == PRACTICE_LAYER
    assert snap["ref_keys"] == [r.key for r in REFS]


def test_goel_doi_is_the_verified_ejor_article() -> None:
    goel = next(r for r in REFS if r.key == "goel_meisel_2013")
    assert goel.url.endswith("10.1016/j.ejor.2013.05.021")
    model = (ROOT / "src" / "synaps_gridplan" / "model.py").read_text(encoding="utf-8")
    assert "10.1016/j.ejor.2013.05.021" in model


def test_barral_doi_is_stable_springer_lncs() -> None:
    """barral_cpaior_2024 must point to the chapter DOI, not a volume or slides.

    EasyChair smart-slide links are transient. CPAIOR 2024 is two LNCS volumes:
    Part I = LNCS 14742 (10.1007/978-3-031-60597-0), Part II = LNCS 14743
    (10.1007/978-3-031-60599-4). Barral et al. is LNCS 14742 pp. 34–50,
    chapter DOI 10.1007/978-3-031-60597-0_3 (PolyPublie / Springer).
    """
    chapter = "https://doi.org/10.1007/978-3-031-60597-0_3"
    barral = next(r for r in REFS if r.key == "barral_cpaior_2024")
    assert barral.url == chapter, (
        f"barral_cpaior_2024 URL must be the Springer chapter DOI, got: {barral.url}"
    )
    assert "easychair" not in barral.url.lower()
    assert "60599-4" not in barral.url, (
        "10.1007/978-3-031-60599-4 is CPAIOR 2024 Part II (LNCS 14743), not this paper."
    )
    text = PRACTICE_MD.read_text(encoding="utf-8")
    assert "10.1007/978-3-031-60597-0_3" in text
    assert "10.1007/978-3-031-60599-4" not in text


def test_energies_2025_and_hydro_quebec_are_cited() -> None:
    urls = {r.url for r in REFS}
    assert "https://doi.org/10.3390/en18205454" in urls
    assert "https://doi.org/10.4230/LIPIcs.CP.2022.34" in urls
    text = PRACTICE_MD.read_text(encoding="utf-8")
    assert "10.3390/en18205454" in text
    assert "Hydro-Qu\u00e9bec" in text
    assert "\u010cEZ" in text
    assert "out of scope" in text.lower()


def test_mapping_does_not_overclaim_capabilities() -> None:
    implemented = " ".join(m.we_implement.lower() for m in ALIGNMENT)
    for phrase in OVERCLAIM_DENYLIST:
        assert phrase not in implemented, phrase
    for row in ALIGNMENT:
        low = row.we_implement.lower()
        assert "saidi" not in low
        assert "n-1" not in low
        assert "pilot" not in low


def test_practice_md_names_forbidden_topics_as_limits() -> None:
    text = PRACTICE_MD.read_text(encoding="utf-8")
    assert "N-1" in text
    assert "SAIDI" in text
    assert "INFIMUM" in text
    assert "not" in text.lower()


def test_plan_metadata_carries_practice_snapshot() -> None:
    problem = synthesize_feeder(mode="small", seed=12)
    outcome = plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    practice = outcome.metadata["practice"]
    assert practice["layer"] == PRACTICE_LAYER
    assert practice["electrical_security"] == "out_of_scope"
    assert "popovic_cp_2022" in practice["ref_keys"]
    report_md = render_report(outcome, fmt="markdown")
    assert "combinatorial crew/window/mutex/freeze" in report_md
    payload = json.loads(render_report(outcome, fmt="json"))
    assert payload["practice"]["electrical_security"] == "out_of_scope"
    assert payload["applicability_limits"] == list(APPLICABILITY_LIMITS)


def test_cli_practice_prints_citations(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["practice"]) == 0
    out = capsys.readouterr().out
    assert "popovic_cp_2022" in out
    assert "10.4230/LIPIcs.CP.2022.34" in out
    assert "10.3390/en18205454" in out
    assert ELECTRICAL_SECURITY in out
    assert "PRACTICE.md" in out


def test_dual_feed_and_m9_are_cited_as_limits() -> None:
    urls = {r.url for r in REFS}
    assert any("uptimeinstitute.com" in u for u in urls)
    assert any("meduza.io" in u for u in urls)
    text = PRACTICE_MD.read_text(encoding="utf-8")
    assert "Concurrently Maintainable" in text or "concurrent maintainability" in text.lower()
    assert "MMTS-9" in text
    assert "not a reconstruction" in text.lower() or "not a reconstruction of M9" in text.lower()
    assert "\u041a\u0438\u0440\u0438\u0435\u043d\u043a\u043e" not in text
    assert "\u0421\u0430\u0432\u0438\u043d\u043e\u0432\u0441\u043a\u0438\u0439" not in text
    assert "dual-feed-hall" in text
