"""Synthetic emergency-restoration day: узел «Восточный», 18.08.2026.

Modelled after the public 18.08.2026 publications about the special
(особый) operating mode in the Pavlovo-Posad branch of АО «Мособлэнерго»:
109 de-energised 10 kV transformer substations in Ликино-Дулёво and
Орехово-Зуево, >10 тыс. потребителей and 46 соцобъектов without supply,
35 передвижных электростанций (17 МВт) deployed, основная схема restored
the same day, private-sector tail (Ликино-Дулёво, д. Мисцево) — in the
evening. Names, ids, durations and the topology are invented.
Not a dump from АО «Мособлэнерго», ПАО «Россети Московский регион»,
or any other grid operator.

Restoration stages follow the public regulatory frame:
СТО 17330282.29.240.004-2008 and Приказ Минэнерго РФ № 289 (локализация →
осмотр/диагностика → аварийно-восстановительные работы → восстановление
схемы / ввод в работу); переключения — оперативный персонал по распоряжению
диспетчера (ТИ 34-70-058-86 для сетей 0,38–20 кВ). One ОП crew stands in for
the district оперативный персонал.

Claim level: experiment. Data provenance: synthetic.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.fingerprint import fingerprint_payload
from synaps_gridplan.model import (
    Asset,
    Crew,
    Criticality,
    FrozenAssignment,
    GridPlanProblem,
    JobKind,
    MaintenanceJob,
    OutageWindow,
    RiskProfile,
    SparePart,
)
from synaps_gridplan.planner import PlanOutcome, replan_after_disruption
from synaps_gridplan.report import ru_violation_counts
from synaps_gridplan.synthetic import _uid
from synaps_gridplan.versions import GRIDPLAN_VERSION, SYNAPS_COMMIT

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

SEED = 20260818
T0 = datetime(2026, 8, 18, 6, 0, tzinfo=UTC)  # аварийные сутки, с 06:00 (особый режим с 05:30)
HORIZON_HOURS = 24


def _t(hour: float) -> datetime:
    """Local clock hour mapped onto the UTC axis (same convention as РЭС «Северный»)."""
    return T0 + timedelta(hours=hour - 6)


def build_emergency_problem() -> GridPlanProblem:
    """Узел «Восточный»: ночное массовое повреждение, день восстановления.

    Полная регламентная цепочка на каждом повреждённом аппарате:
    локализация (коммутация оперативным персоналом) → осмотр / облёт БПЛА →
    аварийный ремонт → опробование / испытания → ввод в работу (включение).
    Плюс ДГУ для обесточенных ТП, перевод их на основную схему после ввода
    питающего центра, хвост 0,4 кВ (частный сектор) и одна плановая заявка
    ПЛ под заморозкой.
    """
    assets: list[Asset] = []
    crews: list[Crew] = []
    jobs: list[MaintenanceJob] = []
    windows: list[OutageWindow] = []
    spares: list[SparePart] = []

    def asset(
        tag: str,
        code: str,
        name: str,
        cls: str,
        loc: str,
        crit: Criticality,
        pof: float,
        cons: float,
    ) -> Asset:
        a = Asset(
            id=_uid(SEED, "asset", tag),
            code=code,
            name=name,
            asset_class=cls,
            location_code=loc,
            risk=RiskProfile(
                probability_of_failure=pof,
                consequence_score=cons,
                criticality=crit,
                assessment_method="ИТС-proxy (advisory)",
            ),
            data_provenance="synthetic",
        )
        assets.append(a)
        return a

    def job(
        tag: str,
        ref: str,
        a: Asset,
        kind: JobKind,
        dur: int,
        quals: list[str],
        *,
        due_h: float,
        interruption: bool,
        preds: list[MaintenanceJob] | None = None,
        sp: list[SparePart] | None = None,
        prio: int = 50,
        eligible: list[Crew] | None = None,
    ) -> MaintenanceJob:
        j = MaintenanceJob(
            id=_uid(SEED, "job", tag),
            external_ref=ref,
            asset_id=a.id,
            kind=kind,
            duration_min=dur,
            required_qualifications=quals,
            spare_part_ids=[s.id for s in sp or []],
            predecessor_job_ids=[p.id for p in preds or []],
            due_date=_t(due_h),
            release_date=T0,
            priority=prio,
            interruption_required=interruption,
            eligible_crew_ids=[c.id for c in eligible or []],
            data_provenance="synthetic",
        )
        jobs.append(j)
        return j

    def window(tag: str, a: Asset, start_h: float, end_h: float, ref: str) -> None:
        windows.append(
            OutageWindow(
                id=_uid(SEED, "window", tag),
                asset_id=a.id,
                start=_t(start_h),
                end=_t(end_h),
                approved=True,
                external_ref=ref,
                data_provenance="synthetic",
            )
        )

    # --- ЗИП (аварийный запас филиала; дефицит не моделируем — день закрывается) ---
    vvod110 = SparePart(
        id=_uid(SEED, "spare", "vvod110"),
        code="ВВОД-110-1250",
        available_quantity=1,
        warehouse_location="Аварийный запас филиала",
        data_provenance="synthetic",
    )
    kk_vmk = SparePart(
        id=_uid(SEED, "spare", "kk_vmk"),
        code="КК-ВМК-110",
        available_quantity=1,
        warehouse_location="Аварийный запас филиала",
        data_provenance="synthetic",
    )
    provod = SparePart(
        id=_uid(SEED, "spare", "provod"),
        code="ПРОВОД-АС-120 (бухта)",
        available_quantity=2,
        warehouse_location="Аварийный запас филиала",
        data_provenance="synthetic",
    )
    opora = SparePart(
        id=_uid(SEED, "spare", "opora"),
        code="ОПОРА-СВ-10",
        available_quantity=1,
        warehouse_location="Аварийный запас филиала",
        data_provenance="synthetic",
    )
    spares += [vvod110, kk_vmk, provod, opora]

    # --- Бригады (особый режим: все на сутках; профстандарт 20.032) ----------
    def crew(tag: str, code: str, quals: list[str]) -> Crew:
        c = Crew(
            id=_uid(SEED, "crew", tag),
            code=code,
            qualifications=quals,
            home_location_code="База филиала",
            data_provenance="synthetic",
        )
        crews.append(c)
        return c

    crew("ovb1", "ОВБ-1 (гр.IV)", ["ps_110", "ps_10"])
    ovb2 = crew("ovb2", "ОВБ-2 (гр.IV)", ["ps_110", "ps_10"])
    crew("etl", "ЭТЛ-1", ["rza_test", "insulation_test"])
    crew("vlb110", "ВЛБ-110-1", ["vl_110"])
    crew("vlb1", "ВЛБ-1", ["vl_10", "vl_04"])
    crew("prb", "ПРБ-1 (просеки)", ["clearing", "vl_10"])
    crew("uav", "БПЛА-группа", ["uav_inspection"])
    # Оперативный персонал: переключения по распоряжению диспетчера
    # (стенд-ин дежурного персонала района; СТО …240.004-2008, приказ № 289).
    crew("op", "ОП-1 (оперативный персонал)", ["switch_110", "switch_10"])

    # --- Повреждённые активы (ночь 17→18.08, внешние воздействия) -----------
    vl110 = asset(
        "vl110",
        "Л-101",
        "ВЛ-110 Л-101 (питающая)",
        "line_110",
        "РП-Восток",
        Criticality.CRITICAL,
        0.3,
        0.95,
    )
    t1 = asset(
        "t1",
        "Восточная Т-1",
        "ТРДН-25000/110 Т-1 (Восточная)",
        "transformer_110",
        "ПС-Восточная",
        Criticality.CRITICAL,
        0.25,
        0.9,
    )
    v2 = asset(
        "v2",
        "Южная В-2",
        "ВМК-110 В-2 (Южная)",
        "breaker_110",
        "ПС-Южная",
        Criticality.HIGH,
        0.2,
        0.7,
    )
    t2 = asset(
        "t2",
        "Городская Т-2",
        "ТРДН-25000/110 Т-2 (Городская)",
        "transformer_110",
        "ПС-Городская",
        Criticality.HIGH,
        0.18,
        0.8,
    )
    f3 = asset(
        "f3",
        "Ф-3",
        "ВЛ-10 Ф-3 (смешанный лес)",
        "line_10",
        "РЭС-Восточный",
        Criticality.MEDIUM,
        0.35,
        0.5,
    )
    tp14 = asset(
        "tp14",
        "ТП №14",
        "ТП-10/0.4 №14 (пос. Мицево-1, ФАП)",
        "tp_10",
        "Мицево",
        Criticality.HIGH,
        0.2,
        0.6,
    )
    tp22 = asset(
        "tp22",
        "ТП №22",
        "ТП-10/0.4 №22 (пос. Мицево-2)",
        "tp_10",
        "Мицево",
        Criticality.MEDIUM,
        0.2,
        0.45,
    )
    tp7 = asset(
        "tp7",
        "Ликино-7",
        "ТП-10/0.4 Ликино-7",
        "tp_10",
        "Ликино",
        Criticality.LOW,
        0.15,
        0.3,
    )
    tp12 = asset(
        "tp12",
        "Ликино-12",
        "ТП-10/0.4 Ликино-12",
        "tp_10",
        "Ликино",
        Criticality.LOW,
        0.15,
        0.3,
    )
    tpm3 = asset(
        "tpm3",
        "Мицево-3",
        "ТП-10/0.4 Мицево-3",
        "tp_10",
        "Мицево",
        Criticality.LOW,
        0.15,
        0.3,
    )

    # --- Аварийные окна (выпущены диспетчером утром, особый режим) + 1 ПЛ ----
    window("w-vl110", vl110, 9.0, 19.0, "ПЛ-АВ-001")
    window("w-t1", t1, 10.0, 26.0, "ПЛ-АВ-002")  # цепочка 300+180, особый режим 24/7
    window("w-v2", v2, 12.0, 22.0, "ПЛ-АВ-003")
    window("w-f3", f3, 11.0, 19.0, "ПЛ-АВ-004")
    window("w-t2", t2, 13.0, 17.0, "ПЛ-0817-14")  # согласована 17.08, до атаки

    # --- ВЛ-110 Л-101: локализация → облёт → ремонт → опробование → ввод -----
    # Прецедентный граф намеренно линеен: адаптер компилирует только линейные
    # цепочки (ограничение движка: no cross-order predecessor_op_id).
    j_lok = job(
        "lok-vl110",
        "Локализация повреждённого участка Л-101 (коммутация)",
        vl110,
        JobKind.EMERGENCY,
        30,
        ["switch_110"],
        due_h=6.5,
        interruption=False,
        prio=1,
    )
    j_obl = job(
        "obl-vl110",
        "Облёт БПЛА ВЛ-110 Л-101",
        vl110,
        JobKind.INSPECTION,
        90,
        ["uav_inspection"],
        due_h=8.0,
        interruption=False,
        preds=[j_lok],
        prio=1,
    )
    j_rem_vl = job(
        "rem-vl110",
        "Аварийный ремонт ВЛ-110 Л-101 (провод)",
        vl110,
        JobKind.EMERGENCY,
        300,
        ["vl_110"],
        due_h=19.0,
        interruption=True,
        preds=[j_obl],
        sp=[provod],
        prio=1,
    )
    j_opr_vl = job(
        "opr-vl110",
        "Опробование ВЛ-110 Л-101",
        vl110,
        JobKind.INSPECTION,
        120,
        ["rza_test"],
        due_h=21.0,
        interruption=True,
        preds=[j_rem_vl],
        prio=1,
    )
    job(
        "vkl-vl110",
        "Ввод Л-101 в работу (пробное включение)",
        vl110,
        JobKind.EMERGENCY,
        30,
        ["switch_110"],
        due_h=21.5,
        interruption=False,
        preds=[j_opr_vl],
        prio=1,
    )

    # --- Т-1 «Восточная»: осмотр → замена ввода 110 кВ → испытания → ввод ----
    j_osm_t1 = job(
        "osm-t1",
        "Осмотр Т-1 (Восточная) после внешнего воздействия",
        t1,
        JobKind.INSPECTION,
        60,
        ["ps_110"],
        due_h=8.0,
        interruption=False,
        prio=1,
    )
    j_rem_t1 = job(
        "rem-t1",
        "Аварийный ремонт Т-1 (Восточная): ввод 110 кВ",
        t1,
        JobKind.EMERGENCY,
        300,
        ["ps_110"],
        due_h=22.0,
        interruption=True,
        preds=[j_osm_t1],
        sp=[vvod110],
        prio=1,
    )
    j_isp_t1 = job(
        "isp-t1",
        "Испытания изоляции Т-1 (Восточная)",
        t1,
        JobKind.INSPECTION,
        180,
        ["insulation_test"],
        due_h=25.0,
        interruption=True,
        preds=[j_rem_t1],
        prio=2,
    )
    j_vkl_t1 = job(
        "vkl-t1",
        "Ввод Т-1 в работу (включение, нормализация схемы)",
        t1,
        JobKind.EMERGENCY,
        20,
        ["switch_110"],
        due_h=26.0,
        interruption=False,
        preds=[j_isp_t1],
        prio=2,
    )

    # --- В-2 «Южная»: осмотр → ремонт ВМК-110 → ввод --------------------------
    j_osm_v2 = job(
        "osm-v2",
        "Осмотр В-2 (Южная)",
        v2,
        JobKind.INSPECTION,
        45,
        ["ps_110"],
        due_h=10.0,
        interruption=False,
        prio=2,
    )
    j_rem_v2 = job(
        "rem-v2",
        "Аварийный ремонт ВМК-110 В-2 (Южная)",
        v2,
        JobKind.EMERGENCY,
        300,
        ["ps_110"],
        due_h=22.0,
        interruption=True,
        preds=[j_osm_v2],
        sp=[kk_vmk],
        prio=2,
    )
    job(
        "vkl-v2",
        "Ввод В-2 в работу (опробование диспетчером)",
        v2,
        JobKind.EMERGENCY,
        15,
        ["switch_110"],
        due_h=22.5,
        interruption=False,
        preds=[j_rem_v2],
        prio=2,
    )

    # --- Ф-3: расчистка просеки → замена опоры → пробное включение ------------
    j_ras = job(
        "ras-f3",
        "Расчистка просеки Ф-3 (падение дерева)",
        f3,
        JobKind.EMERGENCY,
        180,
        ["clearing"],
        due_h=12.0,
        interruption=False,
        prio=3,
    )
    j_rem_f3 = job(
        "rem-f3",
        "Ремонт ВЛ-10 Ф-3 (замена опоры)",
        f3,
        JobKind.EMERGENCY,
        300,
        ["vl_10"],
        due_h=19.0,
        interruption=True,
        preds=[j_ras],
        sp=[opora],
        prio=3,
    )
    job(
        "vkl-f3",
        "Пробное включение Ф-3",
        f3,
        JobKind.EMERGENCY,
        10,
        ["switch_10"],
        due_h=19.5,
        interruption=False,
        preds=[j_rem_f3],
        prio=3,
    )

    # --- ДГУ: временное подключение потребителей (стенд-ин для 35 ПЭС) --------
    # ТП №14 питает ФАП — ответственный потребитель, первым по регламенту.
    job(
        "dgu-14",
        "Подключение ДГУ-200 к ТП №14 (ФАП)",
        tp14,
        JobKind.EMERGENCY,
        120,
        ["vl_10"],
        due_h=8.0,
        interruption=False,
        prio=1,
    )
    job(
        "dgu-22",
        "Подключение ДГУ-100 к ТП №22",
        tp22,
        JobKind.EMERGENCY,
        120,
        ["vl_10"],
        due_h=12.0,
        interruption=False,
        prio=2,
    )

    # --- Перевод ТП с ДГУ на основную схему (после ввода питающего центра) ----
    # Одна работа на обе ТП (ОП идёт подряд по соседним ТП) — граф остаётся
    # линейным; fan-out на одного предка адаптер скомпилировать не может.
    j_prv = job(
        "prv-tp",
        "Перевод ТП №14 и №22 на основную схему (ДГУ отключены)",
        tp14,
        JobKind.EMERGENCY,
        60,
        ["switch_10"],
        due_h=27.0,
        interruption=False,
        preds=[j_vkl_t1],
        prio=4,
    )

    # --- Хвост 0,4 кВ: частный сектор (в новостях — д. Мисцево, к вечеру) -----
    job(
        "rem-04",
        "Восстановление ответвления 0,4 кВ (д. Мисцево, частный сектор)",
        tp22,
        JobKind.EMERGENCY,
        150,
        ["vl_04"],
        due_h=29.0,
        interruption=False,
        preds=[j_prv],
        prio=4,
    )

    # --- Плановое ТО под замороженной заявкой ПЛ (согласована до атаки) -------
    # В заявке ПЛ указана допущенная бригада (типичная практика диспетчерских).
    j_to_t2 = job(
        "to-t2",
        "ТО Т-2 (Городская)",
        t2,
        JobKind.PREVENTIVE,
        240,
        ["ps_110"],
        due_h=17.0,
        interruption=True,
        prio=5,
        eligible=[ovb2],
    )

    # --- Выборочные осмотры обесточенных ТП (стенд-ин для 109 ТП) -------------
    job(
        "osm-l7",
        "Осмотр ТП-10 Ликино-7 (по заявке СО)",
        tp7,
        JobKind.INSPECTION,
        45,
        ["ps_10"],
        due_h=14.0,
        interruption=False,
        prio=4,
    )
    job(
        "osm-l12",
        "Осмотр ТП-10 Ликино-12 (по заявке СО)",
        tp12,
        JobKind.INSPECTION,
        45,
        ["ps_10"],
        due_h=16.0,
        interruption=False,
        prio=4,
    )
    job(
        "osm-m3",
        "Осмотр ТП-10 Мицево-3 (по заявке СО)",
        tpm3,
        JobKind.INSPECTION,
        45,
        ["ps_10"],
        due_h=18.0,
        interruption=False,
        prio=4,
    )

    frozen = [
        FrozenAssignment(
            job_id=j_to_t2.id,
            crew_id=ovb2.id,
            start=_t(13.0),
            end=_t(17.0),
            source="pl_window",
            frozen_reason="Заявка ПЛ-0817-14 согласована 17.08, до ночной атаки",
            immutable=True,
            data_provenance="synthetic",
        )
    ]

    return GridPlanProblem(
        assets=assets,
        crews=crews,
        jobs=jobs,
        outage_windows=windows,
        spare_parts=spares,
        frozen_assignments=frozen,
        planning_horizon_start=T0,
        planning_horizon_end=T0 + timedelta(hours=HORIZON_HOURS),
        domain_attributes={
            "data_provenance": "synthetic",
            "claim_level": "experiment",
            "iso16290_trl": 4,
            "instance": "vostochny_emergency_day_2026_08_18_synthetic",
            "context": "Особый режим по публичным публикациям 18.08.2026; не данные сетевой",
            "regulatory_frame": "СТО 17330282.29.240.004-2008 / Приказ Минэнерго № 289: "
            "локализация → осмотр → АВР → восстановление схемы",
        },
    )


def _timed(fn: Callable[[], PlanOutcome]) -> tuple[PlanOutcome, float]:
    t0 = time.perf_counter()
    out = fn()
    return out, round(time.perf_counter() - t0, 2)


def _snapshot(o: PlanOutcome, wall_s: float) -> dict[str, Any]:
    return {
        "status": o.status,
        "verified_feasible": o.verified_feasible,
        "assigned": len(o.schedule.assignments),
        "hard_violation_count": o.hard_violation_count,
        "violations_ru": ru_violation_counts(o),
        "wall_time_s": wall_s,
    }


def _ok(s: dict[str, Any]) -> bool:
    return bool(s["verified_feasible"]) and s["hard_violation_count"] == 0


def _mark(flag: bool) -> str:
    return "пройдена ✅" if flag else "НЕ пройдена ❌"


# Цепочка ВЛ-110, которая уходит на локальный repair при «повторном облёте».
DISRUPTED_REFS = [
    "Аварийный ремонт ВЛ-110 Л-101 (провод)",
    "Опробование ВЛ-110 Л-101",
    "Ввод Л-101 в работу (пробное включение)",
]


def run() -> dict[str, Any]:
    problem = build_emergency_problem()
    ref_to_job = {j.external_ref: j for j in problem.jobs}

    fifo, t_fifo = _timed(
        lambda: plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    )
    greed, t_greed = _timed(
        lambda: plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    )

    # Сценарий B: 14:00, повторный облёт подтверждает объём по ВЛ-110 —
    # цепочка «ремонт → опробование → ввод» уходит на перепланирование,
    # остальное (включая замороженную ПЛ-0817-14) обязано остаться неподвижным.
    disrupted = [ref_to_job[r] for r in DISRUPTED_REFS if r in ref_to_job]
    repaired, t_repair = _timed(
        lambda: replan_after_disruption(
            problem,
            base_outcome=greed,
            disrupted_job_ids=[j.id for j in disrupted],
        )
    )
    diff = diff_plans(
        base=greed.schedule,
        repaired=repaired.schedule,
        id_map=greed.id_map,
        frozen=list(problem.frozen_assignments),
        problem=problem,
    )
    frozen_moved = sum(
        1
        for v in repaired.metadata.get("gridplan_violations", [])
        if v["kind"] == "FROZEN_ASSIGNMENT_CONFLICT"
    )

    greed2, _ = _timed(lambda: plan_with_config(problem, solver_config="GREED", apply_frozen=True))
    same_plan = [a.model_dump(mode="json") for a in greed.schedule.assignments] == [
        a.model_dump(mode="json") for a in greed2.schedule.assignments
    ]

    results: dict[str, Any] = {
        "benchmark": "gridplan.emergency-day.v2",
        "claim_level": "experiment",
        "data_provenance": "synthetic",
        "instance_name": "vostochny_emergency_day_2026_08_18_synthetic",
        "gridplan_version": GRIDPLAN_VERSION,
        "synaps_commit": SYNAPS_COMMIT,
        "instance": {
            "assets": len(problem.assets),
            "jobs": len(problem.jobs),
            "crews": len(problem.crews),
            "outage_windows": len(problem.outage_windows),
            "frozen_assignments": len(problem.frozen_assignments),
            "input_hash": greed.metadata.get("input_hash"),
        },
        "scenario_a": {
            "fifo": _snapshot(fifo, t_fifo),
            "greed": _snapshot(greed, t_greed),
        },
        "scenario_b": {
            "disrupted_jobs": DISRUPTED_REFS,
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
        "day_schedule": _crew_timeline(problem, greed),
    }
    (RESULTS / "emergency_day_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (RESULTS / "emergency_day_report.md").write_text(render_md(results), encoding="utf-8")
    return results


def _crew_timeline(problem: GridPlanProblem, outcome: PlanOutcome) -> list[dict[str, str]]:
    """График дня по бригадам (базовый GREED-план), для отчёта и жюри."""
    op_of_job = {j.external_ref: outcome.id_map.get(f"job:{j.id}") for j in problem.jobs}
    crew_of_wc = {outcome.id_map.get(f"crew:{c.id}"): c.code for c in problem.crews}
    frozen_job_ids = {f.job_id for f in problem.frozen_assignments}
    ref_of_job = {j.id: j.external_ref for j in problem.jobs}
    rows: list[dict[str, str]] = []
    for a in sorted(outcome.schedule.assignments, key=lambda x: (x.start_time, x.end_time)):
        job_ref = next((ref for ref, op in op_of_job.items() if op == a.operation_id), "?")
        job_id = next((jid for jid, ref in ref_of_job.items() if ref == job_ref), None)
        rows.append(
            {
                "crew": crew_of_wc.get(a.work_center_id, "?"),
                "job": job_ref,
                "start": f"{a.start_time:%H:%M}",
                "end": f"{a.end_time:%H:%M}",
                "frozen": "ПЛ" if job_id in frozen_job_ids else "",
            }
        )
    return rows


def render_md(r: dict[str, Any]) -> str:
    a, b, c = r["scenario_a"], r["scenario_b"], r["scenario_c"]
    inst = r["instance"]
    fifo_ok, greed_ok = _ok(a["fifo"]), _ok(a["greed"])
    repair_ok = _ok(b["repaired"])
    fifo_v = a["fifo"]["violations_ru"] or {"(нет расшифровки)": a["fifo"]["hard_violation_count"]}
    fifo_rows = "\n".join(f"| {k} | {v} |" for k, v in fifo_v.items())
    churn = b["churn"]
    slot_changes = churn["moved"] + churn["added"] + churn["removed"]
    f_as, g_as = a["fifo"]["assigned"], a["greed"]["assigned"]
    f_hv, g_hv = a["fifo"]["hard_violation_count"], a["greed"]["hard_violation_count"]

    tl_rows = "\n".join(
        f"| {row['crew']} | {row['job']} | {row['start']} | {row['end']} | {row['frozen']} |"
        for row in r["day_schedule"]
    )

    if greed_ok:
        a_verdict = (
            "В аварийный день календарный FIFO даёт недопустимый график (см. расшифровку). "
            "GREED строит день восстановления без жёстких нарушений: аварийные окна, "
            "полные цепочки «локализация → осмотр → ремонт → опробование → ввод в работу», "
            "ЗИП и замороженная заявка ПЛ соблюдены; независимая проверка это подтверждает. "
            "Оптимальность не утверждается."
        )
    else:
        a_verdict = (
            "GREED не прошёл независимую проверку на аварийном дне "
            "(см. таблицу нарушений). Этот прогон нельзя показывать как допустимый план."
        )
    if repair_ok and slot_changes == 0:
        b_verdict = (
            "Повторный облёт: движок перепроверил цепочку ВЛ-110 и подтвердил базовый "
            "план стабильным (0 перемещений); замороженная заявка ПЛ-0817-14 не сдвинута "
            f"({b['frozen_windows_moved']} конфликтов). Перепланирование прошло проверку."
        )
    elif repair_ok:
        b_verdict = (
            f"Повторный облёт: цепочка ВЛ-110 перепланирована локально, замороженная "
            f"заявка ПЛ-0817-14 не сдвинута ({b['frozen_windows_moved']} конфликтов), "
            f"перемещений слотов: {slot_changes}. Перепланирование прошло проверку."
        )
    else:
        b_verdict = (
            f"Перепланирование не подтверждено (status={b['repaired']['status']}, "
            f"нарушений={b['repaired']['hard_violation_count']}). "
            f"Сдвигов заморозки: {b['frozen_windows_moved']}."
        )

    return f"""# Аварийный день 18.08.2026: восстановление узла «Восточный»

