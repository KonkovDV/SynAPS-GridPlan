"""Input/output trust-boundary tests, independent of solver performance claims."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from synaps_gridplan.adapter import _lookup_travel_minutes, to_schedule_problem
from synaps_gridplan.baselines import plan_fifo
from synaps_gridplan.cli import _outcome_from_payload, _payload, main
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.model import Asset, Crew, FrozenAssignment, GridPlanProblem, MaintenanceJob
from synaps_gridplan.planner import PlanOutcome, replan_after_disruption
from synaps_gridplan.report import render_report


@pytest.fixture
def instance() -> tuple[GridPlanProblem, PlanOutcome]:
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


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None, [], {}])
def test_import_requires_real_boolean(instance, value) -> None:
    _, outcome = instance
    raw = _payload(outcome)
    raw["outcome"]["verified_feasible"] = value
    with pytest.raises(ValueError, match="JSON boolean"):
        _outcome_from_payload(raw)


@pytest.mark.parametrize("value", [True, -1, 0.5, "0", None])
def test_import_requires_nonnegative_integer_count(instance, value) -> None:
    _, outcome = instance
    raw = _payload(outcome)
    raw["outcome"]["hard_violation_count"] = value
    with pytest.raises(ValueError, match="JSON integer"):
        _outcome_from_payload(raw)


def test_import_rejects_contradictory_verified_flag(instance) -> None:
    _, outcome = instance
    raw = _payload(outcome)
    raw["outcome"]["hard_violation_count"] = 1
    with pytest.raises(ValueError, match="contradicts"):
        _outcome_from_payload(raw)
    assert not replace(outcome, hard_violation_count=1).ok


def test_import_is_explicitly_not_reverification(instance) -> None:
    _, outcome = instance
    loaded = _outcome_from_payload(_payload(outcome))
    assert loaded.metadata["verification_origin"] == "imported_snapshot_not_rechecked"
    assert "Saved snapshot" in render_report(loaded, fmt="markdown")
    assert "verification_origin" not in outcome.metadata


def test_cli_bad_json_returns_non_success(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text("{broken", encoding="utf-8")
    assert main(["report", str(source)]) == 2


@pytest.mark.parametrize("value", ["=1+1", "+SUM(1,2)", "-1+2", "@SUM(1,2)", "\t=1", " =1"])
def test_csv_formula_like_text_is_inert(instance, value: str) -> None:
    _, outcome = instance
    changed = replace(
        outcome,
        solver_config=value,
        metadata={**outcome.metadata, "claim_level": value},
    )
    rows = list(csv.reader(io.StringIO(render_report(changed, fmt="csv"))))
    assert rows[0] == ["# claim_level", "'" + value]
    assert rows[-1][-1] == "'" + value
    assert json.loads(render_report(changed, fmt="json"))["solver_config"] == value


def test_csv_multiline_metadata_stays_one_cell(instance) -> None:
    _, outcome = instance
    value = "first,second\n# verified_feasible,True"
    changed = replace(outcome, metadata={**outcome.metadata, "claim_level": value})
    rows = list(csv.reader(io.StringIO(render_report(changed, fmt="csv"))))
    assert rows[0] == ["# claim_level", value]
    assert sum(row[0] == "# verified_feasible" for row in rows) == 1


def test_missing_crew_map_cannot_prove_frozen_unchanged(instance) -> None:
    problem, outcome = instance
    assignment = outcome.schedule.assignments[0]
    frozen = FrozenAssignment(
        job_id=problem.jobs[0].id,
        crew_id=problem.crews[0].id,
        start=assignment.start_time,
        end=assignment.end_time,
    )
    mapping = {key: value for key, value in outcome.id_map.items() if not key.startswith("crew:")}
    diff = diff_plans(
        base=outcome.schedule,
        repaired=outcome.schedule,
        id_map=mapping,
        frozen=[frozen],
    )
    assert diff["churn"]["unchanged_frozen"] == 0


def test_unknown_asset_in_model_copy_fails_closed(instance) -> None:
    problem, outcome = instance
    invalid = problem.model_copy(
        update={"jobs": [problem.jobs[0].model_copy(update={"asset_id": UUID(int=0)})]}
    )
    with pytest.raises(ValueError):
        to_schedule_problem(invalid)
    violations = check_gridplan_constraints(
        invalid,
        schedule_problem=outcome.schedule_problem,
        result=outcome.schedule,
        id_map=outcome.id_map,
    )
    assert any(v.kind == "INVALID_PROBLEM" for v in violations)


def test_missing_site_leg_is_not_replaced_by_home_leg(instance) -> None:
    problem, _ = instance
    partial = problem.model_copy(update={"travel_minutes": {"HOME|B": 5}})
    assert _lookup_travel_minutes(partial, from_loc="idle", to_loc="B", home="HOME") == 5
    with pytest.raises(ValueError, match="travel_minutes missing"):
        _lookup_travel_minutes(partial, from_loc="A", to_loc="B", home="HOME")
    assert _lookup_travel_minutes(problem, from_loc="A", to_loc="B", home="HOME") == 0


def test_repair_rejects_solver_name_that_would_only_relabel_result(instance) -> None:
    problem, outcome = instance
    with pytest.raises(ValueError, match="INCREMENTAL_REPAIR"):
        replan_after_disruption(
            problem,
            base_outcome=outcome,
            disrupted_job_ids=[problem.jobs[0].id],
            solver_config="CPSAT-10",
        )
