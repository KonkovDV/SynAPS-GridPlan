"""Planner façade: SynAPS solve/repair with GridPlan semantics and fail-closed checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from synaps.model import ScheduleProblem, ScheduleResult, SolverStatus
from synaps.portfolio import PortfolioValidationError, repair_schedule, solve_schedule
from synaps.solvers.feasibility_checker import FeasibilityChecker, proven_hard_violations
from synaps.solvers.router import SolveRegime

from synaps_gridplan.adapter import compile_frozen_assignments, to_schedule_problem
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.fingerprint import fingerprint_payload
from synaps_gridplan.model import SCHEMA_VERSION, FrozenAssignment, GridPlanProblem
from synaps_gridplan.practice import practice_snapshot
from synaps_gridplan.risk_metrics import compute_risk_metrics
from synaps_gridplan.versions import GRIDPLAN_VERSION, ISO16290_TRL, SYNAPS_COMMIT


@dataclass(frozen=True)
class PlanOutcome:
    """Result of a GridPlan planning call."""

    schema_version: str
    solver_config: str
    status: str
    verified_feasible: bool
    schedule: ScheduleResult
    schedule_problem: ScheduleProblem
    id_map: dict[str, UUID]
    hard_violation_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    frozen_assignments: tuple[FrozenAssignment, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {SolverStatus.OPTIMAL.value, SolverStatus.FEASIBLE.value} and (
            self.verified_feasible
        )


def plan_maintenance(
    problem: GridPlanProblem,
    *,
    solver_config: str = "GREED",
    solve_kwargs: dict[str, Any] | None = None,
    apply_frozen: bool = True,
) -> PlanOutcome:
    """Solve a maintenance plan. Fail-closed: ERROR if hard-infeasible after 'success'."""

    schedule_problem, id_map = to_schedule_problem(problem)
    kwargs = dict(solve_kwargs or {})
    expected_frozen = list(problem.frozen_assignments)
    if apply_frozen:
        frozen = compile_frozen_assignments(problem, schedule_problem, id_map)
        if frozen:
            kwargs["frozen_assignments"] = frozen

    try:
        result = solve_schedule(
            schedule_problem,
            solver_config=solver_config,
            solve_kwargs=kwargs,
            verify_feasibility=True,
        )
    except PortfolioValidationError as exc:
        from synaps.model import ObjectiveValues

        result = ScheduleResult(
            status=SolverStatus.ERROR,
            solver_name=solver_config,
            assignments=[],
            objective=ObjectiveValues(
                coverage=0.0,
                unscheduled_operations=len(schedule_problem.operations),
            ),
            metadata={"error": "solve_rejected", "detail": str(exc)},
        )

    hash_kw = dict(kwargs)
    hash_kw["apply_frozen"] = apply_frozen
    return _wrap(
        result,
        id_map,
        solver_config,
        schedule_problem,
        problem,
        expected_frozen=expected_frozen,
        kwargs_for_hash=hash_kw,
    )


def replan_after_disruption(
    problem: GridPlanProblem,
    *,
    base_outcome: PlanOutcome,
    disrupted_job_ids: list[UUID],
    solver_config: str = "GREED",
    radius: int | None = None,
    preserve_frozen: list[FrozenAssignment] | None = None,
) -> PlanOutcome:
    """Local repair after disruption; reuses the base compiled problem + id map."""

    compiled_job_ids = {
        UUID(key.removeprefix("job:")) for key in base_outcome.id_map if key.startswith("job:")
    }
    live_job_ids = {job.id for job in problem.jobs}
    if compiled_job_ids != live_job_ids:
        return PlanOutcome(
            schema_version=SCHEMA_VERSION,
            solver_config=f"repair:{solver_config}",
            status=SolverStatus.ERROR.value,
            verified_feasible=False,
            schedule=base_outcome.schedule,
            schedule_problem=base_outcome.schedule_problem.model_copy(deep=True),
            id_map=base_outcome.id_map,
            hard_violation_count=0,
            metadata={"error": "problem_jobs_diverged_from_compiled_schedule"},
            frozen_assignments=tuple(
                preserve_frozen
                if preserve_frozen is not None
                else (base_outcome.frozen_assignments or problem.frozen_assignments)
            ),
        )

    # Deep-copy: SynAPS repair mutates assignments/problem in place; the base
    # outcome must stay immutable (audit trail + "plan didn't move" proofs).
    schedule_problem = base_outcome.schedule_problem.model_copy(deep=True)
    id_map = base_outcome.id_map
    expected_frozen = list(
        preserve_frozen
        if preserve_frozen is not None
        else (base_outcome.frozen_assignments or problem.frozen_assignments)
    )

    disrupted_op_ids: list[UUID] = []
    for job_id in disrupted_job_ids:
        op_id = id_map.get(f"job:{job_id}")
        if op_id is not None:
            disrupted_op_ids.append(op_id)

    if not disrupted_op_ids:
        return PlanOutcome(
            schema_version=SCHEMA_VERSION,
            solver_config=f"repair:{solver_config}",
            status=SolverStatus.ERROR.value,
            verified_feasible=False,
            schedule=base_outcome.schedule,
            schedule_problem=schedule_problem,
            id_map=id_map,
            hard_violation_count=0,
            metadata={"error": "no disrupted jobs mapped to operations"},
            frozen_assignments=tuple(expected_frozen),
        )

    # Default: freeze the rest of the base plan so repair stays local.
    # Explicit ПЛ rows are a subset of that freeze. Pass preserve_frozen=[] to disable.
    if preserve_frozen is None:
        from synaps_gridplan.adapter import extract_frozen_from_result

        job_of_op = {
            v: UUID(k.removeprefix("job:")) for k, v in id_map.items() if k.startswith("job:")
        }
        disrupted_set = set(disrupted_job_ids)
        keep = [
            a
            for a in base_outcome.schedule.assignments
            if job_of_op.get(a.operation_id) is not None
            and job_of_op[a.operation_id] not in disrupted_set
        ]
        if keep:
            expected_frozen = list(
                extract_frozen_from_result(
                    problem,
                    result_assignments=keep,
                    id_map=id_map,
                    reason="disruption_freeze_rest",
                )
            )

    # Pass immutable frozen rows into SynAPS so repair cannot silently move them.
    frozen_kwargs: dict[str, Any] = {}
    if expected_frozen:
        frozen_asns = compile_frozen_assignments(
            problem.model_copy(update={"frozen_assignments": expected_frozen}),
            schedule_problem,
            id_map,
        )
        if frozen_asns:
            frozen_kwargs["frozen_assignments"] = frozen_asns

    try:
        result = repair_schedule(
            schedule_problem,
            base_assignments=[a.model_copy(deep=True) for a in base_outcome.schedule.assignments],
            disrupted_op_ids=disrupted_op_ids,
            radius=radius,
            regime=SolveRegime.BREAKDOWN,
            solve_kwargs=frozen_kwargs,
            verify_feasibility=True,
        )
    except PortfolioValidationError as exc:
        return PlanOutcome(
            schema_version=SCHEMA_VERSION,
            solver_config=f"repair:{solver_config}",
            status=SolverStatus.ERROR.value,
            verified_feasible=False,
            schedule=base_outcome.schedule,
            schedule_problem=schedule_problem,
            id_map=id_map,
            hard_violation_count=0,
            metadata={"error": "repair_rejected", "detail": str(exc)},
            frozen_assignments=tuple(expected_frozen),
        )

    tagged = result.model_copy(update={"solver_name": f"repair:{solver_config}"})
    return _wrap(
        tagged,
        id_map,
        f"repair:{solver_config}",
        schedule_problem,
        problem,
        expected_frozen=expected_frozen,
        kwargs_for_hash={
            "radius": radius,
            "disrupted_job_ids": [str(x) for x in disrupted_job_ids],
        },
    )


def _wrap(
    result: ScheduleResult,
    id_map: dict[str, UUID],
    solver_config: str,
    schedule_problem: ScheduleProblem,
    problem: GridPlanProblem,
    *,
    expected_frozen: list[FrozenAssignment],
    kwargs_for_hash: dict[str, Any] | None = None,
) -> PlanOutcome:
    checker = FeasibilityChecker()
    violations = checker.check(schedule_problem, list(result.assignments))
    hard = proven_hard_violations(violations)
    gp_violations = check_gridplan_constraints(
        problem,
        schedule_problem=schedule_problem,
        result=result,
        id_map=id_map,
        expected_frozen=expected_frozen,
    )

    verified = (
        len(hard) == 0
        and len(gp_violations) == 0
        and result.status in {SolverStatus.OPTIMAL, SolverStatus.FEASIBLE}
    )

    status = result.status.value
    if result.status in {SolverStatus.OPTIMAL, SolverStatus.FEASIBLE} and (hard or gp_violations):
        status = SolverStatus.ERROR.value
        verified = False

    # Heuristic configs never claim OPTIMAL at GridPlan layer.
    heuristic_prefixes = ("FIFO", "GREED", "BEAM", "ALNS", "RHC", "repair:")
    is_heuristic = any(solver_config.startswith(p) for p in heuristic_prefixes)
    claim_status = status
    if is_heuristic and status in {SolverStatus.OPTIMAL.value, SolverStatus.FEASIBLE.value}:
        claim_status = "heuristic_feasible"
        status = SolverStatus.FEASIBLE.value

    input_hash = fingerprint_payload(problem.model_dump(mode="json"))
    config_hash = fingerprint_payload(
        {
            "solver_config": solver_config,
            "synaps_commit": SYNAPS_COMMIT,
            "solve_kwargs": kwargs_for_hash,
            "frozen_job_ids": sorted(str(f.job_id) for f in expected_frozen),
        }
    )
    risk = compute_risk_metrics(problem, result, id_map)

    meta = dict(result.metadata or {})
    meta.update(
        {
            "gridplan_schema_version": SCHEMA_VERSION,
            "gridplan_version": GRIDPLAN_VERSION,
            "synaps_commit": SYNAPS_COMMIT,
            "input_hash": input_hash,
            "config_hash": config_hash,
            "data_provenance": problem.domain_attributes.get("data_provenance", "experiment"),
            "claim_level": problem.domain_attributes.get("claim_level", "experiment"),
            "iso16290_trl": int(problem.domain_attributes.get("iso16290_trl", ISO16290_TRL)),
            "hard_violation_kinds": sorted({v.kind for v in hard}),
            "gridplan_violation_kinds": sorted({v.kind for v in gp_violations}),
            "engine_violations": [{"kind": v.kind, "message": v.message} for v in hard],
            "gridplan_violations": [
                {
                    "kind": v.kind,
                    "message": v.message,
                    "job_id": str(v.job_id) if v.job_id else None,
                }
                for v in gp_violations
            ],
            "risk_proxy": risk,
            "claim_status": claim_status,
            "optimality_note": (
                "Допустимое найденное решение без доказательства оптимальности"
                if claim_status == "heuristic_feasible"
                else None
            ),
            "practice": practice_snapshot(),
        }
    )

    return PlanOutcome(
        schema_version=SCHEMA_VERSION,
        solver_config=solver_config,
        status=status,
        verified_feasible=verified,
        schedule=result,
        schedule_problem=schedule_problem,
        id_map=id_map,
        hard_violation_count=len(hard) + len(gp_violations),
        metadata=meta,
        frozen_assignments=tuple(expected_frozen),
    )
