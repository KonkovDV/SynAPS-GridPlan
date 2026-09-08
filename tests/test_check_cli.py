"""Independent re-check CLI: saved flags are claims, not certificates."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from synaps_gridplan.baselines import plan_fifo
from synaps_gridplan.cli import main
from synaps_gridplan.io import read_text_limited
from synaps_gridplan.model import SCHEMA_VERSION_V2, Asset, Crew, GridPlanProblem, MaintenanceJob


def _tiny_problem() -> GridPlanProblem:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    return GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[MaintenanceJob(external_ref="J", asset_id=asset.id, duration_min=60)],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=1),
    )


def _result_payload(outcome) -> dict:
    return {
        "outcome": {
            "schema_version": outcome.schema_version,
            "solver_config": outcome.solver_config,
            "status": "feasible",
            "verified_feasible": True,
            "hard_violation_count": 0,
            "metadata": {},
            "id_map": {k: str(v) for k, v in outcome.id_map.items()},
            "frozen_assignments": [],
        },
        "schedule": json.loads(outcome.schedule.model_dump_json()),
        "schedule_problem": json.loads(outcome.schedule_problem.model_dump_json()),
    }


def test_check_recomputes_verification_and_ignores_saved_success(tmp_path: Path) -> None:
    problem = _tiny_problem()
    outcome = plan_fifo(problem)
    assert outcome.ok
    problem_path = tmp_path / "problem.json"
    result_path = tmp_path / "result.json"
    checked_path = tmp_path / "checked.json"
    problem_path.write_text(problem.model_dump_json(indent=2), encoding="utf-8")
    result_path.write_text(json.dumps(_result_payload(outcome)), encoding="utf-8")
    assert main(["check", str(problem_path), str(result_path), "-o", str(checked_path)]) == 0
    checked = json.loads(checked_path.read_text(encoding="utf-8"))
    assert checked["outcome"]["verified_feasible"] is True
    assert checked["outcome"]["metadata"]["verification_origin"] == "independent_recheck"
    assert "problem" in checked


def test_check_does_not_trust_a_false_verified_flag(tmp_path: Path) -> None:
    problem = _tiny_problem()
    outcome = plan_fifo(problem)
    problem_path = tmp_path / "problem.json"
    result_path = tmp_path / "result.json"
    problem_path.write_text(problem.model_dump_json(), encoding="utf-8")
    payload = _result_payload(outcome)
    payload["schedule"]["assignments"] = []
    result_path.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["check", str(problem_path), str(result_path)]) == 2


def test_check_rejects_embedded_problem_mismatch(tmp_path: Path) -> None:
    problem = _tiny_problem()
    other = problem.model_copy(update={"schema_version": SCHEMA_VERSION_V2})
    outcome = plan_fifo(problem)
    problem_path = tmp_path / "problem.json"
    result_path = tmp_path / "result.json"
    problem_path.write_text(other.model_dump_json(), encoding="utf-8")
    payload = _result_payload(outcome)
    payload["problem"] = json.loads(problem.model_dump_json())
    result_path.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["check", str(problem_path), str(result_path)]) == 2


def test_v2_input_is_not_relabelled_v1() -> None:
    problem = _tiny_problem().model_copy(update={"schema_version": SCHEMA_VERSION_V2})
    outcome = plan_fifo(problem)
    assert outcome.schema_version == SCHEMA_VERSION_V2
    assert outcome.metadata["gridplan_schema_version"] == SCHEMA_VERSION_V2


def test_read_text_limited_rejects_oversize(tmp_path: Path) -> None:
    path = tmp_path / "tiny.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="limit is"):
        read_text_limited(path, max_bytes=1)


def test_lab_catalog_quota_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("synaps_gridplan.model.MAX_JOBS", 1)
    start = datetime(2026, 9, 1, tzinfo=UTC)
    asset = Asset(code="A")
    crew = Crew(code="C")
    with pytest.raises(ValueError, match="lab limit"):
        GridPlanProblem(
            assets=[asset],
            crews=[crew],
            jobs=[
                MaintenanceJob(external_ref="J1", asset_id=asset.id, duration_min=60),
                MaintenanceJob(external_ref="J2", asset_id=asset.id, duration_min=60),
            ],
            planning_horizon_start=start,
            planning_horizon_end=start + timedelta(days=1),
        )
