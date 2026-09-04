"""Deterministic calendar FIFO baseline (no SynAPS solver).

Earliest-due-date dispatch for synthetic comparisons. Transparent OR
baseline — not an industrial field-workforce method (ČEZ Distribuce /
Hexaly class: daily technician routing). Heuristic, never optimal.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from synaps.model import Assignment, ObjectiveValues, ScheduleResult, SolverStatus

from synaps_gridplan.adapter import compile_frozen_assignments, to_schedule_problem
from synaps_gridplan.fingerprint import fingerprint_payload
from synaps_gridplan.model import SCHEMA_VERSION, GridPlanProblem
from synaps_gridplan.planner import PlanOutcome, _wrap
from synaps_gridplan.versions import SYNAPS_COMMIT


def plan_fifo(
    problem: GridPlanProblem,
    *,
    apply_frozen: bool = False,
) -> PlanOutcome:
    """Earliest-due-date first; assign first eligible free crew (deterministic)."""

    schedule_problem, id_map = to_schedule_problem(problem)
    ops = {op.id: op for op in schedule_problem.operations}
    job_of_op = {id_map[f"job:{j.id}"]: j for j in problem.jobs if f"job:{j.id}" in id_map}
    crews = list(schedule_problem.work_centers)
    crew_free: dict[UUID, datetime] = {wc.id: problem.planning_horizon_start for wc in crews}

    # Stable order: due date, then external_ref, then id.
    ordered_jobs = sorted(
        problem.jobs,
        key=lambda j: (
            j.due_date or problem.planning_horizon_end,
            j.external_ref,
            str(j.id),
        ),
    )

    assignments: list[Assignment] = []
    frozen_ops: set[UUID] = set()
    if apply_frozen:
        # Pin immutable (and explicit) ПЛ rows first; skip those jobs below.
        # Conservative: crew_free advances to frozen.end — FIFO does not pack
        # the hole before a frozen slot (overlap would be fail-closed anyway).
        for asn in compile_frozen_assignments(problem, schedule_problem, id_map):
            if asn.operation_id in frozen_ops:
                continue
            assignments.append(asn)
            frozen_ops.add(asn.operation_id)
            prev = crew_free.get(asn.work_center_id, problem.planning_horizon_start)
            if asn.end_time > prev:
                crew_free[asn.work_center_id] = asn.end_time

    for job in ordered_jobs:
        op_id = id_map.get(f"job:{job.id}")
        if op_id is None or op_id in frozen_ops:
            continue
        op = ops[op_id]
        eligible = list(op.eligible_wc_ids) or [wc.id for wc in crews]
        # Pick earliest free eligible crew (tie-break by work-center code, then id).
        best_wc: UUID | None = None
        best_start: datetime | None = None
        crew_code = {wc.id: wc.code for wc in crews}
        for wc_id in eligible:
            free_at = crew_free.get(wc_id, problem.planning_horizon_start)
            release = job.release_date or problem.planning_horizon_start
            start = max(free_at, release, problem.planning_horizon_start)
            end = start + timedelta(minutes=op.base_duration_min)
            if end > problem.planning_horizon_end:
                continue
            code = crew_code.get(wc_id, "")
            best_code = crew_code.get(best_wc, "") if best_wc is not None else ""
            if (
                best_start is None
                or start < best_start
                or (start == best_start and (code, str(wc_id)) < (best_code, str(best_wc)))
            ):
                best_wc = wc_id
                best_start = start
        if best_wc is None or best_start is None:
            continue
        end = best_start + timedelta(minutes=op.base_duration_min)
        assignments.append(
            Assignment(
                operation_id=op_id,
                work_center_id=best_wc,
                start_time=best_start,
                end_time=end,
                setup_minutes=0,
            )
        )
        crew_free[best_wc] = end

    unscheduled = len(schedule_problem.operations) - len(assignments)
    coverage = (
        len(assignments) / len(schedule_problem.operations) if schedule_problem.operations else 1.0
    )
    makespan = 0.0
    if assignments:
        t0 = min(a.start_time for a in assignments)
        t1 = max(a.end_time for a in assignments)
        makespan = (t1 - t0).total_seconds() / 60.0

    tardiness = 0.0
    for a in assignments:
        job = job_of_op.get(a.operation_id)
        if job is not None and job.due_date is not None and a.end_time > job.due_date:
            tardiness += (a.end_time - job.due_date).total_seconds() / 60.0

    # Empty instance (zero jobs) is vacuously feasible, not a solver failure.
    status = (
        SolverStatus.INFEASIBLE
        if not assignments and schedule_problem.operations
        else SolverStatus.FEASIBLE
    )
    result = ScheduleResult(
        solver_name="FIFO",
        status=status,
        assignments=assignments,
        objective=ObjectiveValues(
            makespan_minutes=makespan,
            total_tardiness_minutes=tardiness,
            coverage=coverage,
            unscheduled_operations=unscheduled,
        ),
        metadata={
            "baseline": "calendar_fifo_earliest_due",
            "metric_tag": "synthetic_experiment",
            "config_hash": fingerprint_payload(
                {"solver_config": "FIFO", "synaps_commit": SYNAPS_COMMIT}
            ),
        },
    )
    return _wrap(
        result,
        id_map,
        "FIFO",
        schedule_problem,
        problem,
        expected_frozen=list(problem.frozen_assignments),
        kwargs_for_hash={"apply_frozen": apply_frozen},
    )


def plan_with_config(
    problem: GridPlanProblem,
    *,
    solver_config: str = "GREED",
    apply_frozen: bool = True,
    solve_kwargs: dict[str, Any] | None = None,
) -> PlanOutcome:
    """Dispatch to FIFO baseline or SynAPS portfolio configs."""

    if solver_config.upper() == "FIFO":
        return plan_fifo(problem, apply_frozen=apply_frozen)
    from synaps_gridplan.planner import plan_maintenance

    return plan_maintenance(
        problem,
        solver_config=solver_config,
        apply_frozen=apply_frozen,
        solve_kwargs=solve_kwargs,
    )


__all__ = ["plan_fifo", "plan_with_config", "SCHEMA_VERSION"]
