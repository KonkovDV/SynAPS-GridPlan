"""Synthetic monthly ТОиР instance: РЭС «Северный».

Typical 110/35/10 kV district shape and public duration norms (СТО 34.01-24,
Minenergo order 1013, occupational standard 20.032). Invented topology and
ids. Not a dump from ПАО «Россети» or any DZO.

Claim level: experiment. Data provenance: synthetic.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from synaps_gridplan.adapter import extract_frozen_from_result
from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.diff import diff_plans
from synaps_gridplan.fingerprint import fingerprint_payload
from synaps_gridplan.model import (
    Asset,
    Crew,
    Criticality,
    GridPlanProblem,
    JobKind,
    MaintenanceJob,
    OutageWindow,
    RiskProfile,
    SimultaneousOutageBan,
    SparePart,
)
from synaps_gridplan.planner import replan_after_disruption
from synaps_gridplan.report import ru_violation_counts
from synaps_gridplan.synthetic import _uid
from synaps_gridplan.versions import GRIDPLAN_VERSION, SYNAPS_COMMIT

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

SEED = 20260901
T0 = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)  # месячный график на сентябрь 2026
HORIZON_DAYS = 30


def _w(
    seed_tag: str, asset_id: UUID, days: list[int], start_h: int, dur_h: int
) -> list[OutageWindow]:
    """Approved outage windows (диспетчерские заявки категории ПЛ)."""
    return [
        OutageWindow(
            id=_uid(SEED, "window", seed_tag, str(d)),
            asset_id=asset_id,
            start=T0 + timedelta(days=d, hours=start_h - 6),
            end=T0 + timedelta(days=d, hours=start_h + dur_h - 6),
            approved=True,
            external_ref=f"ПЛ-{seed_tag}-{d:02d}",
            data_provenance="synthetic",
        )
        for d in days
    ]


def build_res_problem() -> GridPlanProblem:
    """РЭС «Северный»: 2 ПС-110, 3 ПС-35, 6 фидеров 10 кВ, 12 ТП, 5 ВЛ-0.4."""
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
        due_d: int,
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
            due_date=T0 + timedelta(days=due_d),
            release_date=T0,
            priority=prio,
            interruption_required=interruption,
            eligible_crew_ids=[c.id for c in eligible or []],
            data_provenance="synthetic",
        )
        jobs.append(j)
        return j

    # --- ЗИП (склад РЭС) ------------------------------------------------------
    shf20 = SparePart(
        id=_uid(SEED, "spare", "shf20"),
        code="ШФ-20",
        available_quantity=24,
        warehouse_location="Склад РЭС",
        data_provenance="synthetic",
    )
    kontakt_vmk = SparePart(
        id=_uid(SEED, "spare", "vmk110"),
        code="КК-ВМК-110",
        available_quantity=4,
        warehouse_location="Склад РЭС",
        data_provenance="synthetic",
    )
    maslo = SparePart(
        id=_uid(SEED, "spare", "oil"),
        code="МАСЛО-Т",
        available_quantity=4,
        warehouse_location="Склад РЭС",
        data_provenance="synthetic",
    )
    spares += [shf20, kontakt_vmk, maslo]

    # --- Бригады (профстандарт 20.032; ОВБ 2–3 чел., старший — гр. IV) --------
    def crew(tag: str, code: str, quals: list[str]) -> Crew:
        c = Crew(
            id=_uid(SEED, "crew", tag),
            code=code,
            qualifications=quals,
            home_location_code="База РЭС",
            data_provenance="synthetic",
        )
        crews.append(c)
        return c

    crew("ovb1", "ОВБ-1 (гр.IV)", ["ps_110", "ps_10"])
    crew("ovb2", "ОВБ-2 (гр.IV)", ["ps_110", "ps_10"])
    crew("etl", "ЭТЛ-1", ["rza_test", "insulation_test"])
    crew("vlb1", "ВЛБ-1", ["vl_10", "vl_04"])
    crew("vlb2", "ВЛБ-2", ["vl_10", "vl_04"])
    crew("prb", "ПРБ-1 (просеки)", ["clearing", "vl_10"])
    pbk = crew("kap", "ПБК-1 (подрядчик)", ["capital_repair"])

    # --- ПС 110/10 кВ «Северная» и «Заводская» (по 2×ТРДН-25000 + 2×ВМК-110) --
    # Окна 07:00–21:00 (две смены): цепочка ТО(8ч)+испытания(4ч)+переезды должна
    # целиком помещаться в первое окно (адаптер ставит due = конец 1-го окна).
    # Первые окна разнесены по дням, чтобы бригады не конкурировали за один день.
    for ps, base_day in (("Северная", 2), ("Заводская", 9)):
        for k, unit in enumerate(("Т-1", "Т-2", "В-1", "В-2")):
            days = [base_day + k, base_day + k + 7, base_day + k + 14]
            if unit.startswith("Т"):
                a = asset(
                    f"{ps}-{unit}",
                    f"{ps} {unit}",
                    f"ТРДН-25000/110 {unit} ({ps})",
                    "transformer_110",
                    f"ПС-{ps}",
                    Criticality.CRITICAL if unit == "Т-1" else Criticality.HIGH,
                    0.18,
                    0.9,
                )
                windows += _w(f"{ps}-{unit}", a.id, days, 7, 14)
                to = job(
                    f"to-{ps}-{unit}",
                    f"ТО {unit} ({ps})",
                    a,
                    JobKind.PREVENTIVE,
                    480,
                    ["ps_110"],
                    due_d=days[0] + 1,
                    interruption=True,
                    prio=10,
                )
                job(
                    f"isp-{ps}-{unit}",
                    f"Испытания изоляции {unit} ({ps})",
                    a,
                    JobKind.INSPECTION,
                    240,
                    ["insulation_test"],
                    due_d=days[0] + 1,
                    interruption=True,
                    preds=[to],
                    prio=20,
                )
            else:
                a = asset(
                    f"{ps}-{unit}",
                    f"{ps} {unit}",
                    f"ВМК-110 {unit} ({ps})",
                    "breaker_110",
                    f"ПС-{ps}",
                    Criticality.HIGH,
                    0.22,
                    0.7,
                )
                windows += _w(f"{ps}-{unit}", a.id, days, 7, 14)
                tr = job(
                    f"tr-{ps}-{unit}",
                    f"Текущий ремонт {unit} ({ps})",
                    a,
                    JobKind.CORRECTIVE,
                    540,
                    ["capital_repair"],
                    due_d=days[0] + 1,
                    interruption=True,
                    sp=[kontakt_vmk],
                    prio=15,
                    eligible=[pbk],
                )
                job(
                    f"opr-{ps}-{unit}",
                    f"Опробование {unit} ({ps})",
                    a,
                    JobKind.INSPECTION,
                    120,
                    ["rza_test"],
                    due_d=days[0] + 1,
                    interruption=True,
                    preds=[tr],
                    prio=25,
                )
    # Ревизия РПН Т-1 «Северная» (доливка масла). Нельзя ставить в то же окно,
    # что ТО+испытания: одно отключение на аппарат.
    # Первое окно — только цепочка ТО→испытания; второе — только РПН.
    t1_sev = next(a for a in assets if a.code == "Северная Т-1")
    to_sev = next(j for j in jobs if j.external_ref == "ТО Т-1 (Северная)")
    isp_sev = next(j for j in jobs if j.external_ref == "Испытания изоляции Т-1 (Северная)")
    rpn_sev = job(
        "rpn-sev",
        "Ревизия РПН Т-1 (Северная)",
        t1_sev,
        JobKind.CORRECTIVE,
        360,
        ["ps_110"],
        due_d=18,
        interruption=True,
        sp=[maslo],
        prio=30,
    )
    t1_wins = sorted((w for w in windows if w.asset_id == t1_sev.id), key=lambda w: w.start)
    # День 0/1 — цепочка ТО→испытания (и запасной слот); день 2 — только РПН,
    # чтобы не отжимать ОВБ у ПС «Заводская» в её первом окне.
    t1_wins[0].allowed_job_ids = [to_sev.id, isp_sev.id]
    t1_wins[1].allowed_job_ids = [to_sev.id, isp_sev.id]
    t1_wins[2].allowed_job_ids = [rpn_sev.id]

    # --- ПС 35/10 кВ (по 2×ТМ-6300/35), окна 09:00–17:00 -----------------------
    for ps, base_day in (("Рудничная", 4), ("Лесная", 6), ("Поселковая", 8)):
        for k, unit in enumerate(("Т-1", "Т-2")):
            days = [base_day + k, base_day + k + 7]
            a = asset(
                f"{ps}-{unit}",
                f"{ps} {unit}",
                f"ТМ-6300/35 {unit} ({ps})",
                "transformer_35",
                f"ПС-{ps}",
                Criticality.HIGH,
                0.15,
                0.6,
            )
            windows += _w(f"{ps}-{unit}", a.id, days, 9, 8)
            job(
                f"to35-{ps}-{unit}",
                f"ТО {unit} ({ps})",
                a,
                JobKind.PREVENTIVE,
                300,
                ["ps_110"],
                due_d=days[0] + 1,
                interruption=True,
                prio=40,
            )

    # --- ВЛ-110 «Северная—Заводская» и ВЛ-35 «Рудничная отпайка» --------------
    vl110 = asset(
        "VL110",
        "ВЛ-110 С-З",
        "ВЛ-110 Северная—Заводская (12 км)",
        "line_110",
        "Трасса-СЗ",
        Criticality.HIGH,
        0.12,
        0.8,
    )
    windows += _w("VL110", vl110.id, [6, 13], 7, 12)
    job(
        "bpla-vl110",
        "Облёт БПЛА ВЛ-110",
        vl110,
        JobKind.INSPECTION,
        120,
        ["vl_10"],
        due_d=7,
        interruption=False,
        prio=60,
    )
    job(
        "clear-vl110",
        "Расчистка просеки ВЛ-110",
        vl110,
        JobKind.PREVENTIVE,
        540,
        ["clearing"],
        due_d=7,
        interruption=True,
        prio=35,
    )

    vl35 = asset(
        "VL35",
        "ВЛ-35 Рудн.",
        "ВЛ-35 Рудничная отпайка (8 км)",
        "line_35",
        "Трасса-Р",
        Criticality.MEDIUM,
        0.14,
        0.5,
    )
    windows += _w("VL35", vl35.id, [7], 8, 10)
    job(
        "clear-vl35",
        "Расчистка просеки ВЛ-35",
        vl35,
        JobKind.PREVENTIVE,
        480,
        ["clearing"],
        due_d=8,
        interruption=True,
        prio=45,
    )

    # --- Фидеры ВЛ-10 кВ Ф-1..Ф-6, окна 08:00–17:00 ----------------------------
    for i in range(1, 7):
        a = asset(
            f"F{i}",
            f"Ф-{i}",
            f"ВЛ-10 кВ фидер Ф-{i}",
            "line_10",
            f"Фидер-{i}",
            Criticality.MEDIUM,
            0.2,
            0.4,
        )
        windows += _w(f"F{i}", a.id, [3 + i, 10 + i], 8, 9)
        job(
            f"izol-f{i}",
            f"Замена изоляторов Ф-{i}",
            a,
            JobKind.CORRECTIVE,
            480,
            ["vl_10"],
            due_d=4 + i,
            interruption=True,
            sp=[shf20],
            prio=30,
        )
        job(
            f"osm-f{i}",
            f"Осмотр Ф-{i} после грозы",
            a,
            JobKind.INSPECTION,
            120,
            ["vl_10"],
            due_d=6 + i,
            interruption=False,
            prio=70,
        )

    # --- ТП 10/0.4 кВ №1..12 (КТП-250..630): короткие окна = минимум недоотпуска
    # Окна ТП — во второй половине месяца, после крупных работ на ПС-110
    # (иначе ОВБ конкурируют за один день и цепочки вываливаются из окон).
    for i in range(1, 13):
        a = asset(
            f"TP{i}",
            f"ТП-{i:02d}",
            f"КТП-10/0.4 №{i}",
            "tp_10",
            f"ТП-зона-{(i - 1) // 4 + 1}",
            Criticality.MEDIUM if i % 4 else Criticality.HIGH,
            0.1,
            0.3,
        )
        first = 13 + (i % 9)
        windows += _w(f"TP{i}", a.id, [first, first + 7], 9, 4)
        job(
            f"to-tp{i}",
            f"ТО КТП №{i}",
            a,
            JobKind.PREVENTIVE,
            180,
            ["ps_10"],
            due_d=first + 1,
            interruption=True,
            prio=50,
        )

    # --- ВЛ-0.4 кВ участки У-1..У-5, окна 09:00–17:00 ---------------------------
    for i in range(1, 6):
        a = asset(
            f"U{i}",
            f"ВЛ-0.4 У-{i}",
            f"ВЛ-0.4 кВ участок У-{i}",
            "line_04",
            f"ТП-зона-{i}",
            Criticality.LOW,
            0.25,
            0.2,
        )
        windows += _w(f"U{i}", a.id, [4 + i, 14 + i], 9, 8)
        job(
            f"opor-u{i}",
            f"Ремонт опор У-{i}",
            a,
            JobKind.CORRECTIVE,
            420,
            ["vl_04"],
            due_d=5 + i,
            interruption=True,
            prio=55,
        )

    # --- Переезды между площадками (setup, мин) --------------------------------
    locs = {a.location_code for a in assets} | {"База РЭС"}
    travel: dict[str, int] = {}
    for x in locs:
        for y in locs:
            if x != y:
                travel[f"{x}|{y}"] = 45

    # network_constraints (explicit, NOT N-1): both ПС-110 heads must not be
    # under interruption at once — customer-declared anti-coincidence.
    t1_zav = next(a for a in assets if a.code == "Заводская Т-1")
    bans = [
        SimultaneousOutageBan(
            asset_id_a=t1_sev.id,
            asset_id_b=t1_zav.id,
            reason="оба Т-1 ПС-110 — без заявленного резерва по коридору",
            external_ref="BAN-PS110-T1",
            data_provenance="synthetic",
        )
    ]

    return GridPlanProblem(
        assets=assets,
        crews=crews,
        jobs=jobs,
        outage_windows=windows,
        spare_parts=spares,
        simultaneous_outage_bans=bans,
        travel_minutes=travel,
        planning_horizon_start=T0,
        planning_horizon_end=T0 + timedelta(days=HORIZON_DAYS),
        domain_attributes={
            "scenario": "РЭС «Северный» — месячный график ТОиР (сентябрь 2026)",
            "model_basis": "synthetic 110/35/10 kV district; durations from public СТО 34.01-24 "
            "and Minenergo order 1013; not a named DZO",
            "network_constraints": "explicit simultaneous_outage_bans only — not N-1",
            "data_provenance": "synthetic",
        },
    )


def _violations_ru(outcome) -> dict[str, int]:
    return ru_violation_counts(outcome)


def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def run() -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    problem = build_res_problem()

    # --- A: месячный график — FIFO vs GREED -----------------------------------
    fifo, t_fifo = _timed(
        lambda: plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    )
    greed, t_greed = _timed(
        lambda: plan_with_config(problem, solver_config="GREED", apply_frozen=False)
    )

    # --- B: замороженные заявки ПЛ; срыв работ → перепланирование
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
    # Гроза 12.09: бригады ВЛ переброшены на аварийку — сорваны облёт БПЛА и
    # осмотры фидеров; плюс сорвано ТО КТП №5 — работа С ОТКЛЮЧЕНИЕM в окне
    # заявки ПЛ (repair обязан вернуть её в согласованное окно; ранее —
    # upstream-дефект IncrementalRepair, исправлен в SynAPS: release_date
    # теперь жёсткая нижняя граница, регрессионный тест в upstream).
    disrupted_refs = ["Облёт БПЛА ВЛ-110", "ТО КТП №5"] + [
        f"Осмотр Ф-{i} после грозы" for i in range(1, 5)
    ]
    disrupted = [ref_to_job[r] for r in disrupted_refs if r in ref_to_job]
    job_by_id = {j.id: j for j in problem.jobs}
    windowed_disrupted = [
        job_by_id[jid] for jid in disrupted if job_by_id[jid].interruption_required
    ]
    repaired, t_repair = _timed(
        lambda: replan_after_disruption(
            problem_frozen, base_outcome=greed, disrupted_job_ids=disrupted
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

    # --- C: воспроизводимость ---------------------------------------------------
    greed2, _ = _timed(lambda: plan_with_config(problem, solver_config="GREED", apply_frozen=False))
    same_plan = [a.model_dump(mode="json") for a in greed.schedule.assignments] == [
        a.model_dump(mode="json") for a in greed2.schedule.assignments
    ]

    # --- D: CP-SAT vs GREED on makespan (OR-Tools dual bound) ------------------
    # OPTIMAL means the solver proved bound = objective on this instance.
    cpsat, t_cpsat = _timed(
        lambda: plan_with_config(problem, solver_config="CPSAT-30", apply_frozen=False)
    )
    cpsat2, _ = _timed(
        lambda: plan_with_config(problem, solver_config="CPSAT-30", apply_frozen=False)
    )
    cpsat_same = [a.model_dump(mode="json") for a in cpsat.schedule.assignments] == [
        a.model_dump(mode="json") for a in cpsat2.schedule.assignments
    ]
    go, co = greed.schedule.objective, cpsat.schedule.objective
    bound = cpsat.metadata.get("best_objective_bound")
    bound_units = cpsat.metadata.get("objective_bound_units")
    makespan_gap_pct = (
        round(100.0 * (go.makespan_minutes - float(bound)) / float(bound), 2)
        if bound and bound_units == "makespan_minutes" and float(bound) > 0
        else None
    )
    setup_delta_min = round(go.total_setup_minutes - co.total_setup_minutes)
    setup_ratio = (
        round(go.total_setup_minutes / co.total_setup_minutes, 2)
        if co.total_setup_minutes > 0
        else None
    )

    crit_assets = {
        a.id for a in problem.assets if a.criticality in (Criticality.HIGH, Criticality.CRITICAL)
    }
    crit_jobs = [j for j in problem.jobs if j.asset_id in crit_assets]
    served_crit = sum(
        1
        for j in crit_jobs
        if any(
            greed.id_map.get(f"job:{j.id}") == a.operation_id for a in greed.schedule.assignments
        )
    )

    results = {
        "benchmark": "gridplan.res-severny.v1",
        "claim_level": "experiment",
        "data_provenance": "synthetic (open-data-derived model)",
        "gridplan_version": GRIDPLAN_VERSION,
        "synaps_commit": SYNAPS_COMMIT,
        "instance": {
            "name": "РЭС «Северный» — месячный график ТОиР, сентябрь 2026",
            "assets": len(problem.assets),
            "jobs": len(problem.jobs),
            "crews": len(problem.crews),
            "outage_windows": len(problem.outage_windows),
            "horizon_days": HORIZON_DAYS,
            "input_hash": greed.metadata.get("input_hash"),
        },
        "scenario_a": {
            "fifo": {
                "status": fifo.status,
                "verified_feasible": fifo.verified_feasible,
                "assigned": len(fifo.schedule.assignments),
                "hard_violation_count": fifo.hard_violation_count,
                "violations_ru": _violations_ru(fifo),
                "wall_time_s": round(t_fifo, 3),
            },
            "greed": {
                "status": greed.status,
                "claim_status": greed.metadata.get("claim_status"),
                "verified_feasible": greed.verified_feasible,
                "assigned": len(greed.schedule.assignments),
                "hard_violation_count": greed.hard_violation_count,
                "violations_ru": _violations_ru(greed),
                "wall_time_s": round(t_greed, 3),
            },
            "critical_jobs_served": f"{served_crit}/{len(crit_jobs)}",
        },
        "scenario_b": {
            "frozen_pl_orders": len(frozen),
            "disrupted_jobs": [r for r in disrupted_refs if r in ref_to_job],
            "windowed_disrupted": [j.external_ref for j in windowed_disrupted],
            "windowed_repaired_in_window": bool(
                repaired.verified_feasible
                and repaired.hard_violation_count == 0
                and windowed_disrupted
            ),
            "repaired_status": repaired.status,
            "verified_feasible": repaired.verified_feasible,
            "hard_violation_count": repaired.hard_violation_count,
            "frozen_moved": frozen_moved,
            "churn": diff["churn"],
            "wall_time_s": round(t_repair, 3),
        },
        "scenario_c": {
            "two_runs_identical": same_plan,
            "plan_fingerprint": fingerprint_payload(
                [a.model_dump(mode="json") for a in greed.schedule.assignments]
            ),
        },
        "scenario_d": {
            "solver": "CPSAT-30 (OR-Tools CP-SAT, strict determinism)",
            "status": cpsat.status,
            "claim_status": cpsat.metadata.get("claim_status"),
            "verified_feasible": cpsat.verified_feasible,
            "determinism": cpsat.metadata.get("determinism"),
            "determinism_violated": cpsat.metadata.get("determinism_violated"),
            "two_runs_identical": cpsat_same,
            "wall_time_s": round(t_cpsat, 2),
            "makespan_min": {
                "greed": round(go.makespan_minutes),
                "cpsat": round(co.makespan_minutes),
                "dual_bound": bound,
                "greed_gap_pct": makespan_gap_pct,
            },
            "tardiness_min": {
                "greed": round(go.total_tardiness_minutes),
                "cpsat": round(co.total_tardiness_minutes),
            },
            "setup_min": {
                "greed": round(go.total_setup_minutes),
                "cpsat": round(co.total_setup_minutes),
                "delta": setup_delta_min,
                "greed_ratio": setup_ratio,
            },
        },
    }
    (RESULTS / "res_severny_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (RESULTS / "res_severny_report.md").write_text(_render_md(results), encoding="utf-8")
    return results


def _ok(verified: bool, hard_count: int) -> bool:
    return bool(verified) and int(hard_count) == 0


def _render_md(r: dict) -> str:
    a, b, c, d = r["scenario_a"], r["scenario_b"], r["scenario_c"], r["scenario_d"]
    fifo_v = a["fifo"]["violations_ru"]
    greed_v = a["greed"]["violations_ru"]
    fifo_n = int(a["fifo"].get("hard_violation_count", sum(fifo_v.values())))
    greed_n = int(a["greed"].get("hard_violation_count", sum(greed_v.values())))
    fifo_ok = _ok(a["fifo"].get("verified_feasible"), fifo_n)
    greed_ok = _ok(a["greed"].get("verified_feasible"), greed_n)
    repair_ok = _ok(b.get("verified_feasible"), int(b.get("hard_violation_count", 0)))
    fifo_rows = "\n".join(f"| {k} | {v} |" for k, v in fifo_v.items()) or "| — | 0 |"
    greed_rows = "\n".join(f"| {k} | {v} |" for k, v in greed_v.items()) or "| — | 0 |"
    inst = r["instance"]
    proven = d["status"] == "optimal"
    gap = d["makespan_min"]["greed_gap_pct"]
    gap_line = (
        f"доказанный оптимум (разрыв эвристики по горизонту: {gap}%)"
        if proven and gap is not None
        else (f"не доказан за лимит; нижняя граница {d['makespan_min']['dual_bound']} мин")
    )
    repair_mark = "да" if repair_ok else f"нет ({b['repaired_status']})"
    window_mark = "да" if b.get("windowed_repaired_in_window") else "нет"
    same_mark = "да" if c["two_runs_identical"] else "нет"
    cpsat_mark = "доказан" if proven else "лимит времени"
    cpsat_det = "да" if d["two_runs_identical"] and not d["determinism_violated"] else "нет"
    return f"""# Демо: РЭС «Северный» — месячный график ТОиР

