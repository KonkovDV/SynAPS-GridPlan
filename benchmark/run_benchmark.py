"""Minimal reproducible benchmark runner (synthetic fixtures only).

Compares calendar FIFO vs GREED. Metrics tagged ``synthetic_experiment``.
Not industrial proof and not a Россети deployment claim.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.fingerprint import fingerprint_payload
from synaps_gridplan.model import GridPlanProblem
from synaps_gridplan.planner import replan_after_disruption
from synaps_gridplan.synthetic import synthesize_feeder
from synaps_gridplan.versions import GRIDPLAN_VERSION, SYNAPS_COMMIT

ROOT = Path(__file__).resolve().parent
INSTANCES = ROOT / "instances"
SCENARIOS = ROOT / "scenarios"
RESULTS = ROOT / "results"


def _write_instance(name: str, mode: str, seed: int) -> Path:
    INSTANCES.mkdir(parents=True, exist_ok=True)
    problem = synthesize_feeder(mode=mode, seed=seed)
    path = INSTANCES / name
    path.write_text(problem.model_dump_json(indent=2), encoding="utf-8")
    return path


def _row(label: str, seed: int, cfg: str, outcome, wall: float) -> dict:
    return {
        "instance": label,
        "input_hash": outcome.metadata.get("input_hash"),
        "seed": seed,
        "solver_config": cfg,
        "gridplan_version": GRIDPLAN_VERSION,
        "synaps_commit": SYNAPS_COMMIT,
        "wall_time_s": round(wall, 4),
        "status": outcome.status,
        "claim_status": outcome.metadata.get("claim_status"),
        "verified_feasible": outcome.verified_feasible,
        "hard_violation_count": outcome.hard_violation_count,
        "assignment_count": len(outcome.schedule.assignments),
        "coverage": outcome.schedule.objective.coverage,
        "tardiness_min": outcome.schedule.objective.total_tardiness_minutes,
        "makespan_min": outcome.schedule.objective.makespan_minutes,
        "risk_proxy_delta": (outcome.metadata.get("risk_proxy") or {}).get("risk_exposure_delta"),
        "metric_tag": "synthetic_experiment",
    }


def run(*, try_cpsat: bool = False) -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    SCENARIOS.mkdir(parents=True, exist_ok=True)
    small = _write_instance("feeder-small.json", "small", 42)
    medium = _write_instance("feeder-medium.json", "small", 7)

    configs = ["FIFO", "GREED"]
    if try_cpsat:
        configs.append("CPSAT-10")

    rows: list[dict] = []
    for path, label, seed in [(small, "small", 42), (medium, "medium-as-small", 7)]:
        problem = GridPlanProblem.model_validate_json(path.read_text(encoding="utf-8"))
        for cfg in configs:
            t0 = time.perf_counter()
            try:
                outcome = plan_with_config(problem, solver_config=cfg, apply_frozen=False)
            except Exception as exc:  # noqa: BLE001 — record CPSAT absence honestly
                rows.append(
                    {
                        "instance": label,
                        "seed": seed,
                        "solver_config": cfg,
                        "status": "error",
                        "verified_feasible": False,
                        "detail": str(exc),
                        "metric_tag": "synthetic_experiment",
                    }
                )
                continue
            wall = time.perf_counter() - t0
            rows.append(_row(label, seed, cfg, outcome, wall))

    problem = GridPlanProblem.model_validate_json(small.read_text(encoding="utf-8"))
    base = plan_with_config(problem, solver_config="GREED", apply_frozen=False)
    disrupted = [problem.jobs[0].id]
    repaired = replan_after_disruption(problem, base_outcome=base, disrupted_job_ids=disrupted)
    d = diff_plans(
        base=base.schedule,
        repaired=repaired.schedule,
        id_map=base.id_map,
        frozen=list(base.frozen_assignments),
        problem=problem,
        violations=repaired.metadata.get("gridplan_violations", []),
    )
    (SCENARIOS / "disruption.json").write_text(
        json.dumps(
            {
                "event_type": "job_disruption",
                "disrupted_job_ids": [str(x) for x in disrupted],
                "base_status": base.status,
                "repaired_status": repaired.status,
                "diff": d,
                "metric_tag": "synthetic_experiment",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = {
        "benchmark_protocol": "gridplan.benchmark.v1",
        "claim_level": "experiment",
        "data_provenance": "synthetic",
        "baselines": ["FIFO", "GREED"],
        "optional": ["CPSAT-10"] if try_cpsat else [],
        "rows": rows,
        "summary_hash": fingerprint_payload(rows),
        "applicability": [
            "Synthetic only. Not customer evidence.",
            "Heuristic FEASIBLE is not OPTIMAL.",
        ],
    }
    (RESULTS / "latest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    out = run(try_cpsat=False)
    print(json.dumps({"rows": len(out["rows"]), "hash": out["summary_hash"]}, indent=2))
