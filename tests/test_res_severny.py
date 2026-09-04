"""Demo-instance guard: РЭС «Северный» must stay GREED-clean and FIFO-broken.

Protects the jury benchmark from regressions in adapter/planner semantics
(first-window release/due, chain compilation, fail-closed post-checks).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))

from res_severny_benchmark import build_res_problem  # noqa: E402

from synaps_gridplan.baselines import plan_with_config  # noqa: E402


@pytest.fixture(scope="module")
def res_problem():
    return build_res_problem()


def test_res_instance_shape(res_problem) -> None:
    assert len(res_problem.assets) == 39
    assert len(res_problem.jobs) == 55
    assert len(res_problem.crews) == 7
    assert len(res_problem.outage_windows) > 60


def test_res_greed_verified_clean(res_problem) -> None:
    outcome = plan_with_config(res_problem, solver_config="GREED", apply_frozen=False)
    assert outcome.verified_feasible
    assert outcome.metadata.get("gridplan_violations", []) == []
    assert (outcome.metadata.get("engine_violations") or []) == []
    assert outcome.hard_violation_count == 0
    assert len(outcome.schedule.assignments) == len(res_problem.jobs)


def test_res_fifo_breaks_hard_rules(res_problem) -> None:
    outcome = plan_with_config(res_problem, solver_config="FIFO", apply_frozen=False)
    violations = outcome.metadata.get("gridplan_violations", [])
    engine = outcome.metadata.get("engine_violations") or []
    assert not outcome.verified_feasible
    assert len(violations) >= 20  # naive rule must visibly break windows
    assert outcome.hard_violation_count == len(violations) + len(engine)


def test_res_windowed_job_repair_feasible(res_problem) -> None:
    """Product-level guard for the upstream fix: repair of a windowed job
    (release_date bound in IncrementalRepair) must return a verified plan."""
    from synaps_gridplan.planner import replan_after_disruption

    base = plan_with_config(res_problem, solver_config="GREED", apply_frozen=False)
    win_job = next(j for j in res_problem.jobs if j.interruption_required)
    repaired = replan_after_disruption(
        res_problem, base_outcome=base, disrupted_job_ids=[win_job.id]
    )
    assert repaired.status == "feasible"
    assert repaired.verified_feasible
    assert repaired.metadata.get("gridplan_violations", []) == []
    assert (repaired.metadata.get("engine_violations") or []) == []


@pytest.mark.slow
def test_res_cpsat_proves_optimal_makespan(res_problem) -> None:
    """CP-SAT must prove OPTIMAL and its dual bound must equal achieved makespan."""
    outcome = plan_with_config(res_problem, solver_config="CPSAT-30", apply_frozen=False)
    assert outcome.status == "optimal"
    assert outcome.verified_feasible
    bound = outcome.metadata.get("best_objective_bound")
    assert outcome.metadata.get("objective_bound_units") == "makespan_minutes"
    assert bound is not None
    assert outcome.schedule.objective.makespan_minutes == pytest.approx(bound, abs=1.0)
    # Heuristic must match the proven optimum on the primary criterion.
    greed = plan_with_config(res_problem, solver_config="GREED", apply_frozen=False)
    assert greed.schedule.objective.makespan_minutes == pytest.approx(bound, abs=1.0)
