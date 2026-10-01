"""Solver-visible crew shifts: WorkCenter.calendar is the compiled intersection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from synaps_gridplan.adapter import to_schedule_problem
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.model import (
    Asset,
    Crew,
    CrewCalendarWindow,
    GridPlanProblem,
    MaintenanceJob,
)
from synaps_gridplan.planner import plan_maintenance

MSK = timezone(timedelta(hours=3))
DAY = datetime(2026, 10, 5, tzinfo=MSK)


def _shifts() -> list[CrewCalendarWindow]:
    rows = []
    for offset in range(2):
        start = DAY + timedelta(days=offset, hours=8)
        rows.append(CrewCalendarWindow(start=start, end=start + timedelta(hours=9)))
    return rows


def _problem(
    *,
    shifts: list[CrewCalendarWindow] | None = None,
    availability: list[CrewCalendarWindow] | None = None,
    duration_min: int = 90,
) -> tuple[GridPlanProblem, Asset, Crew, MaintenanceJob]:
    asset = Asset(code="A", location_code="L")
    crew = Crew(
        code="C",
        home_location_code="L",
        shift_calendar=shifts if shifts is not None else _shifts(),
        availability=availability or [],
    )
    job = MaintenanceJob(
        external_ref="J",
        asset_id=asset.id,
        duration_min=duration_min,
        eligible_crew_ids=[crew.id],
    )
    problem = GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[job],
        planning_horizon_start=DAY,
        planning_horizon_end=DAY + timedelta(days=2),
    )
    return problem, asset, crew, job


def test_empty_calendars_compile_as_round_the_clock() -> None:
    problem, _, _, _ = _problem(shifts=[])
    schedule, _ = to_schedule_problem(problem)
    assert schedule.work_centers[0].calendar == []


def test_solver_calendar_is_the_intersection() -> None:
    day = DAY
    shifts = [CrewCalendarWindow(start=day + timedelta(hours=8), end=day + timedelta(hours=17))]
    availability = [
        CrewCalendarWindow(start=day + timedelta(hours=10), end=day + timedelta(hours=12))
    ]
    problem, _, _, _ = _problem(shifts=shifts, availability=availability)
    schedule, _ = to_schedule_problem(problem)
    calendar = schedule.work_centers[0].calendar
    assert [(row.start, row.end) for row in calendar] == [
        (day + timedelta(hours=10), day + timedelta(hours=12))
    ]


def test_disjoint_calendars_are_not_compiled_as_round_the_clock() -> None:
    shifts = [CrewCalendarWindow(start=DAY + timedelta(hours=8), end=DAY + timedelta(hours=12))]
    availability = [
        CrewCalendarWindow(start=DAY + timedelta(hours=13), end=DAY + timedelta(hours=17))
    ]
    problem, _, _, _ = _problem(shifts=shifts, availability=availability)
    schedule, _ = to_schedule_problem(problem)
    calendar = schedule.work_centers[0].calendar
    assert [(row.start, row.end) for row in calendar] == [
        (problem.planning_horizon_start - timedelta(minutes=1), problem.planning_horizon_start)
    ]


def test_setup_before_the_shift_is_a_violation() -> None:
    problem, _, crew, job = _problem()
    schedule, id_map = to_schedule_problem(problem)
    start = DAY + timedelta(hours=8)
    from synaps.model import Assignment, ObjectiveValues, ScheduleResult, SolverStatus

    result = ScheduleResult(
        status=SolverStatus.FEASIBLE,
        solver_name="forged",
        assignments=[
            Assignment(
                operation_id=id_map[f"job:{job.id}"],
                work_center_id=id_map[f"crew:{crew.id}"],
                start_time=start,
                end_time=start + timedelta(minutes=90),
                setup_minutes=30,
            )
        ],
        objective=ObjectiveValues(coverage=1.0, unscheduled_operations=0),
        metadata={},
    )
    kinds = {
        item.kind
        for item in check_gridplan_constraints(
            problem, schedule_problem=schedule, result=result, id_map=id_map
        )
    }
    assert "SHIFT_CALENDAR_VIOLATION" in kinds


def test_greed_and_cpsat_place_a_short_job_inside_the_moscow_shift() -> None:
    problem, _, _, _ = _problem()
    for config in ("GREED", "CPSAT-10"):
        outcome = plan_maintenance(problem, solver_config=config)
        assert outcome.verified_feasible, config
        assert outcome.schedule.assignments, config
        for assignment in outcome.schedule.assignments:
            occupancy = assignment.start_time - timedelta(minutes=assignment.setup_minutes)
            assert any(
                occupancy >= row.start and assignment.end_time <= row.end
                for row in outcome.schedule_problem.work_centers[0].calendar
            ), config


def test_utc_instants_compare_with_moscow_shifts() -> None:
    """The same civil shift expressed in UTC still compiles to one window."""

    start = datetime(2026, 10, 5, 5, tzinfo=UTC)  # 08:00 MSK
    problem, _, _, _ = _problem(
        shifts=[CrewCalendarWindow(start=start, end=start + timedelta(hours=9))]
    )
    schedule, _ = to_schedule_problem(problem)
    row = schedule.work_centers[0].calendar[0]
    assert row.start == start
    assert row.end == start + timedelta(hours=9)


def test_job_longer_than_a_shift_compiles_to_day_parts() -> None:
    problem, _, _, job = _problem(duration_min=600)
    schedule, id_map = to_schedule_problem(problem)
    durations = [op.base_duration_min for op in schedule.operations]
    assert durations == [540, 60]
    assert sum(durations) == 600
    assert id_map[f"job:{job.id}:part:0"] == id_map[f"job:{job.id}"]
    assert f"job:{job.id}:part:1" in id_map
    assert schedule.operations[1].predecessor_op_id == schedule.operations[0].id


def test_day_parts_of_a_long_job_fit_moscow_shifts() -> None:
    problem, _, _, _ = _problem(duration_min=600)
    for config in ("GREED", "CPSAT-10"):
        outcome = plan_maintenance(problem, solver_config=config)
        assert outcome.verified_feasible, config
        assert len(outcome.schedule.assignments) == 2, config
        for assignment in outcome.schedule.assignments:
            occupancy = assignment.start_time - timedelta(minutes=assignment.setup_minutes)
            assert any(
                occupancy >= row.start and assignment.end_time <= row.end
                for row in outcome.schedule_problem.work_centers[0].calendar
            ), config