Синтетическая схема 110/35/10 кВ и типовые нормы длительностей (СТО 34.01-24,
приказ Минэнерго №1013, профстандарт 20.032). Это не данные ПАО «Россети»
и не пилот. GREED/FIFO — `heuristic_feasible`.

**Участок:** 2 ПС 110/10 кВ, 3 ПС 35/10 кВ, ВЛ-110 и ВЛ-35, 6 фидеров 10 кВ,
12 КТП 10/0.4, 5 участков ВЛ-0.4 кВ.
**Работы:** {inst["jobs"]}. **Ресурсы:** {inst["crews"]} бригад, склад ЗИП,
{inst["outage_windows"]} окон отключений (заявки ПЛ). **Горизонт:** сентябрь 2026.

## Сценарий A. Месячный график: календарный FIFO и GREED

| Показатель | FIFO | GREED |
| --- | --- | --- |
| Работ назначено | {a["fifo"]["assigned"]} / {inst["jobs"]} | {a["greed"]["assigned"]} / {inst["jobs"]} |
| Жёстких нарушений | **{fifo_n}** | **{greed_n}** |
| Проверка | {"да" if fifo_ok else "нет"} | {"да" if greed_ok else "нет"} |
| Работы на критических активах | — | {a["critical_jobs_served"]} |
| Время расчёта, с | {a["fifo"]["wall_time_s"]} | {a["greed"]["wall_time_s"]} |

