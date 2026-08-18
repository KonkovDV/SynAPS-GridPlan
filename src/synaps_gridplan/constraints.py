"""GridPlan post-checks — domain constraints SynAPS does not fully encode."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from synaps.model import Assignment, ScheduleProblem, ScheduleResult

from synaps_gridplan.model import FrozenAssignment, GridPlanProblem, MaintenanceJob


@dataclass(frozen=True)
class ConstraintViolation:
    kind: str
    message: str
    job_id: UUID | None = None
    details: dict[str, Any] | None = None


def check_gridplan_constraints(
    problem: GridPlanProblem,
    *,
    schedule_problem: ScheduleProblem,
    result: ScheduleResult,
    id_map: dict[str, UUID],
    expected_frozen: list[FrozenAssignment] | None = None,
) -> list[ConstraintViolation]:
    """Return hard GridPlan-domain violations (fail-closed callers must escalate)."""

    violations: list[ConstraintViolation] = []
    jobs_by_id = {j.id: j for j in problem.jobs}
    crews_by_id = {c.id: c for c in problem.crews}
    assets_by_id = {a.id: a for a in problem.assets}
    spares_by_id = {s.id: s for s in problem.spare_parts}
    op_to_job = {id_map[f"job:{j.id}"]: j.id for j in problem.jobs if f"job:{j.id}" in id_map}
    crew_of_wc = {id_map[f"crew:{c.id}"]: c.id for c in problem.crews if f"crew:{c.id}" in id_map}

    for asn in result.assignments:
        job_id = op_to_job.get(asn.operation_id)
        if job_id is None:
            violations.append(
                ConstraintViolation(
                    kind="UNKNOWN_OPERATION",
                    message="assignment references an operation that is not a GridPlan job",
                    details={"operation_id": str(asn.operation_id)},
                )
            )
            continue
        job = jobs_by_id[job_id]
        crew_id = crew_of_wc.get(asn.work_center_id)
        if crew_id is None:
            violations.append(
                ConstraintViolation(
                    kind="UNKNOWN_CREW",
                    message=f"assignment for job {job.external_ref} maps to unknown crew",
                    job_id=job_id,
                )
            )
            continue
        crew = crews_by_id[crew_id]
        required = set(job.required_qualifications)
        if required and not required.issubset(set(crew.qualifications)):
            violations.append(
                ConstraintViolation(
                    kind="QUALIFICATION_MISMATCH",
                    message=(
                        f"job {job.external_ref} requires {sorted(required)} "
                        f"but crew {crew.code} has {sorted(crew.qualifications)}"
                    ),
                    job_id=job_id,
                )
            )
        if job.eligible_crew_ids and crew_id not in job.eligible_crew_ids:
            violations.append(
                ConstraintViolation(
                    kind="ELIGIBLE_CREW_MISMATCH",
                    message=(
                        f"job {job.external_ref} assigned to crew {crew.code} "
                        "outside eligible_crew_ids"
                    ),
                    job_id=job_id,
                )
            )
        violations.extend(
            _catalog_field_violations(
                job=job,
                crew=crew,
                asset=assets_by_id.get(job.asset_id),
                start=asn.start_time,
                end=asn.end_time,
            )
        )
        if job.release_date is not None and asn.start_time < job.release_date:
            violations.append(
                ConstraintViolation(
                    kind="RELEASE_DATE_VIOLATION",
                    message=(
                        f"job {job.external_ref} starts {asn.start_time.isoformat()} "
                        f"before release_date {job.release_date.isoformat()}"
                    ),
                    job_id=job_id,
                )
            )

        if (
            asn.start_time < problem.planning_horizon_start
            or asn.end_time > problem.planning_horizon_end
        ):
            violations.append(
                ConstraintViolation(
                    kind="HORIZON_VIOLATION",
                    message=f"job {job.external_ref} assignment outside planning horizon",
                    job_id=job_id,
                )
            )

        if asn.end_time <= asn.start_time or job.duration_min < 1:
            violations.append(
                ConstraintViolation(
                    kind="INVALID_DURATION",
                    message=f"job {job.external_ref} has non-positive scheduled duration",
                    job_id=job_id,
                )
            )
        elif int((asn.end_time - asn.start_time).total_seconds() // 60) < job.duration_min:
            violations.append(
                ConstraintViolation(
                    kind="SHORT_DURATION",
                    message=(
                        f"job {job.external_ref} scheduled shorter than duration_min="
                        f"{job.duration_min}"
                    ),
                    job_id=job_id,
                )
            )

        violations.extend(_outage_violations(problem, job, asn.start_time, asn.end_time))

        if job.latest_finish is not None and asn.end_time > job.latest_finish:
            violations.append(
                ConstraintViolation(
                    kind="LATEST_FINISH_VIOLATION",
                    message=(
                        f"job {job.external_ref} ends {asn.end_time.isoformat()} "
                        f"after latest_finish {job.latest_finish.isoformat()}"
                    ),
                    job_id=job_id,
                )
            )

    violations.extend(_precedence_violations(problem, result, id_map, op_to_job))
    violations.extend(_spare_violations(problem, result, id_map, op_to_job, spares_by_id))
    violations.extend(_asset_overlap_violations(result, op_to_job, jobs_by_id))
    violations.extend(
        _crew_overlap_violations(result, crews_by_id, crew_of_wc, op_to_job, jobs_by_id)
    )
    violations.extend(_simultaneous_outage_ban_violations(problem, result, op_to_job, jobs_by_id))

    frozen = expected_frozen if expected_frozen is not None else list(problem.frozen_assignments)
    violations.extend(_frozen_violations(frozen, result, id_map, op_to_job, crew_of_wc, jobs_by_id))

    # Completeness: a dropped job must not yield verified_feasible.
    all_op_ids = [id_map[f"job:{j.id}"] for j in problem.jobs if f"job:{j.id}" in id_map]
    assigned_op_ids = [a.operation_id for a in result.assignments]
    seen_ops: set[UUID] = set()
    for op_id in assigned_op_ids:
        if op_id in seen_ops and op_id in set(all_op_ids):
            violations.append(
                ConstraintViolation(
                    kind="DUPLICATE_ASSIGNMENT",
                    message="operation scheduled more than once",
                    details={"operation_id": str(op_id)},
                )
            )
        seen_ops.add(op_id)
    for job in problem.jobs:
        op_id = id_map.get(f"job:{job.id}")
        if op_id is not None and op_id not in seen_ops:
            violations.append(
                ConstraintViolation(
                    kind="UNSCHEDULED_JOB",
                    message=(
                        f"job {job.external_ref} has no assignment — solver dropped it "
                        "(no eligible crew / no fitting window / solver limitation)"
                    ),
                    job_id=job.id,
                )
            )

    return violations


def _parse_calendar_instant(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _calendar_covers(rows: list[dict[str, Any]], start: datetime, end: datetime) -> str | None:
    """None = covered or unconstrained. Kind suffix when violated/malformed."""
    if not rows:
        return None
    parsed: list[tuple[datetime, datetime]] = []
    for row in rows:
        window_start = _parse_calendar_instant(row.get("start"))
        window_end = _parse_calendar_instant(row.get("end"))
        if window_start is None or window_end is None or window_end <= window_start:
            return "MALFORMED"
        parsed.append((window_start, window_end))
    if any(start >= window_start and end <= window_end for window_start, window_end in parsed):
        return None
    return "OUTSIDE"


def _catalog_field_violations(
    *,
    job: MaintenanceJob,
    crew: Any,
    asset: Any | None,
    start: datetime,
    end: datetime,
) -> list[ConstraintViolation]:
    """Honor previously decorative catalog fields (shift, safety, service area)."""
    violations: list[ConstraintViolation] = []
    for name, rows, kind in (
        ("shift_calendar", list(getattr(crew, "shift_calendar", []) or []), "SHIFT_CALENDAR"),
        ("availability", list(getattr(crew, "availability", []) or []), "AVAILABILITY"),
    ):
        verdict = _calendar_covers(rows, start, end)
        if verdict == "MALFORMED":
            violations.append(
                ConstraintViolation(
                    kind=f"{kind}_MALFORMED",
                    message=f"crew {crew.code} {name} entries must have parseable start/end",
                    job_id=job.id,
                )
            )
        elif verdict == "OUTSIDE":
            violations.append(
                ConstraintViolation(
                    kind=f"{kind}_VIOLATION",
                    message=(
                        f"job {job.external_ref} assignment is outside crew {crew.code} {name}"
                    ),
                    job_id=job.id,
                )
            )

    required_safety = set(job.safety_constraints)
    if required_safety:
        clearances = set(crew.qualifications)
        extra = getattr(crew, "domain_attributes", {}) or {}
        listed = extra.get("safety_clearances", [])
        if isinstance(listed, list):
            clearances.update(str(item) for item in listed)
        if not required_safety.issubset(clearances):
            violations.append(
                ConstraintViolation(
                    kind="SAFETY_CONSTRAINT_MISMATCH",
                    message=(
                        f"job {job.external_ref} safety_constraints {sorted(required_safety)} "
                        f"are not covered by crew {crew.code}"
                    ),
                    job_id=job.id,
                )
            )

    asset_area = str(getattr(asset, "service_area", "") or "") if asset is not None else ""
    crew_area = str(getattr(crew, "service_area", "") or "")
    if asset_area and crew_area and asset_area != crew_area:
        violations.append(
            ConstraintViolation(
                kind="SERVICE_AREA_MISMATCH",
                message=(
                    f"job {job.external_ref} asset area {asset_area!r} "
                    f"does not match crew {crew.code} area {crew_area!r}"
                ),
                job_id=job.id,
            )
        )
    return violations


def _asset_overlap_violations(
    result: ScheduleResult,
    op_to_job: dict[UUID, UUID],
    jobs_by_id: dict[UUID, MaintenanceJob],
) -> list[ConstraintViolation]:
    """Two interruption jobs on the same asset cannot overlap in time."""
    per_asset: dict[UUID, list[tuple[datetime, datetime, MaintenanceJob]]] = {}
    for asn in result.assignments:
        job_id = op_to_job.get(asn.operation_id)
        if job_id is None:
            continue
        job = jobs_by_id[job_id]
        if not job.interruption_required:
            continue
        per_asset.setdefault(job.asset_id, []).append((asn.start_time, asn.end_time, job))

    out: list[ConstraintViolation] = []
    for asset_id, spans in per_asset.items():
        spans.sort(key=lambda item: item[0])
        for prev, cur in zip(spans, spans[1:], strict=False):
            if prev[1] > cur[0]:  # half-open [start, end): touching is OK
                out.append(
                    ConstraintViolation(
                        kind="ASSET_OVERLAP",
                        message=(
                            f"jobs {prev[2].external_ref} and {cur[2].external_ref} "
                            "overlap on the same asset — simultaneous outage work "
                            "is physically impossible"
                        ),
                        job_id=cur[2].id,
                        details={"asset_id": str(asset_id), "other_job": prev[2].external_ref},
                    )
                )
    return out


def _chain_occupancy_spans(
    jobs: list[MaintenanceJob],
    scheduled: dict[UUID, tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime, MaintenanceJob]]:
    """Hull of each precedence-connected interruption chain on one asset.

    Independent jobs (no predecessor on this asset) stay separate intervals.
    """

    if not jobs:
        return []
    parent = {job.id: job.id for job in jobs}
    ids = set(parent)

    def find(node: UUID) -> UUID:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for job in jobs:
        for pred in job.predecessor_job_ids:
            if pred in ids:
                ra, rb = find(job.id), find(pred)
                if ra != rb:
                    parent[rb] = ra

    groups: dict[UUID, list[MaintenanceJob]] = {}
    for job in jobs:
        groups.setdefault(find(job.id), []).append(job)

    out: list[tuple[datetime, datetime, MaintenanceJob]] = []
    for members in groups.values():
        timed = [scheduled[m.id] + (m,) for m in members if m.id in scheduled]
        if not timed:
            continue
        start = min(item[0] for item in timed)
        end = max(item[1] for item in timed)
        rep = max(timed, key=lambda item: item[1])[2]
        out.append((start, end, rep))
    return out


def _simultaneous_outage_ban_violations(
    problem: GridPlanProblem,
    result: ScheduleResult,
    op_to_job: dict[UUID, UUID],
    jobs_by_id: dict[UUID, MaintenanceJob],
) -> list[ConstraintViolation]:
    """Customer-declared anti-coincidence across DIFFERENT assets.

    Explicit ``network_constraints`` only — not topology / N-1 / load-flow.
    Chain occupancy is the hull of a precedence-connected interruption
    component (Goel et al., EJOR 2013), not pairwise task intervals.
    """
    if not problem.simultaneous_outage_bans:
        return []

    scheduled: dict[UUID, tuple[datetime, datetime]] = {}
    for asn in result.assignments:
        job_id = op_to_job.get(asn.operation_id)
        if job_id is None:
            continue
        job = jobs_by_id[job_id]
        if not job.interruption_required:
            continue
        scheduled[job_id] = (asn.start_time, asn.end_time)

    by_asset: dict[UUID, list[MaintenanceJob]] = {}
    for job in problem.jobs:
        if job.interruption_required:
            by_asset.setdefault(job.asset_id, []).append(job)

    occupancy: dict[UUID, list[tuple[datetime, datetime, MaintenanceJob]]] = {
        asset_id: _chain_occupancy_spans(jobs, scheduled) for asset_id, jobs in by_asset.items()
    }

    out: list[ConstraintViolation] = []
    for ban in problem.simultaneous_outage_bans:
        left = occupancy.get(ban.asset_id_a, [])
        right = occupancy.get(ban.asset_id_b, [])
        for a_start, a_end, a_job in left:
            for b_start, b_end, b_job in right:
                if a_start < b_end and b_start < a_end:
                    out.append(
                        ConstraintViolation(
                            kind="SIMULTANEOUS_OUTAGE_BAN",
                            message=(
                                f"chain occupancy of {a_job.external_ref} and "
                                f"{b_job.external_ref} overlap under customer "
                                "simultaneous-outage ban"
                                + (f" ({ban.reason})" if ban.reason else "")
                            ),
                            job_id=b_job.id,
                            details={
                                "ban_id": str(ban.id),
                                "asset_a": str(ban.asset_id_a),
                                "asset_b": str(ban.asset_id_b),
                                "other_job": a_job.external_ref,
                                "occupancy": "precedence_chain_hull",
                            },
                        )
                    )
    return out


def _crew_overlap_violations(
    result: ScheduleResult,
    crews_by_id: dict[UUID, Any],
    crew_of_wc: dict[UUID, UUID],
    op_to_job: dict[UUID, UUID],
    jobs_by_id: dict[UUID, MaintenanceJob],
) -> list[ConstraintViolation]:
    """Crew double-booking. SynAPS also flags MACHINE_OVERLAP; this copy
    covers standalone callers of check_gridplan_constraints.
    """
    per_crew: dict[UUID, list[tuple[datetime, datetime, str]]] = {}
    for asn in result.assignments:
        crew_id = crew_of_wc.get(asn.work_center_id)
        if crew_id is None:
            continue
        job_id = op_to_job.get(asn.operation_id)
        ref = jobs_by_id[job_id].external_ref if job_id in jobs_by_id else str(asn.operation_id)
        per_crew.setdefault(crew_id, []).append((asn.start_time, asn.end_time, ref))

    out: list[ConstraintViolation] = []
    for crew_id, spans in per_crew.items():
        crew = crews_by_id[crew_id]
        events = [(s, 1, ref) for s, _e, ref in spans] + [(e, -1, ref) for _s, e, ref in spans]
        in_use = 0
        for ts, delta, ref in sorted(events, key=lambda item: (item[0], 0 if item[1] < 0 else 1)):
            in_use += delta
            if in_use > crew.max_parallel:
                out.append(
                    ConstraintViolation(
                        kind="CREW_OVERLAP",
                        message=(
                            f"crew {crew.code} double-booked at {ts.isoformat()}: "
                            f"{in_use} jobs > max_parallel={crew.max_parallel} (e.g. {ref})"
                        ),
                        details={"crew_id": str(crew_id)},
                    )
                )
                break  # one proof per crew is enough
    return out


def _outage_violations(
    problem: GridPlanProblem,
    job: MaintenanceJob,
    start: datetime,
    end: datetime,
) -> list[ConstraintViolation]:
    if not job.interruption_required:
        return []

    windows = [w for w in problem.outage_windows if w.asset_id == job.asset_id and w.approved]
    for w in windows:
        if job.id in w.forbidden_job_ids and start < w.end and end > w.start:
            return [
                ConstraintViolation(
                    kind="FORBIDDEN_OUTAGE_WINDOW",
                    message=(
                        f"job {job.external_ref} intersects forbidden outage "
                        f"{w.external_ref or w.id}"
                    ),
                    job_id=job.id,
                )
            ]

    allowed = []
    for w in windows:
        if w.forbidden_job_ids and job.id in w.forbidden_job_ids:
            continue
        if w.allowed_job_ids and job.id not in w.allowed_job_ids:
            continue
        allowed.append(w)

    if not allowed:
        return [
            ConstraintViolation(
                kind="OUTAGE_WINDOW_MISSING",
                message=(
                    f"job {job.external_ref} requires interruption but has no approved "
                    "outage window"
                ),
                job_id=job.id,
            )
        ]

    for w in allowed:
        if start >= w.start and end <= w.end:
            return []

    return [
        ConstraintViolation(
            kind="OUTAGE_WINDOW_VIOLATION",
            message=(
                f"job {job.external_ref} scheduled [{start.isoformat()} .. {end.isoformat()}] "
                "outside all allowed outage windows"
            ),
            job_id=job.id,
        )
    ]


def _precedence_violations(
    problem: GridPlanProblem,
    result: ScheduleResult,
    id_map: dict[str, UUID],
    op_to_job: dict[UUID, UUID],
) -> list[ConstraintViolation]:
    start_by_job: dict[UUID, datetime] = {}
    end_by_job: dict[UUID, datetime] = {}
    for asn in result.assignments:
        job_id = op_to_job.get(asn.operation_id)
        if job_id is None:
            continue
        start_by_job[job_id] = asn.start_time
        end_by_job[job_id] = asn.end_time

    out: list[ConstraintViolation] = []
    jobs_by_id = {j.id: j for j in problem.jobs}
    for job in problem.jobs:
        if job.id not in start_by_job:
            continue
        for pred in job.predecessor_job_ids:
            if pred not in end_by_job:
                out.append(
                    ConstraintViolation(
                        kind="PRECEDENCE_VIOLATION",
                        message=(
                            f"job {job.external_ref} starts without scheduled predecessor "
                            f"{jobs_by_id.get(pred).external_ref if pred in jobs_by_id else pred}"
                        ),
                        job_id=job.id,
                    )
                )
            elif start_by_job[job.id] < end_by_job[pred]:
                out.append(
                    ConstraintViolation(
                        kind="PRECEDENCE_VIOLATION",
                        message=f"job {job.external_ref} overlaps predecessor {pred}",
                        job_id=job.id,
                    )
                )
    _ = id_map
    return out


def _spare_violations(
    problem: GridPlanProblem,
    result: ScheduleResult,
    id_map: dict[str, UUID],
    op_to_job: dict[UUID, UUID],
    spares_by_id: dict,
) -> list[ConstraintViolation]:
    """Consumable stock post-check (SynAPS aux = concurrent pool only)."""

    consumption: dict[UUID, int] = {s.id: 0 for s in problem.spare_parts}
    assigned_ops = {a.operation_id for a in result.assignments}
    out: list[ConstraintViolation] = []
    for job in problem.jobs:
        op_id = id_map.get(f"job:{job.id}")
        if op_id is None or op_id not in assigned_ops:
            continue
        asn = next(a for a in result.assignments if a.operation_id == op_id)
        for spare_id in job.spare_part_ids:
            spare = spares_by_id.get(spare_id)
            if spare is None:
                continue
            if spare.replenishment_date is not None and asn.start_time < spare.replenishment_date:
                out.append(
                    ConstraintViolation(
                        kind="SPARE_PART_NOT_YET_AVAILABLE",
                        message=(
                            f"job {job.external_ref} uses {spare.code} before replenishment "
                            f"{spare.replenishment_date.isoformat()}"
                        ),
                        job_id=job.id,
                    )
                )
            consumption[spare_id] = consumption.get(spare_id, 0) + 1
            # one unit per listed spare id; per-job BOM quantity is out of scope
    for spare in problem.spare_parts:
        used = consumption.get(spare.id, 0)
        if used > spare.usable_quantity:
            out.append(
                ConstraintViolation(
                    kind="SPARE_PART_SHORTAGE",
                    message=(
                        f"spare {spare.code}: consumed {used} > usable {spare.usable_quantity} "
                        f"(available={spare.available_quantity}, "
                        f"reserved={spare.reserved_quantity})"
                    ),
                    details={"spare_id": str(spare.id), "consumed": used},
                )
            )
    _ = op_to_job
    return out


def _frozen_violations(
    frozen: list[FrozenAssignment],
    result: ScheduleResult,
    id_map: dict[str, UUID],
    op_to_job: dict[UUID, UUID],
    crew_of_wc: dict[UUID, UUID],
    jobs_by_id: dict[UUID, MaintenanceJob],
) -> list[ConstraintViolation]:
    if not frozen:
        return []

    by_job: dict[UUID, Assignment] = {}
    for asn in result.assignments:
        job_id = op_to_job.get(asn.operation_id)
        if job_id is not None:
            by_job[job_id] = asn

    out: list[ConstraintViolation] = []
    for fr in frozen:
        if not fr.immutable:
            continue
        asn = by_job.get(fr.job_id)
        job = jobs_by_id.get(fr.job_id)
        label = job.external_ref if job else str(fr.job_id)
        if asn is None:
            out.append(
                ConstraintViolation(
                    kind="FROZEN_ASSIGNMENT_CONFLICT",
                    message=f"frozen job {label} missing from repaired schedule",
                    job_id=fr.job_id,
                )
            )
            continue
        crew_id = crew_of_wc.get(asn.work_center_id)
        if crew_id != fr.crew_id or asn.start_time != fr.start or asn.end_time != fr.end:
            out.append(
                ConstraintViolation(
                    kind="FROZEN_ASSIGNMENT_CONFLICT",
                    message=(
                        f"frozen job {label} changed: expected crew={fr.crew_id} "
                        f"[{fr.start.isoformat()}..{fr.end.isoformat()}], "
                        f"got crew={crew_id} "
                        f"[{asn.start_time.isoformat()}..{asn.end_time.isoformat()}]"
                    ),
                    job_id=fr.job_id,
                    details={
                        "expected_crew_id": str(fr.crew_id),
                        "actual_crew_id": str(crew_id) if crew_id else None,
                    },
                )
            )
    _ = id_map
    return out