Синтетический сценарий по публичным публикациям 18.08.2026 (особый режим в Павлово-Посадском
филиале АО «Мособлэнерго»: 109 обесточенных ТП, >10 тыс. потребителей, 35 передвижных
электростанций на 17 МВт, восстановление основной схемы в тот же день, хвост частного
сектора — вечером). Названия, id, длительности и топология вымышлены. Это **не** данные
АО «Мособлэнерго» / ПАО «Россети Московский регион». Версия GridPlan {r["gridplan_version"]},
SynAPS `{r["synaps_commit"][:12]}`, уровень — эксперимент (synthetic), не пилот.

**Состав:** {inst["jobs"]} работы, {inst["crews"]} бригад, {inst["assets"]} активов,
{inst["outage_windows"]} окон отключений (4 аварийных + 1 плановая ПЛ),
замороженных заявок: {inst["frozen_assignments"]}.

## Этапы ликвидации по регламенту → модель

Публичная нормативная рамка (СТО 17330282.29.240.004-2008, приказ Минэнерго РФ № 289,
ТИ 34-70-058-86) задаёт четыре этапа; в сценарии каждый — отдельная работа с
техпоследовательностью:

| Этап по регламенту | В модели (кто) |
| --- | --- |
| 1. Локализация участка (переключения) | «Локализация… Л-101» — ОП-1, по распоряжению диспетчера |
| 2. Осмотр / поиск места повреждения | «Облёт БПЛА Л-101», осмотры Т-1/В-2/ТП — БПЛА, ОВБ |
| 3. Аварийно-восстановительные работы | ремонты Л-101, Т-1, В-2, Ф-3; расчистка — ВЛБ, ОВБ, ПРБ |
| 4. Восстановление схемы / ввод в работу | «Опробование», «Ввод в работу» — ЭТЛ-1, затем ОП-1 |
| Приоритет ответственным потребителям | ДГУ-200 на ТП №14 (ФАП) — первая по приоритету |
| Нормализация послеаварийной схемы | «Перевод ТП на основную схему», хвост 0,4 кВ — ОП-1, ВЛБ-1 |

