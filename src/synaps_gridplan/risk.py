"""Risk proxy helpers — advisory scores, never certificates."""

from __future__ import annotations

from synaps_gridplan.model import Asset, Criticality, MaintenanceJob, RiskProfile


def effective_risk(job: MaintenanceJob, asset: Asset) -> RiskProfile:
    if job.risk_override is not None:
        return job.risk_override
    return asset.risk


def job_priority(job: MaintenanceJob, asset: Asset) -> int:
    """Map risk proxy to SynAPS Order.priority (higher = more urgent).

    Scale: base 100..900 so GREED/ATCS tardiness terms see differentiation
    without saturating the default 500 band.
    """

    risk = effective_risk(job, asset)
    score = risk.risk_score  # typically 0..2
    # Criticality bump even when PoF is low (regulatory / SAIDI-sensitive assets).
    criticality_bump = {
        Criticality.LOW: 0,
        Criticality.MEDIUM: 50,
        Criticality.HIGH: 150,
        Criticality.CRITICAL: 300,
    }[risk.criticality]
    raw = 100 + int(round(score * 300)) + criticality_bump
    if job.kind.value == "emergency":
        raw += 200
    return max(1, min(999, raw))
