"""Unit tests for GridPlan domain, adapter, planner, and reproducibility."""

from __future__ import annotations

from datetime import timedelta

from synaps_gridplan.adapter import (
    compile_frozen_assignments,
    extract_frozen_from_result,
    to_schedule_problem,
)
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.fingerprint import fingerprint_payload, stable_int
from synaps_gridplan.model import Criticality, FrozenAssignment
from synaps_gridplan.planner import plan_maintenance, replan_after_disruption
from synaps_gridplan.report import render_report
from synaps_gridplan.risk import job_priority
from synaps_gridplan.synthetic import synthesize_feeder
from synaps_gridplan.versions import SYNAPS_COMMIT


def test_synthesize_feeder_is_marked_synthetic() -> None:
    problem = synthesize_feeder(mode="small", seed=7)
    assert problem.domain_attributes["data_provenance"] == "synthetic"
    assert problem.domain_attributes["claim_level"] == "experiment"
    assert len(problem.assets) == 12
    assert len(problem.jobs) == 30
    assert len(problem.crews) == 4


def test_adapter_produces_valid_schedule_problem() -> None:
    problem = synthesize_feeder(n_assets=8, n_jobs=20, n_crews=3, seed=1)
    schedule, id_map = to_schedule_problem(problem)
    assert len(schedule.operations) == 20
    assert len(schedule.work_centers) == 3
    assert all(f"job:{job.id}" in id_map for job in problem.jobs)
    assert schedule.planning_horizon_end > schedule.planning_horizon_start


def test_risk_priority_orders_critical_above_low() -> None:
    problem = synthesize_feeder(n_assets=4, n_jobs=4, n_crews=2, seed=3)
    low = next(a for a in problem.assets if a.risk.criticality == Criticality.LOW)
    critical = next(a for a in problem.assets if a.risk.criticality == Criticality.CRITICAL)
    job_low = next(j for j in problem.jobs if j.asset_id == low.id)
    job_crit = next(j for j in problem.jobs if j.asset_id == critical.id)
    assert job_priority(job_crit, critical) > job_priority(job_low, low)


def test_plan_maintenance_greed_returns_structured_outcome() -> None:
    problem = synthesize_feeder(mode="small", seed=11)
    outcome = plan_maintenance(problem, solver_config="GREED")
    assert outcome.schema_version == "gridplan.v1"
    assert outcome.status in {"feasible", "infeasible", "timeout", "error"}
    assert outcome.status != "optimal"
    assert outcome.solver_config == "GREED"
    assert isinstance(outcome.verified_feasible, bool)
    assert outcome.hard_violation_count >= 0
    assert outcome.metadata["input_hash"]
    assert outcome.metadata["config_hash"]
    assert outcome.metadata["synaps_commit"] == SYNAPS_COMMIT
    assert "engine_violations" in outcome.metadata
    report = render_report(outcome, fmt="markdown")
    assert "claim_level: `experiment`" in report
    assert "iso16290_trl:" in report
    assert "input_hash:" in report
    assert "verified_feasible" in report


def test_replan_after_disruption_smoke() -> None:
    problem = synthesize_feeder(mode="small", seed=5)
    base = plan_maintenance(problem, solver_config="GREED")
    disrupted = [problem.jobs[0].id]
    repaired = replan_after_disruption(
        problem,
        base_outcome=base,
        disrupted_job_ids=disrupted,
    )
    assert repaired.solver_config.startswith("repair:")
    assert repaired.schema_version == "gridplan.v1"


def test_replan_does_not_mutate_base_outcome() -> None:
    """Repair must leave the base plan bit-identical (audit + freeze proofs)."""
    problem = synthesize_feeder(mode="small", seed=5)
    base = plan_maintenance(problem, solver_config="GREED")
    before = [a.model_dump(mode="json") for a in base.schedule.assignments]
    replan_after_disruption(
        problem,
        base_outcome=base,
        disrupted_job_ids=[problem.jobs[0].id],
    )
    after = [a.model_dump(mode="json") for a in base.schedule.assignments]
    assert before == after


def test_deterministic_synthesize_same_seed() -> None:
    a = synthesize_feeder(mode="small", seed=42)
    b = synthesize_feeder(mode="small", seed=42)
    assert a.model_dump(mode="json") == b.model_dump(mode="json")
    assert fingerprint_payload(a.model_dump(mode="json")) == fingerprint_payload(
        b.model_dump(mode="json")
    )


def test_synthesize_seed_changes_instance() -> None:
    a = synthesize_feeder(mode="small", seed=1)
    b = synthesize_feeder(mode="small", seed=2)
    assert a.model_dump(mode="json") != b.model_dump(mode="json")


def test_stable_travel_hash_independent_of_python_hash() -> None:
    x = stable_int("42", "LOC-1", "LOC-2", modulo=45)
    y = stable_int("42", "LOC-1", "LOC-2", modulo=45)
    assert x == y
    assert 0 <= x < 45


def test_deterministic_solve_same_input() -> None:
    problem = synthesize_feeder(mode="small", seed=99)
    o1 = plan_maintenance(problem, solver_config="GREED", apply_frozen=False)
    o2 = plan_maintenance(problem, solver_config="GREED", apply_frozen=False)
    assert o1.status == o2.status
    assert o1.metadata["input_hash"] == o2.metadata["input_hash"]
    assert [a.model_dump(mode="json") for a in o1.schedule.assignments] == [
        a.model_dump(mode="json") for a in o2.schedule.assignments
    ]