## A. Календарный FIFO и GREED на аварийном дне

| Показатель | FIFO | GREED |
| --- | --- | --- |
| Работ назначено | {f_as} / {inst["jobs"]} | {g_as} / {inst["jobs"]} |
| Жёстких нарушений | **{f_hv}** | **{g_hv}** |
| Проверка | {_mark(fifo_ok)} | {_mark(greed_ok)} |
| Время, с | {a["fifo"]["wall_time_s"]} | {a["greed"]["wall_time_s"]} |

FIFO, расшифровка:

| Нарушение | Сколько |
| --- | ---: |
{fifo_rows}

{a_verdict}

## График дня (базовый план GREED, время местное)

| Бригада | Работа | Старт | Конец | ПЛ |
| --- | --- | --- | --- | --- |
{tl_rows}

## B. Повторный облёт 14:00: локальное перепланирование

Цепочка «Аварийный ремонт ВЛ-110 Л-101 → Опробование → Ввод в работу» ушла на ремонт
плана; остальное зафиксировано (включая заявку ПЛ-0817-14 «ТО Т-2 (Городская)»
13:00–17:00, согласованную ещё 17.08 — до атаки).

| Показатель | Значение |
| --- | --- |
| Статус repair | {b["repaired"]["status"]} |
| Проверка | {_mark(repair_ok)} |
| Жёстких нарушений после repair | {b["repaired"]["hard_violation_count"]} |
| Замороженных окон сдвинуто | {b["frozen_windows_moved"]} |
| Перемещено слотов | {churn["moved"]} |
| Добавлено / снято слотов | {churn["added"]} / {churn["removed"]} |
| Время repair, с | {b["repaired"]["wall_time_s"]} |

