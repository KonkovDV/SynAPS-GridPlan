"""CLI entrypoints for SynAPS-GridPlan."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from synaps.model import ScheduleProblem, ScheduleResult

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.model import FrozenAssignment, GridPlanProblem
from synaps_gridplan.planner import PlanOutcome, replan_after_disruption
from synaps_gridplan.report import render_report
from synaps_gridplan.synthetic import synthesize_feeder
from synaps_gridplan.synthetic_gres import synthesize_gres_block
from synaps_gridplan.synthetic_hall import synthesize_dual_feed_hall

_FIXED_SYNTH: dict[str, Callable[..., GridPlanProblem]] = {
    "gres-block": synthesize_gres_block,
    "dual-feed-hall": synthesize_dual_feed_hall,
}


def _synthesize_problem(args: argparse.Namespace) -> GridPlanProblem:
    """Build a synthetic instance. Fixed modes reject feeder sizing flags."""

    builder = _FIXED_SYNTH.get(args.mode)
    if builder is not None:
        extras = [
            name
            for name, value in (
                ("--assets", args.assets),
                ("--jobs", args.jobs),
                ("--crews", args.crews),
            )
            if value is not None
        ]
        if extras:
            raise ValueError(
                f"{args.mode} is a fixed synthetic instance; omit " + ", ".join(extras)
            )
        return builder(seed=args.seed)
    return synthesize_feeder(
        n_assets=40 if args.assets is None else args.assets,
        n_jobs=200 if args.jobs is None else args.jobs,
        n_crews=10 if args.crews is None else args.crews,
        seed=args.seed,
        mode=args.mode,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="synaps-gridplan")
    sub = parser.add_subparsers(dest="command", required=True)

    p_syn = sub.add_parser(
        "synthesize",
        help="Write a synthetic feeder, GRES-block, or dual-feed hall JSON",
    )
    p_syn.add_argument(
        "--assets",
        type=int,
        default=None,
        help="feeder size (default 40); illegal with fixed modes",
    )
    p_syn.add_argument(
        "--jobs",
        type=int,
        default=None,
        help="feeder size (default 200); illegal with fixed modes",
    )
    p_syn.add_argument(
        "--crews",
        type=int,
        default=None,
        help="feeder size (default 10); illegal with fixed modes",
    )
    p_syn.add_argument("--seed", type=int, default=42)
    p_syn.add_argument(
        "--mode",
        default="medium",
        choices=[
            "small",
            "medium",
            "stress",
            "disruption",
            "infeasible",
            "frozen-conflict",
            "gres-block",
            "dual-feed-hall",
        ],
    )
    p_syn.add_argument("-o", "--output", type=Path, required=True)

    p_solve = sub.add_parser("solve", help="Solve a GridPlan JSON instance")
    p_solve.add_argument("input", type=Path)
    p_solve.add_argument(
        "--solver",
        default="GREED",
        help="FIFO | GREED | CPSAT-10 | CPSAT-30 | … (SynAPS configs)",
    )
    p_solve.add_argument("-o", "--output", type=Path, required=True)

    p_rep = sub.add_parser("report", help="Render a plan outcome JSON")
    p_rep.add_argument("input", type=Path)
    p_rep.add_argument("--format", choices=["json", "csv", "markdown"], default="markdown")

    p_dis = sub.add_parser("disrupt", help="Replan after disrupting job UUIDs")
    p_dis.add_argument("problem", type=Path)
    p_dis.add_argument("base_result", type=Path)
    p_dis.add_argument("--job-id", action="append", required=True)
    p_dis.add_argument("-o", "--output", type=Path, required=True)

    sub.add_parser("version", help="Print GridPlan version, SynAPS pin, and import path")
    sub.add_parser(
        "practice",
        help="Print world-practice alignment (citations; not a pilot claim)",
    )

    args = parser.parse_args(argv)

    if args.command == "synthesize":
        try:
            problem = _synthesize_problem(args)
        except ValueError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        args.output.write_text(problem.model_dump_json(indent=2), encoding="utf-8")
        return 0

    if args.command == "solve":
        problem = GridPlanProblem.model_validate_json(args.input.read_text(encoding="utf-8"))
        outcome = plan_with_config(problem, solver_config=args.solver)
        args.output.write_text(json.dumps(_payload(outcome), indent=2), encoding="utf-8")
        return 0 if outcome.ok else 2

    if args.command == "report":
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        outcome = _outcome_from_payload(raw)
        sys.stdout.write(render_report(outcome, fmt=args.format))
        if args.format != "json":
            sys.stdout.write("\n")
        return 0

    if args.command == "version":
        from synaps_gridplan.versions import GRIDPLAN_VERSION, ISO16290_TRL, SYNAPS_COMMIT

        sys.stdout.write(
            f"synaps-gridplan {GRIDPLAN_VERSION}\n"
            f"synaps_commit {SYNAPS_COMMIT}\n"
            f"iso16290_trl {ISO16290_TRL}\n"
            f"source {Path(__file__).resolve()}\n"
        )
        return 0

    if args.command == "practice":
        from synaps_gridplan.practice import render_practice_markdown

        text = render_practice_markdown()
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    if args.command == "disrupt":
        problem = GridPlanProblem.model_validate_json(args.problem.read_text(encoding="utf-8"))
        raw = json.loads(args.base_result.read_text(encoding="utf-8"))
        base = _outcome_from_payload(raw)
        job_ids = [UUID(x) for x in args.job_id]
        outcome = replan_after_disruption(
            problem,
            base_outcome=base,
            disrupted_job_ids=job_ids,
        )
        payload = _payload(outcome)
        payload["diff"] = diff_plans(
            base=base.schedule,
            repaired=outcome.schedule,
            id_map=base.id_map,
            frozen=list(outcome.frozen_assignments or problem.frozen_assignments),
            problem=problem,
            violations=outcome.metadata.get("gridplan_violations", []),
        )
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return 0 if outcome.ok else 2

    return 1


def _payload(outcome: PlanOutcome) -> dict:
    return {
        "outcome": {
            "schema_version": outcome.schema_version,
            "solver_config": outcome.solver_config,
            "status": outcome.status,
            "verified_feasible": outcome.verified_feasible,
            "hard_violation_count": outcome.hard_violation_count,
            "metadata": outcome.metadata,
            "id_map": {k: str(v) for k, v in outcome.id_map.items()},
            "frozen_assignments": [f.model_dump(mode="json") for f in outcome.frozen_assignments],
        },
        "schedule": json.loads(outcome.schedule.model_dump_json()),
        "schedule_problem": json.loads(outcome.schedule_problem.model_dump_json()),
        "report": json.loads(render_report(outcome, fmt="json")),
    }


def _outcome_from_payload(raw: dict) -> PlanOutcome:
    schedule = ScheduleResult.model_validate(raw.get("schedule", raw))
    oc = raw.get("outcome", raw)
    sp_raw = raw.get("schedule_problem")
    if sp_raw is None:
        raise SystemExit("result JSON missing schedule_problem (required for report/disrupt)")
    schedule_problem = ScheduleProblem.model_validate(sp_raw)
    frozen = tuple(FrozenAssignment.model_validate(x) for x in oc.get("frozen_assignments", []))
    return PlanOutcome(
        schema_version=oc.get("schema_version", "gridplan.v1"),
        solver_config=oc.get("solver_config", schedule.solver_name),
        status=oc.get("status", schedule.status.value),
        verified_feasible=bool(oc.get("verified_feasible", False)),
        schedule=schedule,
        schedule_problem=schedule_problem,
        id_map={k: UUID(v) for k, v in oc.get("id_map", {}).items()},
        hard_violation_count=int(oc.get("hard_violation_count", 0)),
        metadata=oc.get("metadata", {}),
        frozen_assignments=frozen,
    )


if __name__ == "__main__":
    raise SystemExit(main())