Расшифровка — сумма слоёв проверки (правила GridPlan и движок SynAPS).

**FIFO:**

| Нарушение | Сколько |
| --- | ---: |
{fifo_rows}

**GREED:**

| Нарушение | Сколько |
| --- | ---: |
{greed_rows}

Ручное правило ставит работы вне окон и ломает последовательность.
GREED на этой синтетике собирает график без жёстких нарушений, если строка
«Проверка» — «да». Оптимальность GREED не утверждается (сценарий D).

## Сценарий B. Срыв работ при замороженных заявках ПЛ

Две заявки ПЛ на ПС-110 заморожены. Срываются облёт БПЛА, осмотры фидеров
и ТО КТП №5 (работа с отключением в окне ПЛ).

| Показатель | Значение |
| --- | --- |
| Заявок ПЛ сдвинуто | **{b["frozen_moved"]}** |
| План восстановлен | {repair_mark} |
| Оконная работа вернулась в окно | {window_mark} |
| Слотов изменено (из {len(b["disrupted_jobs"])} сорванных) | {b["churn"]["moved"] + b["churn"]["added"] + b["churn"]["removed"]} |
| Время, с | {b["wall_time_s"]} |

На этом прогоне замороженные заявки не сдвинуты, если «Заявок ПЛ сдвинуто» = 0.
Это синтетика.

