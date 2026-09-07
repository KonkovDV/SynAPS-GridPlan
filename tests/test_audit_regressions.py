"""Regression probes for the independent-checker and repair trust boundaries."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from synaps.model import Assignment

from synaps_gridplan.adapter import compile_frozen_assignments, to_schedule_problem
from synaps_gridplan.baselines import plan_fifo
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.model import (
    Asset,
    Crew,
    FrozenAssignment,
    GridPlanProblem,
    MaintenanceJob,
    OutageWindow,
)
from synaps_gridplan.planner import replan_after_disruption

T0 = datetime(2026, 9, 1, 6, tzinfo=UTC)


def problem_fixture() -> GridPlanProblem:
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    return GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[
            MaintenanceJob(external_ref=ref, asset_id=asset.id, duration_min=60)
            for ref in ("J1", "J2")
        ],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + timedelta(days=1),
    )


def test_duplicate_job_identity_is_rejected() -> None:
    raw = problem_fixture().model_dump(mode="json")
    raw["jobs"][1]["id"] = raw["jobs"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        GridPlanProblem.model_validate(raw)


def test_missing_job_mapping_is_not_an_empty_success() -> None:
    problem = problem_fixture()
    schedule, mapping = to_schedule_problem(problem)
    violations = check_gridplan_constraints(
        problem,
        schedule_problem=schedule,
        result=SimpleNamespace(assignments=[]),
        id_map={key: value for key, value in mapping.items() if not key.startswith("job:")},
    )
    assert violations, "An incomplete adapter map must fail closed, not erase every job"


def test_clearance_intersects_job_release_and_hard_finish() -> None:
    problem = problem_fixture()
    job = problem.jobs[0].model_copy(
        update={
            "interruption_required": True,
            "release_date": T0 + timedelta(hours=2),
            "latest_finish": T0 + timedelta(hours=5),
        }
    )
    problem = problem.model_copy(
        update={
            "jobs": [job],
            "outage_windows": [
                OutageWindow(asset_id=job.asset_id, start=T0, end=T0 + timedelta(hours=8))
            ],
        }
    )
    schedule, _ = to_schedule_problem(problem)
    assert schedule.operations[0].earliest_start == job.release_date
    assert schedule.operations[0].latest_finish == job.latest_finish


def test_mutable_frozen_row_is_not_compiled_as_a_lock() -> None:
    problem = problem_fixture()
    row = FrozenAssignment(
        job_id=problem.jobs[0].id,
        crew_id=problem.crews[0].id,
        start=T0,
        end=T0 + timedelta(hours=1),
        immutable=False,
    )
    problem = problem.model_copy(update={"frozen_assignments": [row]})
    schedule, mapping = to_schedule_problem(problem)
    assert compile_frozen_assignments(problem, schedule, mapping) == []


def test_repair_recompiles_changed_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    problem = problem_fixture()
    base = plan_fifo(problem)
    changed = problem.model_copy(
        update={"jobs": [problem.jobs[0].model_copy(update={"duration_min": 120}), problem.jobs[1]]}
    )
    monkeypatch.setattr("synaps_gridplan.planner.repair_schedule", lambda *a, **kw: base.schedule)
    repaired = replan_after_disruption(
        changed, base_outcome=base, disrupted_job_ids=[problem.jobs[0].id]
    )
    op_id = repaired.id_map[f"job:{problem.jobs[0].id}"]
    op = next(op for op in repaired.schedule_problem.operations if op.id == op_id)
    assert op.base_duration_min == 120
    assert base.schedule_problem.operations[0].base_duration_min == 60


def test_disruption_does_not_unlock_explicit_immutable_row(monkeypatch: pytest.MonkeyPatch) -> None:
    problem = problem_fixture()
    row = FrozenAssignment(
        job_id=problem.jobs[0].id,
        crew_id=problem.crews[0].id,
        start=T0 + timedelta(hours=2),
        end=T0 + timedelta(hours=3),
    )
    problem = problem.model_copy(update={"frozen_assignments": [row]})
    base = plan_fifo(problem, apply_frozen=True)
    op_id = base.id_map[f"job:{row.job_id}"]
    moved = base.schedule.model_copy(
        update={
            "assignments": [
                Assignment(
                    operation_id=op_id,
                    work_center_id=base.id_map[f"crew:{row.crew_id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(hours=1),
                    setup_minutes=0,
                )
                if assignment.operation_id == op_id
                else assignment.model_copy(deep=True)
                for assignment in base.schedule.assignments
            ]
        }
    )
    monkeypatch.setattr("synaps_gridplan.planner.repair_schedule", lambda *a, **kw: moved)
    repaired = replan_after_disruption(
        problem, base_outcome=base, disrupted_job_ids=[row.job_id]
    )
    assert not repaired.verified_feasible
    assert "FROZEN_ASSIGNMENT_CONFLICT" in repaired.metadata["gridplan_violation_kinds"]
