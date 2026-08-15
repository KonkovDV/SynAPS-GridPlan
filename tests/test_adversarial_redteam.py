"""Fail-closed completeness: dropped jobs, spare shortage, replenishment masking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.model import (
    Asset,
    Crew,
    GridPlanProblem,
    JobKind,
    MaintenanceJob,
    SparePart,
)

T0 = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)
HORIZON = timedelta(days=5)


def _asset() -> Asset:
    return Asset(
        code="A1",
        name="a",
        asset_class="x",
        location_code="L1",
        data_provenance="synthetic",
    )


def _crew(quals: list[str] | None = None) -> Crew:
    return Crew(code="C1", qualifications=quals or ["q1"], data_provenance="synthetic")


def _job(ref: str, asset: Asset, **kw) -> MaintenanceJob:
    kw.setdefault("kind", JobKind.CORRECTIVE)
    kw.setdefault("duration_min", 60)
    kw.setdefault("required_qualifications", ["q1"])
    kw.setdefault("data_provenance", "synthetic")
    return MaintenanceJob(external_ref=ref, asset_id=asset.id, **kw)


def test_unstaffed_qualification_is_fail_closed() -> None:
    a, c = _asset(), _crew()
    j = _job("J1", a, required_qualifications=["NOPE"])
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    assert not o.verified_feasible
    assert o.status == "error"
    assert o.metadata["gridplan_violation_kinds"]


def test_unschedulable_job_is_flagged_unscheduled() -> None:
    """Job longer than the horizon: FIFO cannot place it — must surface, not vanish."""
    a, c = _asset(), _crew()
    j = _job("J-BIG", a, duration_min=60 * 24 * 30)
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="FIFO", apply_frozen=False)
    assert "UNSCHEDULED_JOB" in o.metadata["gridplan_violation_kinds"]
    assert not o.verified_feasible


def test_spare_shortage_is_fail_closed() -> None:
    a, c = _asset(), _crew()
    s = SparePart(code="S1", available_quantity=1, data_provenance="synthetic")
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[_job("J1", a, spare_part_ids=[s.id]), _job("J2", a, spare_part_ids=[s.id])],
        spare_parts=[s],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    assert "SPARE_PART_SHORTAGE" in o.metadata["gridplan_violation_kinds"]
    assert not o.verified_feasible


def test_replenishment_violation_does_not_mask_shortage() -> None:
    """Pre-replenishment use and over-consumption must both be reported."""
    a, c = _asset(), _crew()
    s = SparePart(
        code="S1",
        available_quantity=1,
        replenishment_date=T0 + timedelta(days=30),
        data_provenance="synthetic",
    )
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[_job("J1", a, spare_part_ids=[s.id]), _job("J2", a, spare_part_ids=[s.id])],
        spare_parts=[s],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    kinds = o.metadata["gridplan_violation_kinds"]
    assert "SPARE_PART_NOT_YET_AVAILABLE" in kinds
    assert "SPARE_PART_SHORTAGE" in kinds


def test_fan_in_precedence_is_fail_closed() -> None:
    """Two predecessors from different chains: SynAPS cannot express fan-in;
    the post-check must flag any violating plan (capability is documented)."""
    a, c = _asset(), _crew()
    p1 = _job("P1", a, kind=JobKind.PREVENTIVE)
    p2 = _job("P2", a, kind=JobKind.PREVENTIVE)
    j = _job("J", a, kind=JobKind.INSPECTION, predecessor_job_ids=[p1.id, p2.id])
    p = GridPlanProblem(
        assets=[a],
        crews=[c],
        jobs=[p1, p2, j],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + HORIZON,
    )
    o = plan_with_config(p, solver_config="GREED", apply_frozen=False)
    kinds = o.metadata["gridplan_violation_kinds"]
    assert not o.verified_feasible
    assert "PRECEDENCE_VIOLATION" in kinds
