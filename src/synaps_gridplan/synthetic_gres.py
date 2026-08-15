"""Synthetic GRES-block (generation-shaped). Not a named station dump."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from synaps_gridplan.synthetic import _uid

_T0 = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)
_HORIZON_DAYS = 30


def _asset(seed: int, tag: str, code: str, name: str, klass: str, loc: str) -> Asset:
    return Asset(
        id=_uid(seed, "gres-asset", tag),
        code=code,
        name=name,
        asset_class=klass,
        location_code=loc,
        risk=RiskProfile(
            probability_of_failure=0.12,
            consequence_score=0.8 if klass == "gtu" else 0.4,
            criticality=Criticality.CRITICAL if klass == "gtu" else Criticality.MEDIUM,
            is_advisory=True,
            assessment_method="synthetic_proxy",
        ),
        data_provenance="synthetic",
        domain_attributes={"site": "GRES-block-synthetic"},
    )


def _crew(seed: int, tag: str, code: str, quals: list[str], loc: str) -> Crew:
    return Crew(
        id=_uid(seed, "gres-crew", tag),
        code=code,
        qualifications=quals,
        home_location_code=loc,
        data_provenance="synthetic",
    )


def _window(seed: int, tag: str, asset_id, day: int, hours: int = 14) -> OutageWindow:
    start = _T0 + timedelta(days=day, hours=1)
    return OutageWindow(
        id=_uid(seed, "gres-window", tag),
        asset_id=asset_id,
        start=start,
        end=start + timedelta(hours=hours),
        approved=True,
        external_ref=f"ПЛ-{tag}",
        data_provenance="synthetic",
    )


def _job(
    seed: int,
    tag: str,
    ref: str,
    asset: Asset,
    *,
    kind: JobKind,
    duration_min: int,
    quals: list[str],
    due_day: int,
    interruption: bool,
    preds: list[MaintenanceJob] | None = None,
    spares: list[SparePart] | None = None,
    priority: int = 50,
) -> MaintenanceJob:
    return MaintenanceJob(
        id=_uid(seed, "gres-job", tag),
        external_ref=ref,
        asset_id=asset.id,
        kind=kind,
        duration_min=duration_min,
        required_qualifications=quals,
        spare_part_ids=[part.id for part in spares or []],
        predecessor_job_ids=[pred.id for pred in preds or []],
        due_date=_T0 + timedelta(days=due_day),
        release_date=_T0,
        priority=priority,
        interruption_required=interruption,
        data_provenance="synthetic",
    )


def _gtu_outage_chain(
    seed: int,
    tag: str,
    unit: Asset,
    day: int,
    blade: SparePart,
) -> tuple[list[MaintenanceJob], OutageWindow]:
    iso = _job(
        seed,
        f"{tag}-iso",
        f"Изоляция {unit.code}",
        unit,
        kind=JobKind.PREVENTIVE,
        duration_min=120,
        quals=["electro"],
        due_day=day + 1,
        interruption=True,
        priority=10,
    )
    repair = _job(
        seed,
        f"{tag}-rep",
        f"Ремонт {unit.code}",
        unit,
        kind=JobKind.CORRECTIVE,
        duration_min=480,
        quals=["mechanical"],
        due_day=day + 1,
        interruption=True,
        preds=[iso],
        spares=[blade],
        priority=15,
    )
    test = _job(
        seed,
        f"{tag}-tst",
        f"Испытания {unit.code}",
        unit,
        kind=JobKind.INSPECTION,
        duration_min=180,
        quals=["instrument"],
        due_day=day + 1,
        interruption=True,
        preds=[repair],
        priority=20,
    )
    return [iso, repair, test], _window(seed, tag, unit.id, day)


def _gres_travel() -> dict[str, int]:
    locs = ("Турбинный", "БЩУ", "ОРУ-110")
    return {
        f"{a}|{b}": 0 if a == b else (20 if "ОРУ" not in a + b else 40) for a in locs for b in locs
    }


def synthesize_gres_block(*, seed: int = 42) -> GridPlanProblem:
    """One synthetic GRES block: two GTU chains, BOP, switchyard. Experiment only."""

    end = _T0 + timedelta(days=_HORIZON_DAYS)
    gtu1 = _asset(seed, "gtu1", "GTU-1", "ГТУ-1 (synthetic)", "gtu", "Турбинный")
    gtu2 = _asset(seed, "gtu2", "GTU-2", "ГТУ-2 (synthetic)", "gtu", "Турбинный")
    bop = _asset(seed, "bop", "BOP-FWP", "ПЭН (synthetic)", "bop", "БЩУ")
    swyd = _asset(seed, "swyd", "SWYD-110", "В-110 (synthetic)", "switchyard", "ОРУ-110")
    electro = _crew(seed, "eto", "ЭТО-1", ["electro"], "Турбинный")
    mech = _crew(seed, "mech", "МЕХ-1", ["mechanical"], "Турбинный")
    kip = _crew(seed, "kip", "КИПиА-1", ["instrument"], "БЩУ")
    electro2 = _crew(seed, "eto2", "ЭТО-2", ["electro"], "ОРУ-110")
    blade = SparePart(
        id=_uid(seed, "gres-spare", "blade"),
        code="ЛОПАТКА-ГТУ",
        available_quantity=2,
        warehouse_location="Склад блока",
        data_provenance="synthetic",
    )
    jobs: list[MaintenanceJob] = []
    windows: list[OutageWindow] = []
    for tag, unit, day in (("gtu1", gtu1, 2), ("gtu2", gtu2, 10)):
        chain, window = _gtu_outage_chain(seed, tag, unit, day, blade)
        jobs.extend(chain)
        windows.append(window)
    windows.append(_window(seed, "swyd", swyd.id, 18, hours=8))
    jobs.append(
        _job(
            seed,
            "swyd-to",
            "ТО В-110",
            swyd,
            kind=JobKind.PREVENTIVE,
            duration_min=180,
            quals=["electro"],
            due_day=19,
            interruption=True,
            priority=40,
        )
    )
    jobs.append(
        _job(
            seed,
            "bop-to",
            "ТО ПЭН",
            bop,
            kind=JobKind.PREVENTIVE,
            duration_min=240,
            quals=["mechanical"],
            due_day=8,
            interruption=False,
            priority=60,
        )
    )
    jobs.append(
        _job(
            seed,
            "bop-em",
            "Срочная дефектация ПЭН",
            bop,
            kind=JobKind.EMERGENCY,
            duration_min=90,
            quals=["mechanical"],
            due_day=3,
            interruption=False,
            priority=5,
        )
    )
    return GridPlanProblem(
        schema_version="gridplan.v1",
        assets=[gtu1, gtu2, bop, swyd],
        crews=[electro, mech, kip, electro2],
        jobs=jobs,
        outage_windows=windows,
        spare_parts=[blade],
        simultaneous_outage_bans=[
            SimultaneousOutageBan(
                id=_uid(seed, "gres-ban", "gtu-pair"),
                asset_id_a=gtu1.id,
                asset_id_b=gtu2.id,
                reason="explicit dual-GTU outage ban (not N-1)",
                data_provenance="synthetic",
            )
        ],
        travel_minutes=_gres_travel(),
        planning_horizon_start=_T0,
        planning_horizon_end=end,
        domain_attributes={
            "data_provenance": "synthetic",
            "generator": "synthesize_gres_block",
            "seed": seed,
            "claim_level": "experiment",
            "iso16290_trl": 4,
            "not_live_el5": True,
        },
    )
