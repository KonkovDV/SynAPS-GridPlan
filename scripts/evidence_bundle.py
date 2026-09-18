"""One-command evidence bundle: commit, environment, tests, jury, CP-SAT.

Machine-readable JSON goes to benchmark/results/ (gitignored). Markdown
summary is written beside it. CP-SAT runs on the same res_severny instance
as FIFO/GREED (jury scenario A/D), not on the scale feeder.

Not a plant pilot. Do not merge datasets into one score.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from synaps_gridplan.versions import GRIDPLAN_VERSION, ISO16290_TRL, SYNAPS_COMMIT

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmark" / "results"


def _git(args: list[str]) -> str:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return out.strip()


def _environment() -> dict[str, Any]:
    return {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "gridplan_version": GRIDPLAN_VERSION,
        "iso16290_trl": ISO16290_TRL,
        "synaps_commit": SYNAPS_COMMIT,
        "git_commit": _git(["rev-parse", "HEAD"]),
        "git_describe": _git(["describe", "--always", "--dirty"]),
        "git_dirty": bool(_git(["status", "--porcelain"])),
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "cwd": str(ROOT),
        "ci": os.environ.get("GITHUB_ACTIONS") == "true",
    }


def _run_cmd(cmd: list[str], *, timeout_s: int) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "wall_time_s": round(time.perf_counter() - t0, 3),
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def render_md(bundle: dict[str, Any]) -> str:
    env = bundle["environment"]
    jury = bundle.get("jury") or {}
    inst = jury.get("instance") or {}
    a = (jury.get("scenario_a") or {}).get("greed") or {}
    fifo = (jury.get("scenario_a") or {}).get("fifo") or {}
    cpsat = bundle.get("cpsat_res_severny") or {}
    tests = bundle.get("pytest") or {}
    dirty = "yes" if env.get("git_dirty") else "no"
    cmd = " ".join(tests.get("cmd") or [])
    python = str(env.get("python", ""))[:40]
    fifo_row = (
        f"| FIFO | {fifo.get('status')} | {fifo.get('verified_feasible')} | "
        f"{fifo.get('hard_violation_count')} | {fifo.get('wall_time_s')} |"
    )
    greed_row = (
        f"| GREED | {a.get('status')} | {a.get('verified_feasible')} | "
        f"{a.get('hard_violation_count')} | {a.get('wall_time_s')} |"
    )
    cpsat_row = (
        f"| CPSAT-30 | {cpsat.get('status')} | {cpsat.get('verified_feasible')} | "
        f"{cpsat.get('hard_violation_count')} | {cpsat.get('wall_time_s')} |"
    )
    return f"""# Evidence bundle

Запись `{env.get("recorded_at_utc")}`. Продукт {env.get("gridplan_version")},
ISO 16290 TRL {env.get("iso16290_trl")} (самооценка). SynAPS `{env.get("synaps_commit")}`.
Git `{env.get("git_commit")}` dirty={dirty}.
Python `{python}…`. Platform `{env.get("platform")}`.

Это лабораторный снимок, не пилот и не SLA. Датасеты не объединены.

## pytest

| поле | значение |
| --- | --- |
| returncode | {tests.get("returncode")} |
| wall_time_s | {tests.get("wall_time_s")} |
| cmd | `{cmd}` |

## РЭС «Северный» (один инстанс)

Состав снимка jury: {inst.get("jobs")} работ, {inst.get("crews")} бригад,
{inst.get("assets")} активов, {inst.get("outage_windows")} окон.

| solver | status | verified_feasible | hard_violations | wall_s |
| --- | --- | --- | --- | ---: |
{fifo_row}
{greed_row}
{cpsat_row}

CP-SAT bound: {cpsat.get("best_objective_bound")} ({cpsat.get("objective_bound_units")}).
Makespan CP-SAT: {cpsat.get("makespan_minutes")}. Оптимальность GREED из этой
таблицы не следует. Аварийные сутки и scale-фидер сюда не входят.

## Границы

Партнёрств и живых выгрузок ДЗО в снимке нет. 187-ФЗ / ГОСТ Р 58048 не
аттестованы. Воспроизведение: `python scripts/evidence_bundle.py`.
"""


def run(*, skip_pytest: bool, with_cpsat: bool, pytest_args: list[str]) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "benchmark"))
    from jury_benchmark import run as run_jury

    RESULTS.mkdir(parents=True, exist_ok=True)
    bundle: dict[str, Any] = {
        "bundle": "gridplan.evidence.v1",
        "claim_level": "experiment",
        "data_provenance": "synthetic",
        "environment": _environment(),
        "capability_tags": {
            "checker": "live",
            "greed_fifo": "prototype",
            "cpsat": "prototype",
            "fixtures": "mock",
            "shadow_pilot": "planned",
        },
    }
    if skip_pytest:
        bundle["pytest"] = {"skipped": True, "returncode": None, "cmd": []}
    else:
        cmd = [sys.executable, "-m", "pytest", "-q", *pytest_args]
        bundle["pytest"] = _run_cmd(cmd, timeout_s=900)
    bundle["jury"] = run_jury(with_cpsat=with_cpsat)
    if with_cpsat:
        bundle["cpsat_res_severny"] = bundle["jury"].get("scenario_d")
    json_path = RESULTS / "evidence_bundle.json"
    md_path = RESULTS / "evidence_bundle.md"
    json_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_md(bundle), encoding="utf-8")
    bundle["_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    return bundle


def bundle_ok(bundle: dict[str, Any]) -> bool:
    tests = bundle.get("pytest") or {}
    tests_ok = True if tests.get("skipped") else tests.get("returncode") == 0
    jury = bundle.get("jury") or {}
    greed = (jury.get("scenario_a") or {}).get("greed") or {}
    jury_ok = greed.get("verified_feasible") is True and greed.get("hard_violation_count") == 0
    cpsat = bundle.get("cpsat_res_severny")
    if cpsat is None:
        cpsat_ok = True
    else:
        cpsat_ok = (
            cpsat.get("status") == "optimal"
            and cpsat.get("verified_feasible") is True
            and cpsat.get("hard_violation_count") == 0
        )
    return bool(tests_ok and jury_ok and cpsat_ok)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Do not re-run pytest (use after CI tests already passed).",
    )
    parser.add_argument(
        "--no-cpsat",
        action="store_true",
        help="Skip CP-SAT on res_severny (not recommended for an evidence freeze).",
    )
    parser.add_argument("pytest_args", nargs="*", help="Extra args after pytest -q")
    args = parser.parse_args(argv)
    bundle = run(
        skip_pytest=args.skip_pytest,
        with_cpsat=not args.no_cpsat,
        pytest_args=args.pytest_args,
    )
    print(
        json.dumps(
            {
                "ok": bundle_ok(bundle),
                "json": bundle["_paths"]["json"],
                "markdown": bundle["_paths"]["markdown"],
                "git_commit": bundle["environment"]["git_commit"],
                "cpsat_status": (bundle.get("cpsat_res_severny") or {}).get("status"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if bundle_ok(bundle) else 2


if __name__ == "__main__":
    raise SystemExit(main())
