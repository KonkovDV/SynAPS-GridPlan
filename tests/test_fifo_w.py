"""FIFO-W places work inside shifts and after travel. Calendar FIFO does not."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from synaps_gridplan.baselines import plan_fifo, plan_fifo_w, plan_with_config
from synaps_gridplan.model import (
    Asset,
    Crew,
    CrewCalendarWindow,
    GridPlanProblem,
    MaintenanceJob,
    OutageWindow,
)

DAY = datetime(2026, 10, 5, tzinfo=UTC)


def _problem(
    *,
    shift: list[tuple[datetime, datetime]] | None = None,
    availability: list[tuple[datetime, datetime]] | None = None,
    travel: dict[str, int] | None = None,
    jobs: list[MaintenanceJob] | None = None,
    assets: list[Asset] | None = None,
) -> GridPlanProblem:
    site = Asset(code="SITE", location_code="SITE")
    crew = Crew(
        code="C",
        home_location_code="HOME",
        shift_calendar=[CrewCalendarWindow(start=a, end=b) for a, b in (shift or [])],
        availability=[CrewCalendarWindow(start=a, end=b) for a, b in (availability or [])],
    )
    built = jobs or [
        MaintenanceJob(external_ref="J", asset_id=site.id, duration_min=60),
    ]
    return GridPlanProblem(
        assets=assets or [site],
        crews=[crew],
        jobs=built,
        travel_minutes=travel or {},
        planning_horizon_start=DAY,
        planning_horizon_end=DAY + timedelta(days=1),
    )


def test_fifo_w_starts_after_travel_inside_the_shift() -> None:
    problem = _problem(
        shift=[(DAY + timedelta(hours=8), DAY + timedelta(hours=17))],
        travel={"HOME|SITE": 30, "SITE|HOME": 30},
    )
    plain = plan_fifo(problem)
    windowed = plan_fifo_w(problem)
    assert plain.schedule.assignments[0].start_time == DAY
    assert len(windowed.schedule.assignments) == 1
    placed = windowed.schedule.assignments[0]
    assert placed.start_time == DAY + timedelta(hours=8, minutes=30)
    assert placed.setup_minutes == 30
    assert windowed.solver_config == "FIFO-W"


def test_fifo_w_matches_calendar_fifo_when_the_crew_is_round_the_clock() -> None:
    problem = _problem()
    plain = plan_fifo(problem)
    windowed = plan_fifo_w(problem)
    assert [item.start_time for item in windowed.schedule.assignments] == [
        item.start_time for item in plain.schedule.assignments
    ]


def test_disjoint_shift_and_availability_leave_the_job_unscheduled() -> None:
    problem = _problem(
        shift=[(DAY + timedelta(hours=8), DAY + timedelta(hours=9))],
        availability=[(DAY + timedelta(hours=12), DAY + timedelta(hours=17))],
    )
    outcome = plan_fifo_w(problem)
    assert outcome.schedule.assignments == []
    assert outcome.verified_feasible is False


def test_second_job_waits_for_travel_between_sites() -> None:
    home = Asset(code="A", location_code="A")
    far = Asset(code="B", location_code="B")
    first = MaintenanceJob(
        external_ref="A",
        asset_id=home.id,
        duration_min=60,
        due_date=DAY + timedelta(hours=10),
    )
    second = MaintenanceJob(
        external_ref="B",
        asset_id=far.id,
        duration_min=60,
        due_date=DAY + timedelta(hours=12),
    )
    problem = _problem(
        shift=[(DAY + timedelta(hours=8), DAY + timedelta(hours=17))],
        travel={
            "HOME|A": 0,
            "A|HOME": 0,
            "HOME|B": 20,
            "B|HOME": 20,
            "A|B": 20,
            "B|A": 20,
        },
        assets=[home, far],
        jobs=[first, second],
    )
    outcome = plan_fifo_w(problem)
    starts = {
        assignment.operation_id: assignment.start_time
        for assignment in outcome.schedule.assignments
    }
    start_of = {job.external_ref: starts[outcome.id_map[f"job:{job.id}"]] for job in problem.jobs}
    assert start_of["A"] == DAY + timedelta(hours=8)
    assert start_of["B"] == DAY + timedelta(hours=9, minutes=20)


def test_ready_predecessor_is_placed_before_an_earlier_due_successor() -> None:
    site = Asset(code="SITE", location_code="SITE")
    later = MaintenanceJob(
        external_ref="A",
        asset_id=site.id,
        duration_min=60,
        due_date=DAY + timedelta(hours=16),
    )
    sooner = MaintenanceJob(
        external_ref="B",
        asset_id=site.id,
        duration_min=60,
        due_date=DAY + timedelta(hours=12),
        predecessor_job_ids=[later.id],
    )
    problem = _problem(
        shift=[(DAY + timedelta(hours=8), DAY + timedelta(hours=17))],
        assets=[site],
        jobs=[sooner, later],
    )
    outcome = plan_with_config(problem, solver_config="FIFO-W", apply_frozen=False)
    order = [
        assignment.start_time
        for assignment in sorted(outcome.schedule.assignments, key=lambda item: item.start_time)
    ]
    assert order == [
        DAY + timedelta(hours=8),
        DAY + timedelta(hours=9),
    ]
    assert outcome.metadata.get("baseline") == "fifo_w_windows_travel_shifts"


def test_interruption_starts_inside_the_approved_window() -> None:
    site = Asset(code="SITE", location_code="SITE")
    job = MaintenanceJob(
        external_ref="J",
        asset_id=site.id,
        duration_min=60,
        interruption_required=True,
    )
    problem = GridPlanProblem(
        assets=[site],
        crews=[Crew(code="C", home_location_code="SITE")],
        jobs=[job],
        outage_windows=[
            OutageWindow(
                asset_id=site.id,
                start=DAY + timedelta(hours=10),
                end=DAY + timedelta(hours=12),
            )
        ],
        planning_horizon_start=DAY,
        planning_horizon_end=DAY + timedelta(days=1),
    )
    outcome = plan_fifo_w(problem)
    assert len(outcome.schedule.assignments) == 1
    assert outcome.schedule.assignments[0].start_time == DAY + timedelta(hours=10)
