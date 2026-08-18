"""Generic feeder scale: search time and fail-closed checker, not a verified month.

The checked campaign-shaped demo remains РЭС «Северный» (55 jobs).
`medium` (200) and `stress` (600) are random-window feeders: GREED assigns
every job, the independent checker still rejects the plan.
"""

from __future__ import annotations

from pathlib import Path

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.synthetic import synthesize_feeder

ROOT = Path(__file__).resolve().parents[1]
SCALE_REPORT = ROOT / "benchmark" / "results" / "scale_report.md"


def test_stress_instance_shape() -> None:
    problem = synthesize_feeder(mode="stress", seed=12)
    assert len(problem.assets) == 80
    assert len(problem.jobs) == 600
    assert len(problem.crews) == 15
    assert problem.domain_attributes["data_provenance"] == "synthetic"


def test_medium_greed_is_fail_closed() -> None:
    """200-job generic feeder: search finishes, checker must not rubber-stamp."""
    problem = synthesize_feeder(mode="medium", seed=12)
    assert len(problem.jobs) == 200
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    assert len(outcome.schedule.assignments) == 200
    assert not outcome.verified_feasible
    assert outcome.hard_violation_count >= 1


def test_committed_scale_report_does_not_claim_verified_month() -> None:
    text = SCALE_REPORT.read_text(encoding="utf-8")
    assert "55" in text
    assert "200" in text
    assert "600" in text
    assert "не допустимый месячный график" in text
    assert "50k" in text
    assert "verified_feasible" in text or "проверка" in text.lower()
