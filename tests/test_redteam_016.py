"""Red Team 0.1.6: window freeze on check, naive assignment times, TRL stamp."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from synaps.model import Assignment, ObjectiveValues, ScheduleProblem, ScheduleResult, SolverStatus

from synaps_gridplan.adapter import to_schedule_problem
from synaps_gridplan.baselines import plan_fifo
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.io import read_text_limited
from synaps_gridplan.model import Asset, Crew, GridPlanProblem, MaintenanceJob, OutageWindow
from synaps_gridplan.planner import recheck_plan
from synaps_gridplan.report import render_report
from synaps_gridplan.versions import ISO16290_TRL


def _moved_assignment(
    problem: GridPlanProblem, hours: int = 2
) -> tuple[ScheduleProblem, dict[str, UUID], ScheduleResult]:
    compiled, id_map = to_schedule_problem(problem)
    job = problem.jobs[0]
    crew = problem.crews[0]
    start = problem.planning_horizon_start + timedelta(hours=hours)
    assignment = Assignment(
        operation_id=id_map[f"job:{job.id}"],
        work_center_id=id_map[f"crew:{crew.id}"],
        start_time=start,
        end_time=start + timedelta(minutes=job.duration_min),
        setup_minutes=0,
    )
    result = ScheduleResult(
        status=SolverStatus.FEASIBLE,
        solver_name="forged",
        assignments=[assignment],
        objective=ObjectiveValues(coverage=1.0, unscheduled_operations=0),
        metadata={},
    )
    return compiled, id_map, result


def test_frozen_outage_window_is_an_obligation_on_independent_check() -> None:
    start = datetime(2026, 9, 1, 6, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    job = MaintenanceJob(
        external_ref="J",
        asset_id=asset.id,
        duration_min=60,
        interruption_required=True,
    )
    window = OutageWindow(
        asset_id=asset.id,
        start=start,
        end=start + timedelta(hours=8),
        frozen=True,
        approved=True,
    )
    problem = GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[job],
        outage_windows=[window],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=1),
    )
    compiled, id_map, moved = _moved_assignment(problem)
    kinds = {
        item.kind
        for item in check_gridplan_constraints(
            problem,
            schedule_problem=compiled,
            result=moved,
            id_map=id_map,
            expected_frozen=[],
        )
    }
    assert "FROZEN_ASSIGNMENT_CONFLICT" in kinds
    outcome = recheck_plan(problem, moved, id_map=id_map)
    assert not outcome.verified_feasible
    assert "FROZEN_ASSIGNMENT_CONFLICT" in outcome.metadata["gridplan_violation_kinds"]


def test_naive_assignment_times_are_violations_not_crashes() -> None:
    start = datetime(2026, 9, 1, 6, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    job = MaintenanceJob(external_ref="J", asset_id=asset.id, duration_min=60)
    problem = GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[job],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=1),
    )
    compiled, id_map = to_schedule_problem(problem)
    naive = Assignment(
        operation_id=id_map[f"job:{job.id}"],
        work_center_id=id_map[f"crew:{crew.id}"],
        start_time=datetime(2026, 9, 1, 6),
        end_time=datetime(2026, 9, 1, 7),
        setup_minutes=0,
    )
    result = ScheduleResult(
        status=SolverStatus.FEASIBLE,
        solver_name="forged",
        assignments=[naive],
        objective=ObjectiveValues(coverage=1.0, unscheduled_operations=0),
        metadata={},
    )
    kinds = {
        item.kind
        for item in check_gridplan_constraints(
            problem, schedule_problem=compiled, result=result, id_map=id_map
        )
    }
    assert "INVALID_ASSIGNMENT_TIME" in kinds


def test_outcome_trl_is_package_self_assessment_not_input_claim() -> None:
    start = datetime(2026, 9, 1, 6, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    job = MaintenanceJob(external_ref="J", asset_id=asset.id, duration_min=60)
    problem = GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[job],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=1),
        domain_attributes={"iso16290_trl": 9, "claim_level": "experiment"},
    )
    outcome = plan_fifo(problem)
    assert outcome.metadata["iso16290_trl"] == ISO16290_TRL
    assert outcome.metadata["iso16290_trl"] != 9
    assert outcome.metadata.get("claimed_iso16290_trl") == 9


def test_markdown_flattens_control_characters_in_messages() -> None:
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
    meta = dict(outcome.metadata)
    meta["gridplan_violations"] = [{"kind": "PROBE", "message": "line1\nline2"}]
    text = render_report(replace(outcome, metadata=meta), fmt="markdown")
    assert "line1\nline2" not in text
    assert "line1 line2" in text


def test_read_text_limited_caps_the_bytes_actually_read(tmp_path: Path) -> None:
    path = tmp_path / "exact.json"
    path.write_bytes(b"ab")
    assert read_text_limited(path, max_bytes=2) == "ab"
    path.write_bytes(b"abc")
    with pytest.raises(ValueError, match="limit is 2"):
        read_text_limited(path, max_bytes=2)
