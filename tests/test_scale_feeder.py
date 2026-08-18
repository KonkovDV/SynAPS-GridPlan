"""Generic feeder scale: campaign packing so GREED verifies at 200 and 600.

`small --seed 42` remains the fail-closed ASSET_OVERLAP demo. Medium/stress
are packed as one linear chain per asset, one interruption, stock ≥ demand.
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
    interrupt = [j for j in problem.jobs if j.interruption_required]
    assert len(interrupt) == 80
    for job in problem.jobs:
        assert len(job.predecessor_job_ids) <= 1


def test_medium_greed_verified_clean() -> None:
    problem = synthesize_feeder(mode="medium", seed=12)
    assert len(problem.jobs) == 200
    assert len(problem.outage_windows) == 40
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    assert len(outcome.schedule.assignments) == 200
    assert outcome.verified_feasible
    assert outcome.hard_violation_count == 0


def test_stress_greed_verified_clean() -> None:
    problem = synthesize_feeder(mode="stress", seed=12)
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    assert len(outcome.schedule.assignments) == 600
    assert outcome.verified_feasible
    assert outcome.hard_violation_count == 0


def test_medium_fifo_breaks_windows() -> None:
    problem = synthesize_feeder(mode="medium", seed=12)
    outcome = plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    assert not outcome.verified_feasible
    assert outcome.hard_violation_count >= 1


def test_committed_scale_report_shows_verified_campaign() -> None:
    text = SCALE_REPORT.read_text(encoding="utf-8")
    assert "200" in text
    assert "600" in text
    assert "GREED" in text
    assert "50k" in text
    assert "seed 42" in text
