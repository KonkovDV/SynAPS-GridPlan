"""Synthetic dual-utility hall. Not MMTS-9, not a named cloud campus."""

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
    critical = klass in {"feeder", "ups"}
    return Asset(
        id=_uid(seed, "hall-asset", tag),
        code=code,
        name=name,
        asset_class=klass,
        location_code=loc,
        risk=RiskProfile(
            probability_of_failure=0.1,
            consequence_score=0.85 if critical else 0.4,
            criticality=Criticality.CRITICAL if critical else Criticality.MEDIUM,
            is_advisory=True,
            assessment_method="synthetic_proxy",
        ),
        data_provenance="synthetic",
        domain_attributes={"site": "Zarechny-hall-synthetic"},
    )


def _crew(seed: int, tag: str, code: str, quals: list[str], loc: str) -> Crew:
    return Crew(
        id=_uid(seed, "hall-crew", tag),
        code=code,
        qualifications=quals,
        home_location_code=loc,
        data_provenance="synthetic",
    )


def _window(seed: int, tag: str, asset_id, day: int, hours: int = 14) -> OutageWindow:
    start = _T0 + timedelta(days=day, hours=1)
    return OutageWindow(
        id=_uid(seed, "hall-window", tag),
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
        id=_uid(seed, "hall-job", tag),
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


def _feeder_outage_chain(
    seed: int,
    tag: str,
    feeder: Asset,
    day: int,
    cell: SparePart,
) -> tuple[list[MaintenanceJob], OutageWindow]:
    iso = _job(
        seed,
        f"{tag}-iso",
        f"Изоляция {feeder.code}",
        feeder,
        kind=JobKind.PREVENTIVE,
        duration_min=90,
        quals=["electro"],
        due_day=day + 1,
        interruption=True,
        priority=10,
    )
    repair = _job(
        seed,
        f"{tag}-rep",
        f"Ремонт {feeder.code}",
        feeder,
        kind=JobKind.CORRECTIVE,
        duration_min=240,
        quals=["electro"],
        due_day=day + 1,
        interruption=True,
        preds=[iso],
        spares=[cell],
        priority=15,
    )
    restore = _job(
        seed,
        f"{tag}-rst",
        f"Включение {feeder.code}",
        feeder,
        kind=JobKind.INSPECTION,
        duration_min=90,
        quals=["electro"],
        due_day=day + 1,
        interruption=True,
        preds=[repair],
        priority=20,
    )
    return [iso, repair, restore], _window(seed, tag, feeder.id, day)


def _hall_travel() -> dict[str, int]:
    locs = ("Ввод-A", "Ввод-B", "Машзал", "РУ-10")
    return {f"{a}|{b}": 0 if a == b else 15 for a in locs for b in locs}


def synthesize_dual_feed_hall(*, seed: int = 42) -> GridPlanProblem:
    """Two utility paths into a hall. Explicit mutex, not N-1, not a live IX."""

    end = _T0 + timedelta(days=_HORIZON_DAYS)
    feed_a = _asset(seed, "fa", "FEED-A", "Ввод 10 кВ A (synthetic)", "feeder", "Ввод-A")
    feed_b = _asset(seed, "fb", "FEED-B", "Ввод 10 кВ B (synthetic)", "feeder", "Ввод-B")
    ups = _asset(seed, "ups", "HALL-UPS", "ИБП/ДГУ зала (synthetic)", "ups", "Машзал")
    bus = _asset(seed, "bus", "BUS-10", "РУ-10 зала (synthetic)", "switchgear", "РУ-10")
    eto_a = _crew(seed, "eto-a", "ЭТО-A", ["electro"], "Ввод-A")
    eto_b = _crew(seed, "eto-b", "ЭТО-B", ["electro"], "Ввод-B")
    diesel = _crew(seed, "dgu", "ДГУ-1", ["diesel"], "Машзал")
    rel = _crew(seed, "rel", "РЗА-1", ["relay"], "РУ-10")
    cell = SparePart(
        id=_uid(seed, "hall-spare", "cell"),
        code="ЯЧЕЙКА-ВВ",
        available_quantity=2,
        warehouse_location="Склад зала",
        data_provenance="synthetic",
    )
    jobs: list[MaintenanceJob] = []
    windows: list[OutageWindow] = []
    for tag, feeder, day in (("fa", feed_a, 2), ("fb", feed_b, 12)):
        chain, window = _feeder_outage_chain(seed, tag, feeder, day, cell)
        jobs.extend(chain)
        windows.append(window)
    windows.append(_window(seed, "bus", bus.id, 20, hours=8))
    jobs.append(
        _job(
            seed,
            "bus-to",
            "ТО РУ-10",
            bus,
            kind=JobKind.PREVENTIVE,
            duration_min=180,
            quals=["relay"],
            due_day=21,
            interruption=True,
            priority=40,
        )
    )
    jobs.append(
        _job(
            seed,
            "dgu-test",
            "Прогон ДГУ (без отключения вводов)",
            ups,
            kind=JobKind.INSPECTION,
            duration_min=120,
            quals=["diesel"],
            due_day=5,
            interruption=False,
            priority=30,
        )
    )
    return GridPlanProblem(
        schema_version="gridplan.v1",
        assets=[feed_a, feed_b, ups, bus],
        crews=[eto_a, eto_b, diesel, rel],
        jobs=jobs,
        outage_windows=windows,
        spare_parts=[cell],
        simultaneous_outage_bans=[
            SimultaneousOutageBan(
                id=_uid(seed, "hall-ban", "feed-pair"),
                asset_id_a=feed_a.id,
                asset_id_b=feed_b.id,
                reason=(
                    "explicit dual-feed outage ban (concurrent maintainability "
                    "analogue, not N-1, not M9)"
                ),
                data_provenance="synthetic",
            )
        ],
        travel_minutes=_hall_travel(),
        planning_horizon_start=_T0,
        planning_horizon_end=end,
        domain_attributes={
            "data_provenance": "synthetic",
            "generator": "synthesize_dual_feed_hall",
            "seed": seed,
            "claim_level": "experiment",
            "iso16290_trl": 4,
            "not_live_m9": True,
            "not_live_el5": True,
        },
    )