## Сценарий C. Воспроизводимость

| Проверка | Результат |
| --- | --- |
| Два запуска GREED совпали | {same_mark} |
| Отпечаток плана (SHA-256) | `{c["plan_fingerprint"][:16]}…` |

## Сценарий D. CP-SAT (OR-Tools) на том же инстансе

Статус `optimal` означает: нижняя граница совпала с достигнутым makespan
**на этой постановке**. Это свойство решателя, не сертификат продукта.

| Показатель | GREED | CP-SAT |
| --- | --- | --- |
| Статус | `{a["greed"]["claim_status"]}` | **`{d["status"]}`** ({cpsat_mark}) |
| Горизонт плана, мин | {d["makespan_min"]["greed"]} | {d["makespan_min"]["cpsat"]} |
| Нижняя граница, мин | — | {d["makespan_min"]["dual_bound"]} |
| Просрочки, мин | {d["tardiness_min"]["greed"]} | {d["tardiness_min"]["cpsat"]} |
| Переезды бригад, мин | {d["setup_min"]["greed"]} | {d["setup_min"]["cpsat"]} |
| Время, с | {a["greed"]["wall_time_s"]} | {d["wall_time_s"]} |
| Два запуска CP-SAT совпали | — | {cpsat_det} |

Горизонт: {gap_line}. Совпадение GREED с доказанным makespan на одном
инстансе не переносится на другие цели и размеры. Переезды — вторичный
критерий ({d["setup_min"]["greed"]} vs {d["setup_min"]["cpsat"]} мин).

