"""Campaign-scale feeder: GREED verified at 200 and 600 jobs."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.planner import PlanOutcome
from synaps_gridplan.report import ru_violation_counts
from synaps_gridplan.synthetic import synthesize_feeder
from synaps_gridplan.versions import GRIDPLAN_VERSION, SYNAPS_COMMIT

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def _timed(fn: Callable[[], PlanOutcome]) -> tuple[PlanOutcome, float]:
    t0 = time.perf_counter()
    out = fn()
    return out, round(time.perf_counter() - t0, 3)


def _snap(out: PlanOutcome, wall: float) -> dict[str, Any]:
    return {
        "assigned": len(out.schedule.assignments),
        "verified_feasible": bool(out.verified_feasible),
        "hard_violation_count": int(out.hard_violation_count),
        "violations_ru": ru_violation_counts(out),
        "wall_time_s": wall,
        "status": out.status,
    }


def _ok(snap: dict[str, Any]) -> bool:
    return bool(snap["verified_feasible"]) and int(snap["hard_violation_count"]) == 0


def _run_mode(mode: str, seed: int) -> dict[str, Any]:
    problem = synthesize_feeder(mode=mode, seed=seed)
    fifo, t_fifo = _timed(
        lambda: plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    )
    greed, t_greed = _timed(
        lambda: plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    )
    return {
        "mode": mode,
        "seed": seed,
        "jobs": len(problem.jobs),
        "assets": len(problem.assets),
        "crews": len(problem.crews),
        "windows": len(problem.outage_windows),
        "fifo": _snap(fifo, t_fifo),
        "greed": _snap(greed, t_greed),
    }


def render_md(rows: list[dict[str, Any]]) -> str:
    table = [
        "| Режим | Работ | GREED назн. | GREED наруш. | GREED | GREED, с | FIFO наруш. |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in rows:
        g, f = row["greed"], row["fifo"]
        mark = "да" if _ok(g) else "нет"
        table.append(
            f"| `{row['mode']}` seed={row['seed']} | {row['jobs']} | {g['assigned']} | "
            f"**{g['hard_violation_count']}** | {mark} | {g['wall_time_s']} | "
            f"**{f['hard_violation_count']}** |"
        )
    body = "\n".join(table)
    return f"""# Масштаб генератора (синтетический фидер)

Не именованный РЭС. Режимы `medium` (200) и `stress` (600) собраны как кампания:
одна линейная цепочка на актив, одно отключение в выделенном окне, склад не меньше
спроса, бригада закреплена. GREED проходит независимую проверку. Календарный FIFO
окна не соблюдает.

Именованный макет района — `jury_report.md` (55 работ, РЭС «Северный»).
Fail-closed демо на маленьком фидере — `small --seed 42` (ASSET_OVERLAP).

Версия GridPlan {GRIDPLAN_VERSION}, SynAPS `{SYNAPS_COMMIT[:12]}`.
Время стены — локальный прогон, не SLA.

{body}

Прогоны 50k/500k в README движка SynAPS — другой домен (не постановка ТОиР).
`feasibility_rate` оттуда на GridPlan не переносится.

```bash
python -m synaps_gridplan synthesize --mode medium --seed 12 -o medium.json
python -m synaps_gridplan solve medium.json --solver GREED -o medium-plan.json
# exit 0 — проверка пройдена
python -m synaps_gridplan synthesize --mode stress --seed 12 -o stress.json
python -m synaps_gridplan solve stress.json --solver GREED -o stress-plan.json
```
"""


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = [_run_mode("medium", 12), _run_mode("stress", 12)]
    (RESULTS / "scale_report.md").write_text(render_md(rows), encoding="utf-8")
    for row in rows:
        g = row["greed"]
        print(
            f"[scale] {row['mode']} jobs={row['jobs']} "
            f"greed_ok={_ok(g)} fifo_hard={row['fifo']['hard_violation_count']} "
            f"wall={g['wall_time_s']}"
        )
    print(f"[scale] report -> {RESULTS / 'scale_report.md'}")


if __name__ == "__main__":
    main()
