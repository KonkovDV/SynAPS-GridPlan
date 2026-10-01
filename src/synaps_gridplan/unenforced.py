"""Catalog fields the checker stores but does not enforce, plus spare lead time.

``lead_time_min`` is enforced only when nothing is on hand and no
``replenishment_date`` is set. Every other case is an advisory row, not a
hard violation: a warning must not turn a feasible plan into an error.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from synaps_gridplan.model import GridPlanProblem, SparePart


def lead_time_instant(horizon_start: datetime, lead_time_min: int) -> datetime:
    """Horizon plus procurement delay. Overflow means 'later than any job'."""

    try:
        return horizon_start + timedelta(minutes=lead_time_min)
    except OverflowError:
        return datetime.max.replace(tzinfo=UTC)


def spare_earliest_use(problem: GridPlanProblem, spare: SparePart) -> tuple[datetime, str] | None:
    """Earliest start for a job that consumes ``spare``, and why.

    ``replenishment_date`` wins over ``lead_time_min``. Lead time applies only
    when ``usable_quantity`` is 0: on-hand stock is usable immediately.
    The instant does not add stock.
    """

    if spare.replenishment_date is not None:
        return spare.replenishment_date, "replenishment"
    if spare.usable_quantity == 0 and spare.lead_time_min > 0:
        return lead_time_instant(problem.planning_horizon_start, spare.lead_time_min), "lead_time"
    return None


def _row(field: str, ref: str, message: str) -> dict[str, str]:
    return {"kind": "UNENFORCED_FIELD", "field": field, "ref": ref, "message": message}


def unenforced_fields(problem: GridPlanProblem) -> list[dict[str, Any]]:
    """Non-default catalog values that do not change the verdict."""

    rows: list[dict[str, str]] = []
    for asset in problem.assets:
        if asset.voltage_level.strip():
            rows.append(_row("Asset.voltage_level", asset.code, "stored, not checked"))
        if asset.parent_asset_id is not None:
            rows.append(
                _row(
                    "Asset.parent_asset_id",
                    asset.code,
                    "stored, not checked; no parent-outage coupling",
                )
            )
        if asset.coordinates:
            rows.append(
                _row("Asset.coordinates", asset.code, "stored, not checked; not a travel source")
            )
        if asset.failure_modes:
            rows.append(
                _row(
                    "Asset.failure_modes",
                    asset.code,
                    "stored, not checked; separate from the risk proxy",
                )
            )
    for spare in problem.spare_parts:
        if spare.warehouse_location.strip():
            rows.append(
                _row(
                    "SparePart.warehouse_location",
                    spare.code,
                    "stored, not checked; not a travel node",
                )
            )
        if spare.lead_time_min > 0 and spare.replenishment_date is not None:
            rows.append(
                _row(
                    "SparePart.lead_time_min",
                    spare.code,
                    "ignored because replenishment_date is set",
                )
            )
        elif spare.lead_time_min > 0 and spare.usable_quantity > 0:
            rows.append(
                _row(
                    "SparePart.lead_time_min",
                    spare.code,
                    "ignored because usable stock is already on hand",
                )
            )
    rows.sort(key=lambda row: (row["field"], row["ref"]))
    return rows
