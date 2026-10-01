"""Time and Python-heap budget for synthetic scale-2k and scale-5k.

Prints wall time and the tracemalloc peak. Those figures are a process log.
They are not a row in ``docs/CLAIMS_REGISTRY.md``. Exit 2 when the wall time
exceeds ``--budget-s``, or when the plan is not verified unless
``--allow-unverified`` is set. The pinned GREED time cap does that on scale-5k.
"""

from __future__ import annotations

import argparse
import time
import tracemalloc

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.synthetic import synthesize_feeder

MODES = ("scale-2k", "scale-5k")


def run_budget(*, mode: str, seed: int, budget_s: float) -> dict[str, float | int | bool | str]:
    if mode not in MODES:
        raise ValueError(f"budget modes are {', '.join(MODES)}")
    tracemalloc.start()
    started = time.perf_counter()
    problem = synthesize_feeder(mode=mode, seed=seed)
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    wall_s = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "mode": mode,
        "seed": seed,
        "jobs": len(problem.jobs),
        "assigned": len(outcome.schedule.assignments),
        "verified_feasible": bool(outcome.verified_feasible),
        "hard_violation_count": int(outcome.hard_violation_count),
        "wall_s": round(wall_s, 3),
        "peak_bytes": int(peak),
        "within_budget": wall_s <= budget_s,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--seed", type=int, default=12)
    parser.add_argument("--budget-s", type=float, required=True)
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Accept a finished run that is not verified, if it stayed within the wall budget.",
    )
    args = parser.parse_args()
    row = run_budget(mode=args.mode, seed=args.seed, budget_s=args.budget_s)
    peak_mib = int(row["peak_bytes"]) / (1024 * 1024)
    print(
        f"[scale-budget] mode={row['mode']} seed={row['seed']} jobs={row['jobs']} "
        f"assigned={row['assigned']} verified={row['verified_feasible']} "
        f"hard={row['hard_violation_count']} wall_s={row['wall_s']} "
        f"peak_mib={peak_mib:.1f} budget_s={args.budget_s}"
    )
    verified = (
        row["verified_feasible"] is True
        and row["hard_violation_count"] == 0
        and row["assigned"] == row["jobs"]
    )
    within = row["within_budget"] is True
    ok = within and (verified or args.allow_unverified)
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
