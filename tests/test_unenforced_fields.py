"""Decorative catalog fields warn. Zero-stock lead time is a hard gate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.model import (
    Asset,
    Crew,
    FailureMode,
    GridPlanProblem,
    MaintenanceJob,
    SparePart,
)
from synaps_gridplan.report import render_report

T0 = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)


def _problem(**kwargs: object) -> GridPlanProblem:
    asset = kwargs.get("asset")
    if not isinstance(asset, Asset):
        asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    spare = kwargs.get("spare")
    if not isinstance(spare, SparePart):
        spare = SparePart(code="S", available_quantity=1)
    job_kwargs = {"external_ref": "J", "asset_id": asset.id, "duration_min": 60}
    extra = kwargs.get("job_extra")
    if isinstance(extra, dict):
        job_kwargs.update(extra)
    job_kwargs["spare_part_ids"] = [spare.id]
    return GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[MaintenanceJob(**job_kwargs)],
        spare_parts=[spare],
        planning_horizon_start=T0,
        planning_horizon_end=T0 + timedelta(days=5),
    )


def _fields(outcome) -> list[str]:
    return [row["field"] for row in outcome.metadata["unenforced_fields"]]


def test_zero_stock_lead_time_blocks_use_before_the_delay() -> None:
    problem = _problem(spare=SparePart(code="S", available_quantity=0, lead_time_min=120))
    outcome = plan_with_config(problem, solver_config="GREED")
    kinds = outcome.metadata["gridplan_violation_kinds"]
    assert "SPARE_PART_NOT_YET_AVAILABLE" in kinds
    assert "SPARE_PART_SHORTAGE" in kinds
    assert not outcome.ok
    assert "SparePart.lead_time_min" not in _fields(outcome)


def test_lead_time_does_not_create_stock_after_the_delay() -> None:
    problem = _problem(
        spare=SparePart(code="S", available_quantity=0, lead_time_min=60),
        job_extra={"release_date": T0 + timedelta(hours=3)},
    )
    outcome = plan_with_config(problem, solver_config="GREED")
    kinds = outcome.metadata["gridplan_violation_kinds"]
    assert "SPARE_PART_SHORTAGE" in kinds
    assert "SPARE_PART_NOT_YET_AVAILABLE" not in kinds


def test_on_hand_stock_ignores_lead_time_and_warns() -> None:
    problem = _problem(spare=SparePart(code="S", available_quantity=4, lead_time_min=10**6))
    outcome = plan_with_config(problem, solver_config="GREED")
    assert outcome.ok
    assert outcome.hard_violation_count == 0
    assert "SparePart.lead_time_min" in _fields(outcome)
    text = render_report(outcome, fmt="markdown")
    assert "Stored fields with no effect" in text
    assert "usable stock is already on hand" in text


def test_replenishment_date_wins_and_lead_time_is_advisory() -> None:
    problem = _problem(
        spare=SparePart(
            code="S",
            available_quantity=0,
            lead_time_min=10,
            replenishment_date=T0 + timedelta(days=30),
        )
    )
    outcome = plan_with_config(problem, solver_config="GREED")
    kinds = outcome.metadata["gridplan_violation_kinds"]
    assert "SPARE_PART_NOT_YET_AVAILABLE" in kinds
    assert "SPARE_PART_SHORTAGE" in kinds
    notes = outcome.metadata["unenforced_fields"]
    lead = next(row for row in notes if row["field"] == "SparePart.lead_time_min")
    assert "replenishment_date" in lead["message"]


def test_decorative_catalog_fields_warn_without_failing_the_plan() -> None:
    parent = Asset(code="PARENT", location_code="L")
    asset = Asset(
        code="A",
        location_code="L",
        voltage_level="10kV",
        parent_asset_id=parent.id,
        coordinates={"lat": 55.0, "lon": 37.0},
        failure_modes=[FailureMode(code="wear", label="wear")],
    )
    spare = SparePart(code="S", available_quantity=2, warehouse_location="yard")
    problem = _problem(asset=asset, spare=spare)
    problem = problem.model_copy(update={"assets": [parent, asset]})
    outcome = plan_with_config(problem, solver_config="GREED")
    assert outcome.ok
    fields = set(_fields(outcome))
    assert fields == {
        "Asset.voltage_level",
        "Asset.parent_asset_id",
        "Asset.coordinates",
        "Asset.failure_modes",
        "SparePart.warehouse_location",
    }
    assert all(row["kind"] == "UNENFORCED_FIELD" for row in outcome.metadata["unenforced_fields"])