## Границы

- Синтетика. Эффект на данных заказчика — отдельный пилот.
- Оптимум CP-SAT — только этот инстанс и критерий makespan.
- Риск в продукте — справочный, не модель отказов.
- Repair пересобирает план от начала горизонта (нет якоря «сейчас»).

_Версии: gridplan {r["gridplan_version"]}, SynAPS `{r["synaps_commit"][:12]}`._
"""


if __name__ == "__main__":
    out = run()
    a, d = out["scenario_a"], out["scenario_d"]
    print(
        json.dumps(
            {
                "fifo_violations": sum(a["fifo"]["violations_ru"].values()),
                "greed_violations": sum(a["greed"]["violations_ru"].values()),
                "critical_served": a["critical_jobs_served"],
                "frozen_moved": out["scenario_b"]["frozen_moved"],
                "repaired": out["scenario_b"]["repaired_status"],
                "windowed_repaired": out["scenario_b"]["windowed_repaired_in_window"],
                "deterministic": out["scenario_c"]["two_runs_identical"],
                "cpsat_status": d["status"],
                "cpsat_makespan_bound": d["makespan_min"]["dual_bound"],
                "greed_makespan_gap_pct": d["makespan_min"]["greed_gap_pct"],
                "setup_greed_vs_cpsat": [
                    d["setup_min"]["greed"],
                    d["setup_min"]["cpsat"],
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
