"""Risk exposure proxy metrics — advisory, not failure certificates."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from synaps.model import ScheduleResult

from synaps_gridplan.model import Asset, Criticality, GridPlanProblem, MaintenanceJob
from synaps_gridplan.risk import effective_risk

_CRIT_WEIGHT = {
    Criticality.LOW: 0.5,
    Criticality.MEDIUM: 1.0,
    Criticality.HIGH: 1.5,
    Criticality.CRITICAL: 2.0,
}


def risk_exposure_for_job(
    job: MaintenanceJob,
    asset: Asset,
    *,
    exposure_duration_min: float | None = None,
) -> float:
    """Proxy: PoF × consequence × exposure_duration × criticality_weight."""

    risk = effective_risk(job, asset)
    duration = float(
        exposure_duration_min if exposure_duration_min is not None else job.duration_min
    )
    return (
        risk.probability_of_failure
        * risk.consequence_score
        * duration
        * _CRIT_WEIGHT[risk.criticality]
    )


def compute_risk_metrics(
    problem: GridPlanProblem,
    result: ScheduleResult | None,
    id_map: dict[str, UUID],
) -> dict[str, Any]:
    """Compute advisory risk proxy metrics for a plan (or unscheduled baseline)."""

    assets = {a.id: a for a in problem.assets}
    op_to_job = {id_map[f"job:{j.id}"]: j.id for j in problem.jobs if f"job:{j.id}" in id_map}
    assigned: dict[UUID, Any] = {}
    if result is not None:
        for asn in result.assignments:
            jid = op_to_job.get(asn.operation_id)
            if jid is not None:
                assigned[jid] = asn

    before = 0.0
    after = 0.0
    overdue_risk = 0.0
    critical_late = 0
    unserved_critical = 0
    emergency_backlog = 0

    for job in problem.jobs:
        asset = assets[job.asset_id]
        risk = effective_risk(job, asset)
        before += risk_exposure_for_job(job, asset)
        asn = assigned.get(job.id)
        if asn is None:
            after += risk_exposure_for_job(job, asset)
            if risk.criticality in {Criticality.HIGH, Criticality.CRITICAL}:
                unserved_critical += 1
            if job.kind.value == "emergency":
                emergency_backlog += 1
            continue
        # Served: residual exposure uses zero remaining duration for proxy "after".
        # Late jobs keep their exposure in `overdue_risk_exposure` instead.
        after += 0.0
        if job.due_date is not None and asn.end_time > job.due_date:
            overdue_risk += risk_exposure_for_job(job, asset)
            if risk.criticality in {Criticality.HIGH, Criticality.CRITICAL}:
                critical_late += 1

    return {
        "metric_kind": "risk_proxy",
        "is_advisory": True,
        "total_risk_exposure": after,
        "risk_exposure_before": before,
        "risk_exposure_after": after,
        "risk_exposure_delta": before - after,
        "overdue_risk_exposure": overdue_risk,
        "unserved_critical_jobs": unserved_critical,
        "emergency_backlog": emergency_backlog,
        "critical_jobs_late": critical_late,
        "claim_note": (
            "Proxy only. Not a validated failure model. Not industrial risk reduction proof."
        ),
    }
