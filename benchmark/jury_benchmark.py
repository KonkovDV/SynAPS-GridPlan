"""Jury demo: synthetic РЭС «Северный» (not a live Россети site).

Scenario A — calendar FIFO vs GREED, with an independent check.
Scenario B — freeze two ПЛ rows, disrupt a storm set, replan.
Scenario C — same seed twice.

A plan is marked verified only when the checker agrees and hard violations are 0.
Heuristic GREED is never called optimal here. The violation table sums both
check layers (GridPlan rules and the SynAPS engine).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from synaps_gridplan.adapter import extract_frozen_from_result
from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.fingerprint import fingerprint_payload
from synaps_gridplan.planner import replan_after_disruption
from synaps_gridplan.report import ru_violation_counts
from synaps_gridplan.versions import GRIDPLAN_VERSION, ISO16290_TRL, SYNAPS_COMMIT

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT))
from res_severny_benchmark import build_res_problem  # noqa: E402


def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def _snapshot(outcome, wall_s: float) -> dict:
    return {
        "status": outcome.status,
        "claim_status": outcome.metadata.get("claim_status"),
        "verified_feasible": bool(outcome.verified_feasible),
        "assigned": len(outcome.schedule.assignments),
        "hard_violation_count": int(outcome.hard_violation_count),
        "violations_ru": ru_violation_counts(outcome),
        "wall_time_s": round(wall_s, 3),
    }


def _ok(snap: dict) -> bool:
    return bool(snap.get("verified_feasible")) and int(snap.get("hard_violation_count", 0)) == 0


def _mark(ok: bool) -> str:
    return "да" if ok else "нет"


def run() -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    problem = build_res_problem()

    fifo, t_fifo = _timed(
        lambda: plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    )
    greed, t_greed = _timed(
        lambda: plan_with_config(problem, solver_config="GREED", apply_frozen=False)
    )

    frozen_jobs = {"ТО Т-1 (Северная)", "ТО Т-1 (Заводская)"}
    ref_to_job = {j.external_ref: j.id for j in problem.jobs}
    frozen_op_ids = {
        greed.id_map.get(f"job:{ref_to_job[r]}") for r in frozen_jobs if r in ref_to_job
    }
    frozen = extract_frozen_from_result(
        problem,
        result_assignments=[
            a for a in greed.schedule.assignments if a.operation_id in frozen_op_ids
        ],
        id_map=greed.id_map,
        reason="заявка ПЛ согласована",
    )
    problem_frozen = problem.model_copy(update={"frozen_assignments": frozen})
    disrupted_refs = ["Облёт БПЛА ВЛ-110", "ТО КТП №5"] + [
        f"Осмотр Ф-{i} после грозы" for i in range(1, 5)
    ]
    disrupted = [ref_to_job[r] for r in disrupted_refs if r in ref_to_job]
    repaired, t_repair = _timed(
        lambda: replan_after_disruption(
            problem_frozen,
            base_outcome=greed,
            disrupted_job_ids=disrupted,
        )
    )
    diff = diff_plans(
        base=greed.schedule,
        repaired=repaired.schedule,
        id_map=greed.id_map,
        frozen=frozen,
        problem=problem,
        violations=repaired.metadata.get("gridplan_violations", []),
    )
    frozen_moved = sum(
        1
        for v in repaired.metadata.get("gridplan_violations", [])
        if v["kind"] == "FROZEN_ASSIGNMENT_CONFLICT"
    )

    greed2, _ = _timed(lambda: plan_with_config(problem, solver_config="GREED", apply_frozen=False))
    same_plan = [a.model_dump(mode="json") for a in greed.schedule.assignments] == [
        a.model_dump(mode="json") for a in greed2.schedule.assignments
    ]

    results = {
        "benchmark": "gridplan.jury.v2",
        "claim_level": "experiment",
        "iso16290_trl": ISO16290_TRL,
        "data_provenance": "synthetic",
        "instance_name": "res_severny_synthetic",
        "gridplan_version": GRIDPLAN_VERSION,
        "synaps_commit": SYNAPS_COMMIT,
        "instance": {
            "assets": len(problem.assets),
            "jobs": len(problem.jobs),
            "crews": len(problem.crews),
            "outage_windows": len(problem.outage_windows),
            "input_hash": greed.metadata.get("input_hash"),
        },
        "scenario_a": {
            "fifo": _snapshot(fifo, t_fifo),
            "greed": _snapshot(greed, t_greed),
        },
        "scenario_b": {
            "frozen_windows": len(frozen),
            "disrupted_jobs": [r for r in disrupted_refs if r in ref_to_job],
            "repaired": _snapshot(repaired, t_repair),
            "frozen_windows_moved": frozen_moved,
            "churn": diff["churn"],
        },
        "scenario_c": {
            "two_runs_identical": same_plan,
            "plan_fingerprint": fingerprint_payload(
                [a.model_dump(mode="json") for a in greed.schedule.assignments]
            ),
        },
    }
    (RESULTS / "jury_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (RESULTS / "jury_report.md").write_text(render_md(results), encoding="utf-8")
    return results


def render_md(r: dict) -> str:
    """Pure renderer — unit-tested so a dirty GREED plan cannot be labelled verified."""

    a, b, c = r["scenario_a"], r["scenario_b"], r["scenario_c"]
    inst = r["instance"]
    fifo_ok, greed_ok = _ok(a["fifo"]), _ok(a["greed"])
    repair_ok = _ok(b["repaired"])
    fifo_v = a["fifo"]["violations_ru"] or {"(нет расшифровки)": a["fifo"]["hard_violation_count"]}
    greed_v = a["greed"]["violations_ru"]
    fifo_rows = "\n".join(f"| {k} | {v} |" for k, v in fifo_v.items())
    greed_rows = "\n".join(f"| {k} | {v} |" for k, v in greed_v.items()) if greed_v else "| — | 0 |"
    if greed_ok:
        a_verdict = (
            "На этом синтетическом РЭС календарный FIFO даёт недопустимый график. "
            "GREED даёт график без жёстких нарушений; независимая проверка "
            "это подтверждает. Оптимальность GREED не утверждается."
        )
    else:
        a_verdict = (
            "GREED сократил число нарушений относительно FIFO, но независимая "
            "проверка **не** пройдена (см. таблицу). Этот прогон нельзя показывать "
            "как допустимый план."
        )
    if repair_ok:
        b_verdict = (
            f"Замороженные заявки ПЛ не сдвинуты ({b['frozen_windows_moved']} конфликтов). "
            "Перепланирование прошло проверку. Это не пилот на живой сети."
        )
    else:
        b_verdict = (
            f"Перепланирование не подтверждено (status={b['repaired']['status']}, "
            f"нарушений={b['repaired']['hard_violation_count']}). "
            f"Сдвигов заморозки: {b['frozen_windows_moved']}."
        )
    churn = b["churn"]
    slot_changes = churn["moved"] + churn["added"] + churn["removed"]
    return f"""# Демо-бенчмарк SynAPS-GridPlan

