"""Resource-boundary and identity regressions for the final audit pass."""

from datetime import UTC, datetime, timedelta

import pytest

from synaps_gridplan.adapter import to_schedule_problem
from synaps_gridplan.baselines import plan_fifo
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.model import Asset, Crew, FrozenAssignment, GridPlanProblem, MaintenanceJob


@pytest.fixture
def planned():
    start = datetime(2026, 9, 1, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    problem = GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[MaintenanceJob(external_ref="J", asset_id=asset.id, duration_min=60)],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=1),
    )
    outcome = plan_fifo(problem)
    assert outcome.ok
    return problem, outcome


def test_setup_limit_is_checked_before_allocating_states(planned, monkeypatch) -> None:
    problem, _ = planned
    monkeypatch.setattr("synaps_gridplan.adapter.MAX_SCHEDULE_SETUP_ENTRIES", 3)

    def allocation_would_be_too_early(*_args):
        pytest.fail("adapter allocated IDs before checking the quadratic setup limit")

    monkeypatch.setattr("synaps_gridplan.adapter._sid", allocation_would_be_too_early)
    with pytest.raises(ValueError, match="rejected before allocation"):
        to_schedule_problem(problem)


def test_setup_limit_accepts_the_exact_boundary(planned, monkeypatch) -> None:
    problem, _ = planned
    # One crew, states L and idle: 1 * 2**2 = four entries, including diagonals.
    monkeypatch.setattr("synaps_gridplan.adapter.MAX_SCHEDULE_SETUP_ENTRIES", 4)
    compiled, _ = to_schedule_problem(problem)
    assert len(compiled.setup_matrix) == 4


def test_duplicate_compiled_ids_do_not_pass_a_set_only_comparison(planned) -> None:
    problem, outcome = planned
    compiled = outcome.schedule_problem.model_copy(
        update={
            "operations": [
                *outcome.schedule_problem.operations,
                outcome.schedule_problem.operations[0],
            ],
        }
    )
    violations = check_gridplan_constraints(
        problem,
        schedule_problem=compiled,
        result=outcome.schedule,
        id_map=outcome.id_map,
    )
    assert [v.kind for v in violations] == ["INVALID_ID_MAP"]


@pytest.mark.parametrize("conflicting, unchanged", [(False, 1), (True, 0)])
def test_frozen_diff_counts_obligations_not_duplicate_rows(planned, conflicting, unchanged) -> None:
    problem, outcome = planned
    assignment = outcome.schedule.assignments[0]
    frozen = FrozenAssignment(
        job_id=problem.jobs[0].id,
        crew_id=problem.crews[0].id,
        start=assignment.start_time,
        end=assignment.end_time,
    )
    other = frozen.model_copy()
    if conflicting:
        other = frozen.model_copy(
            update={
                "start": frozen.start + timedelta(minutes=1),
                "end": frozen.end + timedelta(minutes=1),
            }
        )
    result = diff_plans(
        base=outcome.schedule,
        repaired=outcome.schedule,
        id_map=outcome.id_map,
        frozen=[frozen, other],
    )
    assert result["frozen_job_count"] == 1
    assert result["churn"]["unchanged_frozen"] == unchanged