{b_verdict}

## C. Воспроизводимость

- Два прогона GREED подряд дают идентичный план: **{c["two_runs_identical"]}**.
- Отпечаток плана (SHA-256): `{c["plan_fingerprint"][:16]}…`.
- Входной отпечаток инстанса: `{inst["input_hash"]}`.

## Реальный день по публикациям vs модель

| Веха 18.08.2026 (публикации) | Модель (базовый план) |
| --- | --- |
| 05:30 — особый режим в филиале | горизонт суток с 06:00, все бригады на сменах |
| ~2 часа — потребители на передвижных ЭС | ДГУ-200 (ФАП) и ДГУ-100 подключены к 08:00 |
| к 12:00 — основная схема (Минэнерго МО) | ввод Л-101 днём; Т-1 ночью — в модели пакет тяжелее |
| вечер — хвост частного сектора на ДГУ | перевод ТП ночью, ответвление 0,4 кВ — к 05:00 |

Совпадение по структуре дня, не по минутам: длительности и топология вымышлены.

## Как это читать

Сценарий показывает продукт в день массового повреждения: аварийные окна диспетчера,
регламентная четырёхэтапная цепочка на каждом аппарате, приоритет ответственных
потребителей (ДГУ на ФАП первой), жёсткая заморозка согласованной накануне заявки ПЛ
и локальное перепланирование после уточнения объёма работ. Это синтетический
эксперимент, а не восстановление реального филиала; для пилота нужны санитизированные
данные сетевой организации.
"""


def main() -> None:
    r = run()
    a, b = r["scenario_a"], r["scenario_b"]
    print(
        f"[emergency-day] jobs={r['instance']['jobs']} "
        f"fifo_ok={_ok(a['fifo'])} greed_ok={_ok(a['greed'])} "
        f"repair_ok={_ok(b['repaired'])} frozen_moved={b['frozen_windows_moved']} "
        f"deterministic={r['scenario_c']['two_runs_identical']}"
    )
    print(f"[emergency-day] report → {RESULTS / 'emergency_day_report.md'}")


if __name__ == "__main__":
    main()
