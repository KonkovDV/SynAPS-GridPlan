"""Search eligibility uses the checker predicate when a legal crew remains."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from synaps.model import Assignment

from synaps_gridplan.adapter import to_schedule_problem
from synaps_gridplan.baselines import plan_fifo
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.model import Asset, Crew, GridPlanProblem, JobKind, MaintenanceJob

T0 = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)
HORIZON = timedelta(days=2)


def _asset() -> Asset:
    return Asset(
        code="A1",
        name="a",
        asset_class="x",
        location_code="A1",
        service_area="north",
        data_provenance="synthetic",
    )


def _crew(
    code: str,
    *,
    area: str = "",
    quals: list[str] | None = None,
    clearances: list[object] | None = None,
) -> Crew:
    attributes: dict = {}
    if clearances is not None:
        attributes["safety_clearances"] = clearances
    return Crew(
        code=code,
        qualifications=quals if quals is not None else ["q1"],
        service_area=area,
        domain_attributes=attributes,
        data_provenance="synthetic",
    )


def _job(asset: Asset, ref: str = "J1", **kw: object) -> MaintenanceJob:
    kw.setdefault("kind", JobKind.CORRECTIVE)
    kw.setdefault("duration_min", 60)
    kw.setdefault("required_qualifications", ["q1"])
    kw.setdefault("data_provenance", "synthetic")
    return MaintenanceJob(external_ref=ref, asset_id=asset.id, **kw)  # type: ignore[arg-type]


def _problem(asset: Asset, crews: list[Crew], job: MaintenanceJob) -> GridPlanProblem:
    return GridPlanProblem(
        assets=[asset],
        crews=crews,
        jobs=[job],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )


def test_search_keeps_only_the_crew_that_matches_service_area() -> None:
    asset = _asset()
    south = _crew("south", area="south")
    north = _crew("north", area="north")
    problem = _problem(asset, [south, north], _job(asset))
    schedule, id_map = to_schedule_problem(problem)
    assert schedule.operations[0].eligible_wc_ids == [id_map[f"crew:{north.id}"]]
    outcome = plan_fifo(problem)
    assert outcome.verified_feasible
    assert outcome.hard_violation_count == 0
    assert outcome.schedule.assignments[0].work_center_id == id_map[f"crew:{north.id}"]


def test_imported_assignment_still_fails_service_area() -> None:
    asset = _asset()
    south = _crew("south", area="south")
    north = _crew("north", area="north")
    job = _job(asset)
    problem = _problem(asset, [south, north], job)
    schedule, id_map = to_schedule_problem(problem)
    result = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{job.id}"],
                    work_center_id=id_map[f"crew:{south.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=60),
                )
            ]
        },
    )()
    kinds = {
        item.kind
        for item in check_gridplan_constraints(
            problem, schedule_problem=schedule, result=result, id_map=id_map
        )
    }
    assert "SERVICE_AREA_MISMATCH" in kinds


def test_string_clearance_admits_a_crew_and_a_number_does_not() -> None:
    asset = _asset().model_copy(update={"service_area": ""})
    named = _crew("named", clearances=["hot-work"])
    numbered = _crew("numbered", clearances=[1])
    text_one = _crew("text-one", clearances=["1"])
    hot = _job(asset, safety_constraints=["hot-work"])
    schedule, id_map = to_schedule_problem(_problem(asset, [numbered, named], hot))
    assert schedule.operations[0].eligible_wc_ids == [id_map[f"crew:{named.id}"]]

    coerced = _job(asset, "J-NUM", safety_constraints=["1"])
    only_number = _problem(asset, [numbered], coerced)
    schedule, id_map = to_schedule_problem(only_number)
    assert schedule.operations[0].eligible_wc_ids == [id_map[f"crew:{numbered.id}"]]
    result = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{coerced.id}"],
                    work_center_id=id_map[f"crew:{numbered.id}"],
                    start_time=T0,
                    end_time=T0 + timedelta(minutes=60),
                )
            ]
        },
    )()
    kinds = {
        item.kind
        for item in check_gridplan_constraints(
            only_number, schedule_problem=schedule, result=result, id_map=id_map
        )
    }
    assert "SAFETY_CONSTRAINT_MISMATCH" in kinds

    both = _problem(asset, [numbered, text_one], coerced)
    schedule, id_map = to_schedule_problem(both)
    assert schedule.operations[0].eligible_wc_ids == [id_map[f"crew:{text_one.id}"]]


def test_empty_safety_and_area_do_not_drop_crews() -> None:
    asset = _asset().model_copy(update={"service_area": ""})
    first = _crew("a")
    second = _crew("b")
    problem = _problem(asset, [first, second], _job(asset))
    schedule, id_map = to_schedule_problem(problem)
    assert set(schedule.operations[0].eligible_wc_ids) == {
        id_map[f"crew:{first.id}"],
        id_map[f"crew:{second.id}"],
    }


def test_no_legal_crew_does_not_become_an_empty_eligible_list() -> None:
    asset = _asset()
    south = _crew("south", area="south")
    problem = _problem(asset, [south], _job(asset))
    schedule, id_map = to_schedule_problem(problem)
    assert schedule.operations[0].eligible_wc_ids == [id_map[f"crew:{south.id}"]]
