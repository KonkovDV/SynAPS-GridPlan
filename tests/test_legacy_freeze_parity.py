"""Legacy window locks: one derivation for the compiler and the checker."""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

from synaps_gridplan.adapter import (
    compile_frozen_assignments,
    frozen_assignments_from_windows,
    to_schedule_problem,
)
from synaps_gridplan.legacy_freeze import legacy_window_frozen_assignments
from synaps_gridplan.model import (
    Asset,
    Crew,
    FrozenAssignment,
    GridPlanProblem,
    MaintenanceJob,
    OutageWindow,
)

_ROOT = Path(__file__).resolve().parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


def test_checker_does_not_import_the_compiler() -> None:
    checker = _imports(_ROOT / "src" / "synaps_gridplan" / "constraints.py")
    assert "synaps_gridplan.adapter" not in checker
    freeze = _imports(_ROOT / "src" / "synaps_gridplan" / "legacy_freeze.py")
    assert "synaps_gridplan.adapter" not in freeze
    assert "synaps.model" not in freeze


def test_compiler_window_locks_match_the_checker() -> None:
    start = datetime(2026, 10, 1, 8, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    general = Crew(code="G", home_location_code="L", qualifications=["civil"])
    electrician = Crew(code="E", home_location_code="L", qualifications=["electrical"])
    locked = MaintenanceJob(
        external_ref="LOCK",
        asset_id=asset.id,
        duration_min=60,
        interruption_required=True,
        required_qualifications=["electrical"],
    )
    free = MaintenanceJob(
        external_ref="FREE",
        asset_id=asset.id,
        duration_min=60,
        interruption_required=False,
    )
    short = OutageWindow(
        asset_id=asset.id,
        start=start,
        end=start + timedelta(minutes=30),
        frozen=True,
        approved=True,
        external_ref="short",
    )
    first_fit = OutageWindow(
        asset_id=asset.id,
        start=start + timedelta(hours=2),
        end=start + timedelta(hours=6),
        frozen=True,
        approved=True,
        external_ref="first-fit",
    )
    later_fit = OutageWindow(
        asset_id=asset.id,
        start=start + timedelta(hours=8),
        end=start + timedelta(hours=12),
        frozen=True,
        approved=True,
        external_ref="later-fit",
    )
    unapproved = OutageWindow(
        asset_id=asset.id,
        start=start + timedelta(hours=14),
        end=start + timedelta(hours=18),
        frozen=True,
        approved=False,
        external_ref="draft",
    )
    problem = GridPlanProblem(
        assets=[asset],
        crews=[general, electrician],
        jobs=[locked, free],
        outage_windows=[short, first_fit, later_fit, unapproved],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=1),
    )
    schedule, id_map = to_schedule_problem(problem)
    domain = legacy_window_frozen_assignments(problem)
    compiled = frozen_assignments_from_windows(problem, schedule, id_map)

    assert [(row.job_id, row.crew_id, row.start, row.end) for row in domain] == [
        (locked.id, electrician.id, first_fit.start, first_fit.start + timedelta(minutes=60))
    ]
    assert [
        (row.operation_id, row.work_center_id, row.start_time, row.end_time) for row in compiled
    ] == [
        (
            id_map[f"job:{row.job_id}"],
            id_map[f"crew:{row.crew_id}"],
            row.start,
            row.end,
        )
        for row in domain
    ]

    pinned = compile_frozen_assignments(problem, schedule, id_map)
    assert [(row.operation_id, row.work_center_id, row.start_time) for row in pinned] == [
        (id_map[f"job:{locked.id}"], id_map[f"crew:{electrician.id}"], first_fit.start)
    ]

    explicit = FrozenAssignment(
        job_id=locked.id,
        crew_id=general.id,
        start=later_fit.start,
        end=later_fit.start + timedelta(minutes=60),
    )
    overridden = problem.model_copy(update={"frozen_assignments": [explicit]})
    chosen = compile_frozen_assignments(overridden, schedule, id_map)
    assert len(chosen) == 1
    assert chosen[0].work_center_id == id_map[f"crew:{general.id}"]
    assert chosen[0].start_time == later_fit.start
