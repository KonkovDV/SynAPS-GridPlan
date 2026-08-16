"""Fail-closed overlap, freeze-rest, latest-finish, and simultaneous-outage bans."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from synaps.model import Assignment

from synaps_gridplan.adapter import to_schedule_problem
from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.diff import diff_plans
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
HORIZON = timedelta(days=5)


def _asset(code: str = "A1") -> Asset:
    return Asset(
        code=code,
        name="a",
        asset_class="x",
        location_code="L1",
        data_provenance="synthetic",
    )


def _crew(code: str = "C1", quals: list[str] | None = None) -> Crew:
    return Crew(code=code, qualifications=quals or ["q1"], data_provenance="synthetic")


def _job(ref: str, asset: Asset, **kw) -> MaintenanceJob:
    kw.setdefault("kind", JobKind.CORRECTIVE)
    kw.setdefault("duration_min", 60)
    kw.setdefault("required_qualifications", ["q1"])
    kw.setdefault("data_provenance", "synthetic")
    return MaintenanceJob(external_ref=ref, asset_id=asset.id, **kw)


def _window(asset: Asset, **kw) -> OutageWindow:
    kw.setdefault("start", T0)
    kw.setdefault("end", T0 + HORIZON)
    kw.setdefault("approved", True)
    kw.setdefault("data_provenance", "synthetic")
    return OutageWindow(asset_id=asset.id, **kw)


def test_same_asset_simultaneous_outage_is_fail_closed() -> None:
    """Two interruption jobs on one asset must not overlap."""
    a = _asset()
    c1, c2 = _crew("C1"), _crew("C2")
    j1 = _job("J1", a, interruption_required=True, duration_min=600)
    j2 = _job("J2", a, interruption_required=True, duration_min=600)
    p = GridPlanProblem(
        assets=[a],
        crews=[c1, c2],
        jobs=[j1, j2],
        outage_windows=[_window(a)],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    # Any plan placing them in parallel must be caught; a serial plan is legal.
    if not o.verified_feasible:
        assert "ASSET_OVERLAP" in o.metadata["gridplan_violation_kinds"]
    else:
        ends = sorted((asn.start_time, asn.end_time) for asn in o.schedule.assignments)
        assert ends[0][1] <= ends[1][0], "verified plan must serialize the asset"


def test_crew_double_booking_flagged_at_gridplan_layer() -> None:
    """Standalone check_gridplan_constraints with an overlapping pair."""
    from synaps_gridplan.adapter import to_schedule_problem
    from synaps_gridplan.constraints import check_gridplan_constraints

    a, c = _asset(), _crew()
    j1, j2 = _job("J1", a), _job("J2", a)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j1, j2],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    schedule_problem, id_map = to_schedule_problem(p)
    from synaps.model import Assignment

    def _asn(job: MaintenanceJob, start: datetime) -> Assignment:
        return Assignment(
            operation_id=id_map[f"job:{job.id}"],
            work_center_id=id_map[f"crew:{c.id}"],
            start_time=start,
            end_time=start + timedelta(minutes=job.duration_min),
        )

    result = type("R", (), {"assignments": [_asn(j1, T0), _asn(j2, T0 + timedelta(minutes=30))]})()
    violations = check_gridplan_constraints(
        p, schedule_problem=schedule_problem, result=result, id_map=id_map
    )
    kinds = {v.kind for v in violations}
    assert "CREW_OVERLAP" in kinds


def test_replan_freezes_rest_even_with_pl_frozen_rows() -> None:
    """Explicit ПЛ freeze present: non-disrupted jobs must still be frozen."""
    a = _asset()
    c = _crew()
    frozen_job = _job("ПЛ-1", a, duration_min=120)
    keep_job = _job("KEEP", a, duration_min=60)
    gone_job = _job("GONE", a, duration_min=60)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[frozen_job, keep_job, gone_job],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    base = plan_maintenance(p, solver_config="GREED")
    assert base.verified_feasible
    frozen_row = FrozenAssignment(
        job_id=frozen_job.id,
        crew_id=c.id,
        start=base.schedule.assignments[0].start_time,
        end=base.schedule.assignments[0].end_time,
        reason="ПЛ",
    )
    # repair with explicit ПЛ row present — the old code skipped freeze-rest
    p_frozen = p.model_copy(update={"frozen_assignments": [frozen_row]})
    repaired = replan_after_disruption(p_frozen, base_outcome=base, disrupted_job_ids=[gone_job.id])
    assert repaired.verified_feasible, repaired.metadata
    keep_op = base.id_map[f"job:{keep_job.id}"]
    base_keep = next(a for a in base.schedule.assignments if a.operation_id == keep_op)
    new_keep = next(a for a in repaired.schedule.assignments if a.operation_id == keep_op)
    assert (new_keep.start_time, new_keep.end_time, new_keep.work_center_id) == (
        base_keep.start_time,
        base_keep.end_time,
        base_keep.work_center_id,
    ), "non-disrupted job must not move when freeze-rest is active"


def test_diff_does_not_call_crew_swapped_frozen_unchanged() -> None:
    """Frozen row with same times but a different crew is not unchanged."""
    a = _asset()
    c1, c2 = _crew("C1"), _crew("C2")
    j = _job("J1", a)
    p = GridPlanProblem(
        assets=[a],
        crews=[c1, c2],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    base = plan_maintenance(p, solver_config="GREED")
    assert base.verified_feasible
    asn = base.schedule.assignments[0]
    used_c1 = asn.work_center_id == base.id_map[f"crew:{c1.id}"]
    other = c2 if used_c1 else c1
    frozen = [
        FrozenAssignment(
            job_id=j.id,
            crew_id=other.id,  # same slot, wrong crew
            start=asn.start_time,
            end=asn.end_time,
            frozen_reason="ПЛ",
        )
    ]
    diff = diff_plans(
        base=base.schedule,
        repaired=base.schedule,
        id_map=base.id_map,
        frozen=frozen,
    )
    assert diff["churn"]["unchanged_frozen"] == 0


def test_latest_finish_is_hard() -> None:
    """Job ending past latest_finish must not verify."""
    a, c = _asset(), _crew()
    j = _job("J1", a, duration_min=600, latest_finish=T0 + timedelta(minutes=30))
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    assert not o.verified_feasible
    kinds = o.metadata["gridplan_violation_kinds"]
    # Solver may refuse the slot (UNSCHEDULED_JOB) or emit a late assignment;
    # both are fail-closed. The kind is proven by the forged-row check below.
    assert "LATEST_FINISH_VIOLATION" in kinds or "UNSCHEDULED_JOB" in kinds

    schedule_problem, id_map = to_schedule_problem(p)
    forged = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{j.id}"],
                    work_center_id=id_map[f"crew:{c.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=600),
                )
            ]
        },
    )()
    kinds_forged = {
        v.kind
        for v in check_gridplan_constraints(
            p, schedule_problem=schedule_problem, result=forged, id_map=id_map
        )
    }
    assert "LATEST_FINISH_VIOLATION" in kinds_forged


def test_simultaneous_outage_ban_is_fail_closed() -> None:
    """network_constraints: overlapping interruption on banned asset pair fails."""
    from synaps.model import Assignment

    from synaps_gridplan.adapter import to_schedule_problem
    from synaps_gridplan.constraints import check_gridplan_constraints
    from synaps_gridplan.model import SimultaneousOutageBan

    a1, a2 = _asset("A1"), _asset("A2")
    c1, c2 = _crew("C1"), _crew("C2")
    j1 = _job("J1", a1, interruption_required=True, duration_min=120)
    j2 = _job("J2", a2, interruption_required=True, duration_min=120)
    ban = SimultaneousOutageBan(
        asset_id_a=a1.id, asset_id_b=a2.id, reason="corridor", data_provenance="synthetic"
    )
    p = GridPlanProblem(
        assets=[a1, a2],
        crews=[c1, c2],
        jobs=[j1, j2],
        outage_windows=[_window(a1), _window(a2)],
        simultaneous_outage_bans=[ban],
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
                    operation_id=id_map[f"job:{j1.id}"],
                    work_center_id=id_map[f"crew:{c1.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=120),
                ),
                Assignment(
                    operation_id=id_map[f"job:{j2.id}"],
                    work_center_id=id_map[f"crew:{c2.id}"],
                    start_time=T0 + timedelta(minutes=30),
                    end_time=T0 + timedelta(minutes=150),
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
    assert "SIMULTANEOUS_OUTAGE_BAN" in kinds


def test_independent_interruptions_do_not_hull_across_a_gap() -> None:
    """No predecessor edge ⇒ occupancy is pairwise intervals, not the calendar hull."""

    from synaps.model import Assignment

    from synaps_gridplan.adapter import to_schedule_problem
    from synaps_gridplan.constraints import check_gridplan_constraints
    from synaps_gridplan.model import SimultaneousOutageBan

    a1, a2 = _asset("A1"), _asset("A2")
    c1, c2 = _crew("C1"), _crew("C2")
    j1 = _job("J1", a1, interruption_required=True, duration_min=60)
    j2 = _job("J2", a1, interruption_required=True, duration_min=60)
    j3 = _job("J3", a2, interruption_required=True, duration_min=60)
    ban = SimultaneousOutageBan(
        asset_id_a=a1.id, asset_id_b=a2.id, reason="corridor", data_provenance="synthetic"
    )
    p = GridPlanProblem(
        assets=[a1, a2],
        crews=[c1, c2],
        jobs=[j1, j2, j3],
        outage_windows=[_window(a1), _window(a2)],
        simultaneous_outage_bans=[ban],
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
                    operation_id=id_map[f"job:{j1.id}"],
                    work_center_id=id_map[f"crew:{c1.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=60),
                ),
                Assignment(
                    operation_id=id_map[f"job:{j2.id}"],
                    work_center_id=id_map[f"crew:{c1.id}"],
                    start_time=T0 + timedelta(hours=8),
                    end_time=T0 + timedelta(hours=9),
                ),
                Assignment(
                    operation_id=id_map[f"job:{j3.id}"],
                    work_center_id=id_map[f"crew:{c2.id}"],
                    start_time=T0 + timedelta(hours=3),
                    end_time=T0 + timedelta(hours=4),
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
    assert "SIMULTANEOUS_OUTAGE_BAN" not in kinds


def test_interruption_job_without_any_window_is_not_verified() -> None:
    a = _asset()
    c = _crew()
    j = _job("J1", a, interruption_required=True, duration_min=60)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        outage_windows=[],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    assert o.verified_feasible is False
    kinds = o.metadata.get("gridplan_violation_kinds", [])
    assert "OUTAGE_WINDOW_MISSING" in kinds or "OUTAGE_WINDOW_VIOLATION" in kinds
