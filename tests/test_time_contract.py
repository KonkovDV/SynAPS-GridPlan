"""Domain timestamps are instants, not ambiguous local clock readings."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from synaps_gridplan.model import (
    DisruptionEvent,
    FrozenAssignment,
    GridPlanProblem,
    MaintenanceJob,
    OutageWindow,
    RiskProfile,
    SparePart,
)


def test_horizon_rejects_naive_timestamps() -> None:
    start = datetime(2026, 9, 1)
    with pytest.raises(ValueError, match="timezone"):
        GridPlanProblem(
            assets=[],
            crews=[],
            jobs=[],
            planning_horizon_start=start,
            planning_horizon_end=start + timedelta(hours=1),
        )


def test_explicit_offsets_are_normalized_without_changing_the_instant() -> None:
    problem = GridPlanProblem(
        assets=[],
        crews=[],
        jobs=[],
        planning_horizon_start="2026-09-01T09:00:00+03:00",
        planning_horizon_end="2026-09-01T10:00:00+03:00",
    )
    assert problem.planning_horizon_start == datetime(2026, 9, 1, 6, tzinfo=UTC)
    assert problem.planning_horizon_start.tzinfo is UTC


def test_fall_back_fold_keeps_the_real_elapsed_hour() -> None:
    zone = ZoneInfo("Europe/Berlin")
    first = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
    second = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1)
    problem = GridPlanProblem(
        assets=[], crews=[], jobs=[], planning_horizon_start=first, planning_horizon_end=second
    )
    assert problem.planning_horizon_end - problem.planning_horizon_start == timedelta(hours=1)


@pytest.mark.parametrize(
    "model, fields",
    [
        (RiskProfile, {"assessment_timestamp": "2026-09-01T06:00:00"}),
        (SparePart, {"code": "SP", "replenishment_date": "2026-09-01T06:00:00"}),
        (DisruptionEvent, {"event_type": "test", "occurred_at": "2026-09-01T06:00:00"}),
        (
            MaintenanceJob,
            {
                "external_ref": "J",
                "asset_id": UUID(int=1),
                "duration_min": 60,
                "release_date": "2026-09-01T06:00:00",
            },
        ),
        (
            OutageWindow,
            {
                "asset_id": UUID(int=1),
                "start": "2026-09-01T06:00:00",
                "end": "2026-09-01T08:00:00Z",
            },
        ),
    ],
)
def test_nested_catalog_instants_also_require_offsets(model, fields) -> None:
    with pytest.raises(ValueError, match="timezone"):
        model.model_validate(fields)


def test_even_advisory_freeze_requires_a_valid_interval() -> None:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="end must be after start"):
        FrozenAssignment(
            job_id=UUID(int=1), crew_id=UUID(int=2), start=start, end=start, immutable=False
        )
