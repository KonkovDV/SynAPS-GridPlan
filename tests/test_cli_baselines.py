"""CLI, baseline, and infeasible-mode tests."""

from __future__ import annotations

import json
from pathlib import Path

from synaps_gridplan.baselines import plan_fifo, plan_with_config
from synaps_gridplan.cli import main
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.planner import plan_maintenance, replan_after_disruption
from synaps_gridplan.report import render_report
from synaps_gridplan.synthetic import synthesize_feeder


def test_fifo_baseline_deterministic() -> None:
    problem = synthesize_feeder(mode="small", seed=21)
    # plan_with_config(FIFO) defaults apply_frozen=True; plan_fifo defaults False.
    # Small feeders plant frozen outage windows, so the flag must match.
    a = plan_fifo(problem, apply_frozen=True)
    b = plan_with_config(problem, solver_config="FIFO", apply_frozen=True)
    assert a.solver_config == "FIFO"
    assert a.status == b.status
    assert [x.model_dump(mode="json") for x in a.schedule.assignments] == [
        x.model_dump(mode="json") for x in b.schedule.assignments
    ]
    off_a = plan_fifo(problem, apply_frozen=False)
    off_b = plan_fifo(problem, apply_frozen=False)
    assert [x.model_dump(mode="json") for x in off_a.schedule.assignments] == [
        x.model_dump(mode="json") for x in off_b.schedule.assignments
    ]
    assert a.metadata.get("claim_status") in {
        "heuristic_feasible",
        "feasible",
        "infeasible",
        "error",
    }


def test_diff_auto_metrics_on_disruption() -> None:
    problem = synthesize_feeder(mode="small", seed=22)
    base = plan_maintenance(problem, solver_config="GREED", apply_frozen=False)
    repaired = replan_after_disruption(
        problem,
        base_outcome=base,
        disrupted_job_ids=[problem.jobs[0].id],
    )
    d = diff_plans(
        base=base.schedule,
        repaired=repaired.schedule,
        id_map=base.id_map,
        frozen=list(base.frozen_assignments),
        problem=problem,
        violations=repaired.metadata.get("gridplan_violations", []),
    )
    assert d["schema_version"] == "gridplan.diff.v1"
    assert "churn" in d
    assert "changed_metrics" in d
    assert "base_coverage" in d["changed_metrics"]


def test_csv_report_includes_provenance() -> None:
    problem = synthesize_feeder(mode="small", seed=23)
    outcome = plan_with_config(problem, solver_config="FIFO")
    csv_text = render_report(outcome, fmt="csv")
    assert "# claim_level,experiment" in csv_text
    assert "# iso16290_trl," in csv_text
    assert "# input_hash," in csv_text
    assert "operation_id," in csv_text


def test_infeasible_mode_does_not_claim_verified() -> None:
    problem = synthesize_feeder(mode="infeasible", seed=24)
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=False)
    assert outcome.verified_feasible is False
    assert outcome.status in {"error", "infeasible", "timeout"}


def test_frozen_conflict_mode_surfaces_conflict() -> None:
    problem = synthesize_feeder(mode="frozen-conflict", seed=25)
    assert problem.frozen_assignments
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    kinds = outcome.metadata.get("gridplan_violation_kinds", [])
    # Either conflict detected, or fail-closed error / infeasible — never verified.
    assert outcome.verified_feasible is False
    assert "FROZEN_ASSIGNMENT_CONFLICT" in kinds or outcome.status in {
        "error",
        "infeasible",
        "timeout",
    }


def test_cli_synthesize_solve_report_disrupt(tmp_path: Path) -> None:
    feeder = tmp_path / "feeder.json"
    result = tmp_path / "result.json"
    repaired = tmp_path / "repaired.json"

    assert main(["synthesize", "--mode", "small", "--seed", "26", "-o", str(feeder)]) == 0
    code = main(["solve", str(feeder), "--solver", "FIFO", "-o", str(result)])
    assert code in {0, 2}
    raw = json.loads(result.read_text(encoding="utf-8"))
    assert "schedule_problem" in raw
    assert "outcome" in raw

    assert main(["report", str(result), "--format", "json"]) == 0

    job_id = json.loads(feeder.read_text(encoding="utf-8"))["jobs"][0]["id"]
    code2 = main(
        [
            "disrupt",
            str(feeder),
            str(result),
            "--job-id",
            job_id,
            "-o",
            str(repaired),
        ]
    )
    assert code2 in {0, 2}
    repaired_raw = json.loads(repaired.read_text(encoding="utf-8"))
    assert "diff" in repaired_raw
    assert repaired_raw["diff"]["schema_version"] == "gridplan.diff.v1"
