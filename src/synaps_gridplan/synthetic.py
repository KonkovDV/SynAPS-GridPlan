"""Synthetic feeder instance generator (explicitly labelled synthetic)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from synaps_gridplan.fingerprint import stable_int
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

_NS = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _uid(seed: int, *parts: str) -> UUID:
    return uuid5(_NS, f"synaps-gridplan:{seed}:" + ":".join(parts))


def synthesize_feeder(
    *,
    n_assets: int = 40,
    n_jobs: int = 200,
    n_crews: int = 10,
    seed: int = 42,
    horizon_days: int = 30,
    mode: str = "medium",
) -> GridPlanProblem:
    """Build a synthetic radial feeder maintenance problem.

    Data provenance: **synthetic**. Not customer data. Not a pilot.
    Fully deterministic for a fixed ``seed`` (stable digests, uuid5 ids).
    """

    presets = {
        "small": (12, 30, 4, 14),
        "medium": (n_assets, n_jobs, n_crews, horizon_days),
        "stress": (80, 600, 15, 45),
        "disruption": (40, 200, 10, 30),
        "infeasible": (8, 40, 1, 7),
        "frozen-conflict": (10, 24, 3, 14),
    }
    if mode not in presets:
        raise ValueError(f"unknown mode: {mode}")
    if mode != "medium":
        n_assets, n_jobs, n_crews, horizon_days = presets[mode]

    if n_assets < 1 or n_jobs < 1 or n_crews < 1:
        raise ValueError("assets, jobs, and crews must be >= 1")

    rng = _Lcg(seed)
    start = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)
    end = start + timedelta(days=horizon_days)

    skills = ["electro", "relay", "line", "switchgear"]
    crews: list[Crew] = []
    for i in range(n_crews):
        q = [skills[i % len(skills)], skills[(i + 1) % len(skills)]]
        crews.append(
            Crew(
                id=_uid(seed, "crew", str(i)),
                code=f"CREW-{i + 1:02d}",
                qualifications=q,
                max_parallel=1 if mode != "infeasible" else 1,
                home_location_code=f"DEPOT-{(i % 3) + 1}",
                data_provenance="synthetic",
            )
        )

    criticalities = [
        Criticality.LOW,
        Criticality.MEDIUM,
        Criticality.HIGH,
        Criticality.CRITICAL,
    ]
    assets: list[Asset] = []
    for i in range(n_assets):
        crit = criticalities[i % len(criticalities)]
        pof = 0.05 + (rng.next() % 60) / 100.0 * 0.5
        cons = 0.2 + (rng.next() % 80) / 100.0 * 0.8
        assets.append(
            Asset(
                id=_uid(seed, "asset", str(i)),
                code=f"EQ-{i + 1:03d}",
                name=f"Asset {i + 1}",
                asset_class="switchgear" if i % 3 == 0 else "line",
                location_code=f"LOC-{(i % 12) + 1}",
                risk=RiskProfile(
                    probability_of_failure=min(1.0, pof),
                    consequence_score=min(1.0, cons),
                    criticality=crit,
                    is_advisory=True,
                    assessment_method="synthetic_proxy",
                ),
                data_provenance="synthetic",
            )
        )

    spare_stock = {
        "small": (6, 4, 2),
        "medium": (20, 15, 8),
        "stress": (30, 20, 12),
        "disruption": (20, 15, 8),
        "infeasible": (0, 0, 0),
        "frozen-conflict": (10, 8, 4),
    }[mode]
    spares = [
        SparePart(
            id=_uid(seed, "spare", "contact"),
            code="SP-CONTACT",
            stock_qty=spare_stock[0],
            available_quantity=spare_stock[0],
            data_provenance="synthetic",
        ),
        SparePart(
            id=_uid(seed, "spare", "insulator"),
            code="SP-INSULATOR",
            stock_qty=spare_stock[1],
            available_quantity=spare_stock[1],
            data_provenance="synthetic",
        ),
        SparePart(
            id=_uid(seed, "spare", "relay"),
            code="SP-RELAY",
            stock_qty=spare_stock[2],
            available_quantity=spare_stock[2],
            data_provenance="synthetic",
        ),
    ]

    outages: list[OutageWindow] = []
    for i, asset in enumerate(assets[: max(1, n_assets // 5)]):
        w_start = start + timedelta(days=2 + i)
        outages.append(
            OutageWindow(
                id=_uid(seed, "outage", str(i)),
                asset_id=asset.id,
                start=w_start,
                end=w_start + timedelta(hours=10),
                frozen=(i % 3 == 0),
                approved=True,
                external_ref=f"OUT-{i + 1:03d}",
                data_provenance="synthetic",
            )
        )
    assets_with_outage = {w.asset_id for w in outages}

    jobs: list[MaintenanceJob] = []
    kinds = [JobKind.PREVENTIVE, JobKind.INSPECTION, JobKind.CORRECTIVE]
    for i in range(n_jobs):
        asset = assets[i % n_assets]
        kind = kinds[i % len(kinds)]
        skill = skills[i % len(skills)]
        duration = 60 + (rng.next() % 8) * 30
        due = start + timedelta(days=1 + (rng.next() % max(1, horizon_days - 1)))
        # Only require interruption when an approved window exists for the asset.
        needs_outage = asset.id in assets_with_outage and (
            asset.asset_class == "switchgear" or kind == JobKind.CORRECTIVE
        )
        # Keep duration inside typical 10h window when interruption is required.
        if needs_outage:
            duration = min(duration, 240)
        jobs.append(
            MaintenanceJob(
                id=_uid(seed, "job", str(i)),
                external_ref=f"WO-{i + 1:04d}",
                asset_id=asset.id,
                kind=kind,
                duration_min=duration,
                required_qualifications=[skill],
                spare_part_ids=[spares[i % len(spares)].id] if i % 4 == 0 else [],
                due_date=due,
                release_date=start,
                interruption_required=needs_outage,
                data_provenance="synthetic",
            )
        )

    for i in range(0, min(n_jobs - 1, 40), 5):
        jobs[i + 1] = jobs[i + 1].model_copy(update={"predecessor_job_ids": [jobs[i].id]})

    travel: dict[str, int] = {}
    locations = sorted({a.location_code for a in assets} | {c.home_location_code for c in crews})
    for a in locations:
        for b in locations:
            if a == b:
                travel[f"{a}|{b}"] = 0
            else:
                travel[f"{a}|{b}"] = 15 + stable_int(str(seed), a, b, modulo=45)

    frozen_rows: list[FrozenAssignment] = []
    if mode == "infeasible":
        # Force interruption jobs with zero usable stock and tiny horizon pressure.
        for i, job in enumerate(jobs[: min(8, len(jobs))]):
            jobs[i] = job.model_copy(
                update={
                    "interruption_required": True,
                    "spare_part_ids": [spares[0].id],
                    "duration_min": max(job.duration_min, 360),
                    "required_qualifications": ["electro", "relay", "line"],
                }
            )
        # No approved windows → OUTAGE_WINDOW_MISSING after any schedule attempt.
        outages = []
        spares = [
            s.model_copy(update={"available_quantity": 0, "stock_qty": 0, "reserved_quantity": 0})
            for s in spares
        ]

    if mode == "frozen-conflict":
        # Plant an immutable frozen row that cannot fit (end beyond horizon).
        job = jobs[0]
        crew = crews[0]
        frozen_rows.append(
            FrozenAssignment(
                job_id=job.id,
                crew_id=crew.id,
                start=end - timedelta(minutes=30),
                end=end + timedelta(hours=6),
                source="synthetic_conflict",
                frozen_reason="forced_horizon_overflow",
                immutable=True,
                data_provenance="synthetic",
            )
        )

    return GridPlanProblem(
        schema_version="gridplan.v1",
        assets=assets,
        crews=crews,
        jobs=jobs,
        outage_windows=outages,
        spare_parts=spares,
        frozen_assignments=frozen_rows,
        travel_minutes=travel,
        planning_horizon_start=start,
        planning_horizon_end=end,
        domain_attributes={
            "data_provenance": "synthetic",
            "generator": "synthesize_feeder",
            "generator_mode": mode,
            "seed": seed,
            "claim_level": "experiment",
            "iso16290_trl": 4,
        },
    )


class _Lcg:
    """Tiny deterministic LCG — no numpy dependency in the generator path."""

    def __init__(self, seed: int) -> None:
        self._state = seed & 0xFFFFFFFF

    def next(self) -> int:
        self._state = (1664525 * self._state + 1013904223) & 0xFFFFFFFF
        return self._state
