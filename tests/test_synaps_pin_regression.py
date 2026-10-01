"""ADR-0004 pin bump: fail-closed coverage and calendar encode on installed SynAPS."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from synaps.model import (
    Assignment,
    AuxiliaryResource,
    Operation,
    OperationAuxRequirement,
    Order,
    ScheduleProblem,
    ScheduleResult,
    SetupEntry,
    ShiftInterval,
    SolverStatus,
    State,
    WorkCenter,
)
from synaps.solvers.coverage_outcome import CoverageClass, process_exit_code, stamp_honest_coverage
from synaps.solvers.feasibility_checker import FeasibilityChecker
from synaps.solvers.registry import create_solver

from synaps_gridplan.versions import SYNAPS_COMMIT

H0 = datetime(2026, 4, 1, tzinfo=UTC)
HE = H0 + timedelta(hours=16)


def _one_op_problem(*, calendar: list[ShiftInterval]) -> ScheduleProblem:
    state = State(code="s")
    work_center = WorkCenter(code="M", capability_group="G", calendar=calendar)
    order = Order(external_ref="O", due_date=HE)
    operation = Operation(
        order_id=order.id,
        seq_in_order=1,
        state_id=state.id,
        base_duration_min=60,
        eligible_wc_ids=[work_center.id],
    )
    return ScheduleProblem(
        states=[state],
        orders=[order],
        operations=[operation],
        work_centers=[work_center],
        setup_matrix=[],
        planning_horizon_start=H0,
        planning_horizon_end=HE,
    )


def test_pin_is_residuals_kernel_sha() -> None:
    assert SYNAPS_COMMIT == "6178c93b705ff58be21fa74a98651883a2da1169"


def test_empty_feasible_stamps_error_and_exit_3() -> None:
    problem = _one_op_problem(calendar=[])
    stamped = stamp_honest_coverage(
        problem,
        ScheduleResult(solver_name="GREED", status=SolverStatus.FEASIBLE, assignments=[]),
    )
    assert stamped.status is SolverStatus.ERROR
    assert process_exit_code(stamped.status, CoverageClass.EMPTY) == 3


def test_process_exit_codes_match_adr_0005() -> None:
    assert process_exit_code(SolverStatus.FEASIBLE, CoverageClass.FULL) == 0
    assert process_exit_code(SolverStatus.FEASIBLE, CoverageClass.INCOMPLETE) == 2
    assert process_exit_code(SolverStatus.ERROR, CoverageClass.EMPTY) == 3
    assert process_exit_code(SolverStatus.ERROR, CoverageClass.INCOMPLETE) == 1


def test_cpsat_alns_lbbd_encode_nonempty_calendar() -> None:
    """Named exact/ALNS configs encode occupancy; they do not schedule 24/7."""

    problem = _one_op_problem(
        calendar=[ShiftInterval(start=H0 + timedelta(hours=8), end=HE)],
    )
    for name in ("CPSAT-10", "ALNS-300", "LBBD-5"):
        solver, kwargs = create_solver(name)
        result = solver.solve(problem, **kwargs, auto_greedy_warm_start=False)
        assert result.assignments, name
        assert result.assignments[0].start_time >= H0 + timedelta(hours=8), name
        assert not FeasibilityChecker().check(problem, result.assignments, exhaustive=True), name
        assert result.metadata.get("calendar_unsupported") is not True, name


def _violation_codes(violations: list) -> set[str]:
    codes: set[str] = set()
    for item in violations:
        code = getattr(item, "code", None) or getattr(item, "kind", None)
        if code:
            codes.add(str(code))
    return codes


def test_matrix_setup_occupies_aux_before_the_asset_job_starts() -> None:
    """Pinned engine charges an aux resource for setup-matrix minutes on every
    assignment after the first on that work center.

    Processing intervals only touch. The 30-minute approach still overlaps the
    other crew's hold on the same asset. An asset mutex of pool_size=1 would
    therefore treat travel as an outage, so GridPlan does not compile one.
    """

    depot = State(code="depot")
    site = State(code="site")
    traveler = WorkCenter(code="M", capability_group="G")
    other = WorkCenter(code="L", capability_group="G")
    order = Order(external_ref="O", release_date=H0, due_date=H0 + timedelta(hours=6))
    elsewhere = Operation(
        order_id=order.id,
        seq_in_order=1,
        state_id=depot.id,
        base_duration_min=30,
        eligible_wc_ids=[traveler.id],
    )
    arrival = Operation(
        order_id=order.id,
        seq_in_order=2,
        state_id=site.id,
        base_duration_min=60,
        eligible_wc_ids=[traveler.id],
    )
    resident = Operation(
        order_id=order.id,
        seq_in_order=3,
        state_id=site.id,
        base_duration_min=60,
        eligible_wc_ids=[other.id],
    )
    asset = AuxiliaryResource(code="ASSET", resource_type="asset", pool_size=1)
    start = H0 + timedelta(hours=1)
    problem = ScheduleProblem(
        states=[depot, site],
        orders=[order],
        operations=[elsewhere, arrival, resident],
        work_centers=[traveler, other],
        auxiliary_resources=[asset],
        aux_requirements=[
            OperationAuxRequirement(
                operation_id=arrival.id,
                aux_resource_id=asset.id,
                quantity_needed=1,
            ),
            OperationAuxRequirement(
                operation_id=resident.id,
                aux_resource_id=asset.id,
                quantity_needed=1,
            ),
        ],
        setup_matrix=[
            SetupEntry(
                work_center_id=traveler.id,
                from_state_id=depot.id,
                to_state_id=site.id,
                setup_minutes=30,
            )
        ],
        planning_horizon_start=H0,
        planning_horizon_end=H0 + timedelta(hours=6),
    )
    assignments = [
        Assignment(
            operation_id=elsewhere.id,
            work_center_id=traveler.id,
            start_time=start,
            end_time=start + timedelta(minutes=30),
            setup_minutes=0,
        ),
        Assignment(
            operation_id=arrival.id,
            work_center_id=traveler.id,
            start_time=start + timedelta(minutes=60),
            end_time=start + timedelta(minutes=120),
            setup_minutes=30,
        ),
        Assignment(
            operation_id=resident.id,
            work_center_id=other.id,
            start_time=start,
            end_time=start + timedelta(minutes=60),
            setup_minutes=0,
        ),
    ]
    codes = _violation_codes(FeasibilityChecker().check(problem, assignments, exhaustive=True))
    assert "AUX_RESOURCE_CAPACITY_VIOLATION" in codes
    assert "MACHINE_OVERLAP" not in codes
