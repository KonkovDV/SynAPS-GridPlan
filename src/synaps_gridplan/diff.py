"""Plan-to-plan assignment diff (machine-readable)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from synaps.model import Assignment, ScheduleResult

from synaps_gridplan.model import FrozenAssignment, GridPlanProblem, MaintenanceJob


def assignment_key(a: Assignment) -> tuple[UUID, UUID, str, str]:
    return (
        a.operation_id,
        a.work_center_id,
        a.start_time.isoformat(),
        a.end_time.isoformat(),
    )


def diff_plans(
    *,
    base: ScheduleResult,
    repaired: ScheduleResult,
    id_map: dict[str, UUID],
    frozen: list[FrozenAssignment],
    problem: GridPlanProblem | None = None,
    newly_late_job_ids: list[UUID] | None = None,
    newly_unassigned_job_ids: list[UUID] | None = None,
    changed_metrics: dict[str, Any] | None = None,
    violations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare two schedules; map ops back to jobs when possible."""

    job_of_op = {v: k.removeprefix("job:") for k, v in id_map.items() if k.startswith("job:")}
    base_map = {a.operation_id: a for a in base.assignments}
    new_map = {a.operation_id: a for a in repaired.assignments}

    added = [a for op, a in new_map.items() if op not in base_map]
    removed = [a for op, a in base_map.items() if op not in new_map]
    moved = []
    for op, a in new_map.items():
        b = base_map.get(op)
        if b is None:
            continue
        if (
            b.work_center_id != a.work_center_id
            or b.start_time != a.start_time
            or b.end_time != a.end_time
        ):
            moved.append({"before": _row(b, job_of_op), "after": _row(a, job_of_op)})

    frozen_job_ids = {f.job_id for f in frozen if f.immutable}
    unchanged_frozen = []
    for fr in frozen:
        if not fr.immutable:
            continue
        op = id_map.get(f"job:{fr.job_id}")
        if op is None:
            continue
        a = new_map.get(op)
        expected_wc = id_map.get(f"crew:{fr.crew_id}")
        if (
            a is not None
            and a.start_time == fr.start
            and a.end_time == fr.end
            and (expected_wc is None or a.work_center_id == expected_wc)
        ):
            unchanged_frozen.append(_row(a, job_of_op))

    late_ids = newly_late_job_ids
    unassigned_ids = newly_unassigned_job_ids
    metrics = changed_metrics
    if problem is not None:
        auto_late, auto_unassigned, auto_metrics = _auto_metrics(
            problem, base, repaired, id_map, job_of_op
        )
        if late_ids is None:
            late_ids = auto_late
        if unassigned_ids is None:
            unassigned_ids = auto_unassigned
        if metrics is None:
            metrics = auto_metrics

    return {
        "schema_version": "gridplan.diff.v1",
        "added_assignments": [_row(a, job_of_op) for a in added],
        "removed_assignments": [_row(a, job_of_op) for a in removed],
        "moved_assignments": moved,
        "unchanged_frozen_assignments": unchanged_frozen,
        "frozen_job_count": len(frozen_job_ids),
        "newly_late_jobs": [str(x) for x in (late_ids or [])],
        "newly_unassigned_jobs": [str(x) for x in (unassigned_ids or [])],
        "changed_metrics": metrics or {},
        "violations": violations or [],
        "churn": {
            "added": len(added),
            "removed": len(removed),
            "moved": len(moved),
            "unchanged_frozen": len(unchanged_frozen),
        },
    }


def _auto_metrics(
    problem: GridPlanProblem,
    base: ScheduleResult,
    repaired: ScheduleResult,
    id_map: dict[str, UUID],
    job_of_op: dict[UUID, str],
) -> tuple[list[UUID], list[UUID], dict[str, Any]]:
    jobs_by_id = {j.id: j for j in problem.jobs}
    base_ops = {a.operation_id for a in base.assignments}
    repaired_ops = {a.operation_id for a in repaired.assignments}
    base_assigned = {_job_uuid(op, job_of_op) for op in base_ops}
    new_assigned = {_job_uuid(op, job_of_op) for op in repaired_ops}
    base_assigned.discard(None)
    new_assigned.discard(None)

    newly_unassigned = sorted(base_assigned - new_assigned, key=str)

    def late_set(result: ScheduleResult) -> set[UUID]:
        out: set[UUID] = set()
        for a in result.assignments:
            jid = _job_uuid(a.operation_id, job_of_op)
            if jid is None:
                continue
            job = jobs_by_id.get(jid)
            if job is not None and job.due_date is not None and a.end_time > job.due_date:
                out.add(jid)
        return out

    newly_late = sorted(late_set(repaired) - late_set(base), key=str)
    metrics = {
        "base_assignments": len(base.assignments),
        "repaired_assignments": len(repaired.assignments),
        "base_coverage": base.objective.coverage,
        "repaired_coverage": repaired.objective.coverage,
        "base_tardiness_min": base.objective.total_tardiness_minutes,
        "repaired_tardiness_min": repaired.objective.total_tardiness_minutes,
        "base_makespan_min": base.objective.makespan_minutes,
        "repaired_makespan_min": repaired.objective.makespan_minutes,
    }
    _ = id_map
    return newly_late, newly_unassigned, metrics


def _job_uuid(op_id: UUID, job_of_op: dict[UUID, str]) -> UUID | None:
    raw = job_of_op.get(op_id)
    if raw is None:
        return None
    return UUID(raw)


def _row(a: Assignment, job_of_op: dict[UUID, str]) -> dict[str, Any]:
    return {
        "operation_id": str(a.operation_id),
        "job_id": job_of_op.get(a.operation_id),
        "work_center_id": str(a.work_center_id),
        "start": a.start_time.isoformat(),
        "end": a.end_time.isoformat(),
        "setup_minutes": a.setup_minutes,
    }


__all__ = ["assignment_key", "diff_plans", "MaintenanceJob"]
