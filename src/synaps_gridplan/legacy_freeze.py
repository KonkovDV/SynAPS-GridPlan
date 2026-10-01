"""Legacy frozen-window locks, shared by the compiler and the checker.

The checker must not import the compiler. Both sides call this module so a
window freeze cannot be an obligation in one path and a suggestion in the other.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from uuid import UUID

from synaps_gridplan.model import (
    FrozenAssignment,
    GridPlanProblem,
    MaintenanceJob,
    OutageWindow,
)


def approved_outage_windows(job: MaintenanceJob, windows: list[OutageWindow]) -> list[OutageWindow]:
    return [
        window
        for window in windows
        if window.approved
        and job.id not in window.forbidden_job_ids
        and (not window.allowed_job_ids or job.id in window.allowed_job_ids)
    ]


def eligible_crew_ids(job: MaintenanceJob, problem: GridPlanProblem) -> list[UUID]:
    required = set(job.required_qualifications)
    selected = [crew.id for crew in problem.crews if required.issubset(set(crew.qualifications))]
    if not selected and not required:
        return [crew.id for crew in problem.crews]
    return selected


def legacy_window_frozen_assignments(problem: GridPlanProblem) -> list[FrozenAssignment]:
    """Domain locks implied by legacy ``outage_windows[].frozen``.

    Explicit ``FrozenAssignment`` rows still win for the same job. The first
    fitting approved window wins; a later window does not add a second lock.
    """

    windows = [window for window in problem.outage_windows if window.frozen and window.approved]
    if not windows:
        return []

    jobs_by_asset: dict[UUID, list[MaintenanceJob]] = defaultdict(list)
    for job in problem.jobs:
        jobs_by_asset[job.asset_id].append(job)

    out: list[FrozenAssignment] = []
    seen: set[UUID] = set()
    for window in windows:
        for job in jobs_by_asset.get(window.asset_id, []):
            if job.id in seen:
                continue
            if not job.interruption_required or not approved_outage_windows(job, [window]):
                continue
            eligible = list(job.eligible_crew_ids) or eligible_crew_ids(job, problem)
            if not eligible:
                continue
            end = window.start + timedelta(minutes=job.duration_min)
            if end > window.end:
                continue
            seen.add(job.id)
            out.append(
                FrozenAssignment(
                    job_id=job.id,
                    crew_id=eligible[0],
                    start=window.start,
                    end=end,
                    source="frozen_outage_window",
                    frozen_reason="legacy_window_freeze",
                    immutable=True,
                    data_provenance=window.data_provenance,
                )
            )
    return out