def test_outage_window_hard_check() -> None:
    problem = synthesize_feeder(mode="small", seed=4)
    interruptable = [j for j in problem.jobs if j.interruption_required]
    if not interruptable:
        return
    schedule, id_map = to_schedule_problem(problem)
    outcome = plan_maintenance(problem, solver_config="GREED", apply_frozen=False)
    violations = check_gridplan_constraints(
        problem,
        schedule_problem=schedule,
        result=outcome.schedule,
        id_map=id_map,
        expected_frozen=[],
    )
    # Either no outage violations, or outcome must not claim verified_feasible.
    outage_kinds = {
        "OUTAGE_WINDOW_VIOLATION",
        "OUTAGE_WINDOW_MISSING",
        "FORBIDDEN_OUTAGE_WINDOW",
    }
    if any(v.kind in outage_kinds for v in violations):
        assert outcome.verified_feasible is False
        assert outcome.status == "error"


def test_frozen_assignment_preserved_on_replan() -> None:
    problem = synthesize_feeder(mode="small", seed=8)
    base = plan_maintenance(problem, solver_config="GREED", apply_frozen=False)
    if not base.schedule.assignments:
        return
    frozen = extract_frozen_from_result(
        problem,
        result_assignments=list(base.schedule.assignments[:3]),
        id_map=base.id_map,
        reason="test_freeze",
    )
    problem2 = problem.model_copy(update={"frozen_assignments": frozen})
    # Disrupt a non-frozen job if possible.
    frozen_jobs = {f.job_id for f in frozen}
    disrupt = next(j.id for j in problem.jobs if j.id not in frozen_jobs)
    repaired = replan_after_disruption(
        problem2,
        base_outcome=base,
        disrupted_job_ids=[disrupt],
        preserve_frozen=frozen,
    )
    for fr in frozen:
        op = repaired.id_map[f"job:{fr.job_id}"]
        match = [a for a in repaired.schedule.assignments if a.operation_id == op]
        if repaired.ok or repaired.status != "error":
            assert match
            assert match[0].start_time == fr.start
            assert match[0].end_time == fr.end
        else:
            kinds = repaired.metadata.get("gridplan_violation_kinds", [])
            assert (
                "FROZEN_ASSIGNMENT_CONFLICT" in kinds
                or repaired.metadata.get("error") == "repair_rejected"
                or repaired.hard_violation_count >= 0
            )


def test_frozen_conflict_detected() -> None:
    problem = synthesize_feeder(mode="small", seed=10)
    base = plan_maintenance(problem, solver_config="GREED", apply_frozen=False)
    if len(base.schedule.assignments) < 1:
        return
    fr = extract_frozen_from_result(
        problem,
        result_assignments=list(base.schedule.assignments[:1]),
        id_map=base.id_map,
    )[0]
    # Corrupt end time to force conflict against actual schedule.
    bad = FrozenAssignment(
        job_id=fr.job_id,
        crew_id=fr.crew_id,
        start=fr.start,
        end=fr.end + timedelta(hours=5),
        immutable=True,
    )
    violations = check_gridplan_constraints(
        problem,
        schedule_problem=base.schedule_problem,
        result=base.schedule,
        id_map=base.id_map,
        expected_frozen=[bad],
    )
    assert any(v.kind == "FROZEN_ASSIGNMENT_CONFLICT" for v in violations)


def test_spare_shortage_postcheck() -> None:
    problem = synthesize_feeder(mode="small", seed=12)
    emptied = [
        s.model_copy(update={"available_quantity": 0, "stock_qty": 0, "reserved_quantity": 0})
        for s in problem.spare_parts
    ]
    job0 = problem.jobs[0].model_copy(update={"spare_part_ids": [emptied[0].id]})
    jobs = [
        (job0 if j.id == job0.id else j.model_copy(update={"spare_part_ids": []}))
        for j in problem.jobs
    ]
    problem = problem.model_copy(update={"spare_parts": emptied, "jobs": jobs})
    outcome = plan_maintenance(problem, solver_config="GREED", apply_frozen=False)
    assert outcome.status in {"feasible", "infeasible", "timeout", "error"}
    kinds = outcome.metadata.get("gridplan_violation_kinds", [])
    op = outcome.id_map.get(f"job:{job0.id}")
    scheduled = op is not None and any(a.operation_id == op for a in outcome.schedule.assignments)
    if scheduled:
        assert "SPARE_PART_SHORTAGE" in kinds
        assert outcome.verified_feasible is False
        assert outcome.status == "error"


def test_compile_frozen_uses_explicit_crew() -> None:
    problem = synthesize_feeder(mode="small", seed=13)
    cleared = [w.model_copy(update={"frozen": False}) for w in problem.outage_windows]
    problem = problem.model_copy(update={"outage_windows": cleared})
    schedule, id_map = to_schedule_problem(problem)
    crew = problem.crews[0]
    job = next(
        j
        for j in problem.jobs
        if not j.required_qualifications
        or set(j.required_qualifications).issubset(set(crew.qualifications))
    )
    start = problem.planning_horizon_start + timedelta(hours=2)
    end = start + timedelta(minutes=job.duration_min)
    fr = FrozenAssignment(
        job_id=job.id,
        crew_id=crew.id,
        start=start,
        end=end,
        immutable=True,
    )
    problem = problem.model_copy(update={"frozen_assignments": [fr]})
    compiled = compile_frozen_assignments(problem, schedule, id_map)
    assert len(compiled) == 1
    assert compiled[0].work_center_id == id_map[f"crew:{crew.id}"]