Синтетический РЭС «Северный» (открытые нормы и типы объектов, не данные ПАО «Россети»).
Версия GridPlan {r["gridplan_version"]}, SynAPS `{r["synaps_commit"][:12]}`, ISO 16290 TRL {r.get("iso16290_trl", 4)}.
GREED/FIFO — эвристики: `heuristic_feasible`, не `optimal`.

**Состав:** {inst["jobs"]} работ, {inst["crews"]} бригад, {inst["assets"]} активов,
{inst["outage_windows"]} окон отключений.

## A. Календарный FIFO и GREED

| Показатель | FIFO | GREED |
| --- | --- | --- |
| Работ назначено | {a["fifo"]["assigned"]} / {inst["jobs"]} | {a["greed"]["assigned"]} / {inst["jobs"]} |
| Жёстких нарушений | **{a["fifo"]["hard_violation_count"]}** | **{a["greed"]["hard_violation_count"]}** |
| Проверка | {_mark(fifo_ok)} | {_mark(greed_ok)} |
| Время, с | {a["fifo"]["wall_time_s"]} | {a["greed"]["wall_time_s"]} |

Расшифровка — сумма двух слоёв проверки (правила ТОиР GridPlan и движок SynAPS);
число в строке «Жёстких нарушений» равно сумме строк таблицы.

FIFO, расшифровка:

| Нарушение | Сколько |
| --- | ---: |
{fifo_rows}

GREED, расшифровка:

| Нарушение | Сколько |
| --- | ---: |
{greed_rows}

{a_verdict}

## B. Срыв работ при замороженных заявках ПЛ

Заморожено заявок: {b["frozen_windows"]}. Сорвано: {", ".join(b["disrupted_jobs"]) or "—"}.

| Показатель | Значение |
| --- | --- |
| Конфликтов с заморозкой | **{b["frozen_windows_moved"]}** |
| Проверка после ремонта | {_mark(repair_ok)} ({b["repaired"]["status"]}) |
| Слотов изменено | {slot_changes} |
| Время, с | {b["repaired"]["wall_time_s"]} |

{b_verdict}

## C. Повтор с тем же входом

| Проверка | Результат |
| --- | --- |
| Два запуска GREED совпали | {_mark(bool(c["two_runs_identical"]))} |
| Отпечаток (SHA-256) | `{c["plan_fingerprint"][:16]}…` |

## Границы

Синтетика. Нет расчёта N-1 и SAIDI, нет живых данных ДЗО. Показатель риска в продукте — справочный.
Доказательство оптимума makespan (CP-SAT, dual bound = факт) — `benchmark/res_severny_benchmark.py`, маркер pytest `slow`.
"""


if __name__ == "__main__":
    out = run()
    a = out["scenario_a"]
    print(
        json.dumps(
            {
                "greed_ok": _ok(a["greed"]),
                "fifo_ok": _ok(a["fifo"]),
                "repair_ok": _ok(out["scenario_b"]["repaired"]),
                "deterministic": out["scenario_c"]["two_runs_identical"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
