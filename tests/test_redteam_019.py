"""Red Team 0.1.9: diamond topology, _cross_refs overflow, sparse precedence.

Three adversarial scenarios not covered by the 0.1.8 test suite.
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from synaps_gridplan.adapter import _job_chains
from synaps_gridplan.model import (
    Asset,
    Crew,
    GridPlanProblem,
    MaintenanceJob,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    asset_id: object,
    *,
    ref: str = "J",
    pred_ids: list[object] | None = None,
) -> MaintenanceJob:
    return MaintenanceJob(
        external_ref=ref,
        asset_id=asset_id,  # type: ignore[arg-type]
        duration_min=60,
        predecessor_job_ids=list(pred_ids or []),  # type: ignore[arg-type]
    )


def _base_problem(
    *,
    jobs: list[MaintenanceJob] | None = None,
    n_extra_assets: int = 0,
) -> dict:
    """Return kwargs for GridPlanProblem with a single asset + crew."""
    start = datetime(2026, 9, 1, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    return dict(
        assets=[asset] + [Asset(code=f"X{i}") for i in range(n_extra_assets)],
        crews=[crew],
        jobs=jobs or [],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=7),
    )


# ---------------------------------------------------------------------------
# 1. Diamond topology: _job_chains partitions into singletons
# ---------------------------------------------------------------------------


def test_diamond_topology_partitions_to_singletons() -> None:
    """Diamond A→B, A→C, B→D, C→D produces four singleton chains.

    _job_chains only forms linear (non-branching) chains. For any non-linear
    precedence graph, the algorithm falls back to singletons. This is an
    architectural boundary: precedence enforcement is delegated to the
    post-checker (PRECEDENCE_VIOLATION).

    This test documents and guards that boundary:
    - No job is lost (all 4 jobs appear in the output).
    - The total number of chains equals the number of jobs (all singletons).
    """
    asset_id = uuid4()
    a = _make_job(asset_id, ref="A")
    b = _make_job(asset_id, ref="B", pred_ids=[a.id])
    c = _make_job(asset_id, ref="C", pred_ids=[a.id])
    d = _make_job(asset_id, ref="D", pred_ids=[b.id, c.id])

    chains = _job_chains([a, b, c, d])

    all_ids = {job.id for chain in chains for job in chain}
    assert all_ids == {a.id, b.id, c.id, d.id}, "no job must be dropped"
    assert len(chains) == 4, (
        f"diamond topology must produce 4 singleton chains, got {len(chains)}"
    )
    assert all(len(chain) == 1 for chain in chains), (
        "each chain must be a singleton for non-linear topology"
    )


def test_diamond_tip_not_silently_dropped() -> None:
    """The join vertex D of a diamond must appear in exactly one chain."""
    asset_id = uuid4()
    a = _make_job(asset_id, ref="A")
    b = _make_job(asset_id, ref="B", pred_ids=[a.id])
    c = _make_job(asset_id, ref="C", pred_ids=[a.id])
    d = _make_job(asset_id, ref="D", pred_ids=[b.id, c.id])

    chains = _job_chains([a, b, c, d])

    d_occurrences = sum(1 for chain in chains for job in chain if job.id == d.id)
    assert d_occurrences == 1, (
        f"join vertex D must appear exactly once, found {d_occurrences} occurrences"
    )


def test_linear_chain_still_correct_after_diamond_fix() -> None:
    """A pure linear chain of 5 jobs must still form one chain of length 5."""
    asset_id = uuid4()
    jobs: list[MaintenanceJob] = []
    prev_id = None
    for i in range(5):
        j = _make_job(asset_id, ref=str(i), pred_ids=[prev_id] if prev_id else None)
        jobs.append(j)
        prev_id = j.id

    chains = _job_chains(jobs)
    assert len(chains) == 1
    assert len(chains[0]) == 5


# ---------------------------------------------------------------------------
# 2. _cross_refs: ValidationError must show overflow count when >20 errors
# ---------------------------------------------------------------------------


def test_cross_refs_overflow_note_when_more_than_20_errors() -> None:
    """When a GridPlanProblem has >20 validation issues the error message
    must include an explicit overflow count — not silently drop errors.

    Before the fix: `"; ".join(issues[:20])` dropped errors 21+.
    After the fix:  the suffix `… and N more` appears in the message.

    This mirrors the _as_markdown truncation fix (PR #18) applied to the
    model layer.
    """
    start = datetime(2026, 9, 1, tzinfo=UTC)
    # Create 25 jobs, each referencing an unknown (different) asset_id.
    # Each produces one issue: "job Jn references unknown asset".
    jobs = [
        MaintenanceJob(
            external_ref=f"J{i}",
            asset_id=uuid4(),  # unknown — not in problem.assets
            duration_min=60,
        )
        for i in range(25)
    ]
    asset = Asset(code="A")
    crew = Crew(code="C")
    with pytest.raises(ValueError) as exc_info:
        GridPlanProblem(
            assets=[asset],
            crews=[crew],
            jobs=jobs,
            planning_horizon_start=start,
            planning_horizon_end=start + timedelta(days=7),
        )
    msg = str(exc_info.value)
    # The overflow suffix must be present.
    assert "more" in msg, (
        "_cross_refs must include an overflow note when issues > _CROSS_REFS_LIMIT; "
        f"got: {msg[:200]}"
    )
    # Exactly _CROSS_REFS_LIMIT=20 errors are listed; 5 are in the overflow.
    assert "5 more" in msg or "and 5" in msg, (
        f"overflow count must be 5, got message: {msg[:200]}"
    )


def test_cross_refs_no_overflow_note_at_exactly_limit() -> None:
    """Exactly 20 errors: no overflow suffix should appear."""
    start = datetime(2026, 9, 1, tzinfo=UTC)
    jobs = [
        MaintenanceJob(
            external_ref=f"J{i}",
            asset_id=uuid4(),
            duration_min=60,
        )
        for i in range(20)
    ]
    asset = Asset(code="A")
    crew = Crew(code="C")
    with pytest.raises(ValueError) as exc_info:
        GridPlanProblem(
            assets=[asset],
            crews=[crew],
            jobs=jobs,
            planning_horizon_start=start,
            planning_horizon_end=start + timedelta(days=7),
        )
    msg = str(exc_info.value)
    assert "more" not in msg, (
        "no overflow note expected when exactly at the limit; got: " + msg[:200]
    )


# ---------------------------------------------------------------------------
# 3. Sparse precedence: unknown predecessor rejected at model construction
# ---------------------------------------------------------------------------


def test_unknown_predecessor_rejected_at_construction() -> None:
    """A job that references a predecessor UUID not in the problem must
    raise ValueError at GridPlanProblem construction time.

    This ensures the model validator catches dangling references before
    they reach the adapter or post-checker.
    """
    start = datetime(2026, 9, 1, tzinfo=UTC)
    asset = Asset(code="A")
    crew = Crew(code="C")
    phantom_pred = uuid4()  # not in jobs list
    job = MaintenanceJob(
        external_ref="J",
        asset_id=asset.id,
        duration_min=60,
        predecessor_job_ids=[phantom_pred],
    )
    with pytest.raises(ValueError, match="unknown predecessor"):
        GridPlanProblem(
            assets=[asset],
            crews=[crew],
            jobs=[job],
            planning_horizon_start=start,
            planning_horizon_end=start + timedelta(days=7),
        )
