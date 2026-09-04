"""Fail-closed catalog fields: release date, eligible crews, unknown ops, duration.

GREED must not report status ``optimal``. Repair rejects a problem whose job
set diverged from the compiled schedule.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from synaps.model import Assignment

from synaps_gridplan.adapter import to_schedule_problem
from synaps_gridplan.baselines import plan_fifo, plan_with_config
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.model import (
    Asset,
    Crew,
    FrozenAssignment,
    GridPlanProblem,
    JobKind,
    MaintenanceJob,
    OutageWindow,
)
from synaps_gridplan.planner import plan_maintenance, replan_after_disruption

T0 = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)
HORIZON = timedelta(days=7)


def _asset(code: str = "A1") -> Asset:
    return Asset(
        code=code,
        name="a",
        asset_class="x",
        location_code=code,
        data_provenance="synthetic",
    )


def _crew(code: str = "C1", quals: list[str] | None = None) -> Crew:
    return Crew(code=code, qualifications=quals or ["q1"], data_provenance="synthetic")


def _job(ref: str, asset: Asset, **kw: object) -> MaintenanceJob:
    kw.setdefault("kind", JobKind.CORRECTIVE)
    kw.setdefault("duration_min", 60)
    kw.setdefault("required_qualifications", ["q1"])
    kw.setdefault("data_provenance", "synthetic")
    return MaintenanceJob(external_ref=ref, asset_id=asset.id, **kw)  # type: ignore[arg-type]


def test_release_date_is_hard() -> None:
    a, c = _asset(), _crew()
    j = _job("J1", a, release_date=T0 + timedelta(days=2))
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule_problem, id_map = to_schedule_problem(p)
    result = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{j.id}"],
                    work_center_id=id_map[f"crew:{c.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=60),
                )
            ]
        },
    )()
    kinds = {
        v.kind
        for v in check_gridplan_constraints(
            p, schedule_problem=schedule_problem, result=result, id_map=id_map
        )
    }
    assert "RELEASE_DATE_VIOLATION" in kinds


def test_eligible_crew_mismatch_is_fail_closed() -> None:
    a = _asset()
    c1, c2 = _crew("C1"), _crew("C2")
    j = _job("J1", a, eligible_crew_ids=[c1.id])
    p = GridPlanProblem(
        assets=[a],
        crews=[c1, c2],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule_problem, id_map = to_schedule_problem(p)
    result = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{j.id}"],
                    work_center_id=id_map[f"crew:{c2.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=60),
                )
            ]
        },
    )()
    kinds = {
        v.kind
        for v in check_gridplan_constraints(
            p, schedule_problem=schedule_problem, result=result, id_map=id_map
        )
    }
    assert "ELIGIBLE_CREW_MISMATCH" in kinds


def test_unknown_operation_assignment_is_fail_closed() -> None:
    a, c = _asset(), _crew()
    j = _job("J1", a)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule_problem, id_map = to_schedule_problem(p)
    ghost = uuid4()
    result = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{j.id}"],
                    work_center_id=id_map[f"crew:{c.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=60),
                ),
                Assignment(
                    operation_id=ghost,
                    work_center_id=id_map[f"crew:{c.id}"],
                    start_time=T0 + timedelta(hours=2),
                    end_time=T0 + timedelta(hours=3),
                ),
            ]
        },
    )()
    kinds = {
        v.kind
        for v in check_gridplan_constraints(
            p, schedule_problem=schedule_problem, result=result, id_map=id_map
        )
    }
    assert "UNKNOWN_OPERATION" in kinds


def test_greed_never_claims_optimal() -> None:
    a, c = _asset(), _crew()
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[_job("J1", a)],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    assert o.status != "optimal"
    assert o.metadata.get("claim_status") != "optimal"


def test_chained_outages_on_distinct_days_per_op_windows() -> None:
    """Order is the union; each Operation keeps its own clearance."""
    a1, a2 = _asset("A1"), _asset("A2")
    c = _crew()
    j1 = _job("J-MON", a1, interruption_required=True, duration_min=120)
    j2 = _job(
        "J-WED",
        a2,
        interruption_required=True,
        duration_min=120,
        predecessor_job_ids=[j1.id],
    )
    wed = T0 + timedelta(days=2)
    mon_end = T0 + timedelta(hours=6)
    wed_end = wed + timedelta(hours=6)
    p = GridPlanProblem(
        assets=[a1, a2],
        crews=[c],
        jobs=[j1, j2],
        outage_windows=[
            OutageWindow(
                asset_id=a1.id,
                start=T0,
                end=mon_end,
                approved=True,
                data_provenance="synthetic",
            ),
            OutageWindow(
                asset_id=a2.id,
                start=wed,
                end=wed_end,
                approved=True,
                data_provenance="synthetic",
            ),
        ],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule, _id_map = to_schedule_problem(p)
    assert len(schedule.orders) == 1
    order = schedule.orders[0]
    assert order.release_date == T0
    assert order.due_date == wed_end
    ops = sorted(schedule.operations, key=lambda op: op.seq_in_order)
    assert ops[0].earliest_start == T0
    assert ops[0].latest_finish == mon_end
    assert ops[1].earliest_start == wed
    assert ops[1].latest_finish == wed_end
    outcome = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    assert outcome.verified_feasible
    assert outcome.metadata.get("gridplan_violations", []) == []


def test_fifo_honors_feasible_frozen() -> None:
    a, c = _asset(), _crew()
    j_frozen = _job("J-FROZEN", a, due_date=T0 + timedelta(hours=1), duration_min=60)
    j_other = _job("J-OTHER", a, due_date=T0 + timedelta(hours=8), duration_min=60)
    pin_start = T0 + timedelta(hours=4)
    pin_end = pin_start + timedelta(minutes=60)
    frozen = FrozenAssignment(
        job_id=j_frozen.id,
        crew_id=c.id,
        start=pin_start,
        end=pin_end,
        immutable=True,
        data_provenance="synthetic",
    )
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j_frozen, j_other],
        frozen_assignments=[frozen],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    off = plan_fifo(p, apply_frozen=False)
    on = plan_fifo(p, apply_frozen=True)
    op = on.id_map[f"job:{j_frozen.id}"]
    pinned = next(x for x in on.schedule.assignments if x.operation_id == op)
    assert pinned.start_time == pin_start
    assert pinned.end_time == pin_end
    assert on.verified_feasible
    off_asn = next(x for x in off.schedule.assignments if x.operation_id == op)
    assert off_asn.start_time == T0
    assert "FROZEN_ASSIGNMENT_CONFLICT" in off.metadata.get("gridplan_violation_kinds", [])


def test_short_duration_is_fail_closed() -> None:
    a, c = _asset(), _crew()
    j = _job("J1", a, duration_min=60)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule_problem, id_map = to_schedule_problem(p)
    result = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{j.id}"],
                    work_center_id=id_map[f"crew:{c.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=10),
                )
            ]
        },
    )()
    kinds = {
        v.kind
        for v in check_gridplan_constraints(
            p, schedule_problem=schedule_problem, result=result, id_map=id_map
        )
    }
    assert "SHORT_DURATION" in kinds
    assert "INVALID_DURATION" not in kinds


def test_explicit_job_priority_is_compiled() -> None:
    a, c = _asset(), _crew()
    j = _job("J1", a, priority=7)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule, _id_map = to_schedule_problem(p)
    assert schedule.orders[0].priority == 7


def test_apply_frozen_is_in_config_hash() -> None:
    a, c = _asset(), _crew()
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[_job("J1", a)],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o1 = plan_maintenance(p, solver_config="GREED", apply_frozen=False)
    o2 = plan_maintenance(p, solver_config="GREED", apply_frozen=True)
    assert o1.metadata["config_hash"] != o2.metadata["config_hash"]


def test_replan_rejects_jobs_not_on_compiled_problem() -> None:
    a, c = _asset(), _crew()
    j1 = _job("J1", a)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j1],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    base = plan_maintenance(p, solver_config="GREED", apply_frozen=False)
    extra = _job("J-NEW", a)
    mutated = p.model_copy(update={"jobs": [j1, extra]})
    repaired = replan_after_disruption(
        mutated,
        base_outcome=base,
        disrupted_job_ids=[j1.id],
    )
    assert repaired.status == "error"
    assert repaired.verified_feasible is False
    assert repaired.metadata.get("error") == "problem_jobs_diverged_from_compiled_schedule"


def test_shift_calendar_and_safety_and_service_area_are_hard() -> None:
    a = _asset()
    a = a.model_copy(update={"service_area": "north"})
    c = _crew()
    c = c.model_copy(
        update={
            "service_area": "south",
            "shift_calendar": [
                {
                    "start": T0.isoformat(),
                    "end": (T0 + timedelta(hours=2)).isoformat(),
                }
            ],
        }
    )
    j = _job("J-CAT", a, safety_constraints=["hot-work"], duration_min=60)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule_problem, id_map = to_schedule_problem(p)
    result = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{j.id}"],
                    work_center_id=id_map[f"crew:{c.id}"],
                    start_time=T0 + timedelta(hours=4),
                    end_time=T0 + timedelta(hours=5),
                )
            ]
        },
    )()
    kinds = {
        v.kind
        for v in check_gridplan_constraints(
            p, schedule_problem=schedule_problem, result=result, id_map=id_map
        )
    }
    assert "SHIFT_CALENDAR_VIOLATION" in kinds
    assert "SAFETY_CONSTRAINT_MISMATCH" in kinds
    assert "SERVICE_AREA_MISMATCH" in kinds


def test_partial_travel_matrix_is_fail_closed() -> None:
    a1, a2 = _asset("A1"), _asset("A2")
    c = _crew()
    j1 = _job("J1", a1)
    j2 = _job("J2", a2)
    p = GridPlanProblem(
        assets=[a1, a2],
        crews=[c],
        jobs=[j1, j2],
        travel_minutes={"A1|A1": 0},
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    with pytest.raises(ValueError, match="travel_minutes missing"):
        to_schedule_problem(p)


def test_malformed_shift_calendar_rejected_at_ingest() -> None:
    with pytest.raises(ValueError, match="shift_calendar"):
        Crew(
            code="C-BAD",
            qualifications=["q1"],
            shift_calendar=[{"start": T0.isoformat()}],
            data_provenance="synthetic",
        )
