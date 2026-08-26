"""Map GridPlanProblem → SynAPS ScheduleProblem without mutating SynAPS types."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from uuid import UUID, uuid5

from synaps.model import (
    Assignment,
    AuxiliaryResource,
    Operation,
    OperationAuxRequirement,
    Order,
    ScheduleProblem,
    SetupEntry,
    State,
    WorkCenter,
)

from synaps_gridplan.model import Asset, FrozenAssignment, GridPlanProblem, MaintenanceJob
from synaps_gridplan.risk import job_priority

_NS = UUID("0f1e2d3c-4b5a-6978-90ab-cdef01234567")


def _sid(*parts: str) -> UUID:
    return uuid5(_NS, "synaps-gridplan:" + ":".join(parts))


def _synaps_priority(job: MaintenanceJob, asset: Asset) -> int:
    """Explicit ``job.priority`` wins; otherwise the risk-derived SynAPS scale."""

    if job.priority is not None:
        return job.priority
    return job_priority(job, asset)


def _travel_key(from_loc: str, to_loc: str) -> str:
    return f"{from_loc}|{to_loc}"


def _lookup_travel_minutes(
    problem: GridPlanProblem,
    *,
    from_loc: str,
    to_loc: str,
    home: str,
) -> int:
    """Travel minutes for a state pair. Empty matrix means zero, not a phantom 30.

    A partial matrix missing ``from|to`` (and the home fallback) raises;
    an empty matrix is zero travel.
    """
    if from_loc == to_loc:
        return 0
    direct = problem.travel_minutes.get(_travel_key(from_loc, to_loc))
    if direct is not None:
        return int(direct)
    if from_loc == "idle":
        home_leg = problem.travel_minutes.get(_travel_key(home, to_loc))
        if home_leg is not None:
            return int(home_leg)
        if home == to_loc or not problem.travel_minutes:
            return 0
    if to_loc == "idle":
        return 0
    home_leg = problem.travel_minutes.get(_travel_key(home, to_loc))
    if home_leg is not None:
        return int(home_leg)
    if not problem.travel_minutes:
        return 0
    raise ValueError(f"travel_minutes missing for {from_loc}|{to_loc} (crew home {home})")


def _approved_outage_windows(job: MaintenanceJob, windows: list) -> list:
    return [
        window
        for window in windows
        if window.approved
        and job.id not in window.forbidden_job_ids
        and (not window.allowed_job_ids or job.id in window.allowed_job_ids)
    ]


def _job_clearance_bounds(job: MaintenanceJob, windows: list) -> tuple:
    """Hard per-op window. Due date is tardiness, not a finish ceiling.

    Interruption jobs use the earliest approved clearance. A union of windows
    would leave a gap the checker still treats as out-of-window.
    """
    allowed = _approved_outage_windows(job, windows)
    if job.interruption_required and allowed:
        chosen = min(allowed, key=lambda window: window.start)
        return chosen.start, chosen.end
    return job.release_date, job.latest_finish


def compile_frozen_assignments(
    problem: GridPlanProblem,
    schedule: ScheduleProblem,
    id_map: dict[str, UUID],
) -> list[Assignment]:
    """Compile explicit FrozenAssignment rows (preferred) plus legacy frozen windows."""

    ops_by_id = {op.id: op for op in schedule.operations}
    frozen: list[Assignment] = []
    seen_ops: set[UUID] = set()

    for fr in problem.frozen_assignments:
        op_id = id_map.get(f"job:{fr.job_id}")
        wc_id = id_map.get(f"crew:{fr.crew_id}")
        if op_id is None or wc_id is None:
            continue
        op = ops_by_id.get(op_id)
        if op is None:
            continue
        if wc_id not in op.eligible_wc_ids:
            # Still emit — feasibility / frozen conflict checks will surface ERROR.
            pass
        frozen.append(
            Assignment(
                operation_id=op_id,
                work_center_id=wc_id,
                start_time=fr.start,
                end_time=fr.end,
                setup_minutes=0,
            )
        )
        seen_ops.add(op_id)

    # Legacy path: frozen outage windows invent placements only when no explicit row.
    for asn in frozen_assignments_from_windows(problem, schedule, id_map):
        if asn.operation_id not in seen_ops:
            frozen.append(asn)
    return frozen


def frozen_assignments_from_windows(
    problem: GridPlanProblem,
    schedule: ScheduleProblem,
    id_map: dict[str, UUID],
) -> list[Assignment]:
    """Legacy helper: pin jobs on frozen windows to window.start + first eligible crew.

    Prefer explicit ``FrozenAssignment`` rows. This path is retained for v1 inputs.
    """

    windows = [w for w in problem.outage_windows if w.frozen]
    if not windows:
        return []

    jobs_by_asset: dict[UUID, list[MaintenanceJob]] = defaultdict(list)
    for job in problem.jobs:
        jobs_by_asset[job.asset_id].append(job)

    ops_by_id = {op.id: op for op in schedule.operations}
    frozen: list[Assignment] = []
    for window in windows:
        for job in jobs_by_asset.get(window.asset_id, []):
            op_id = id_map.get(f"job:{job.id}")
            if op_id is None:
                continue
            op = ops_by_id[op_id]
            if not op.eligible_wc_ids:
                continue
            start = window.start
            end = start + timedelta(minutes=op.base_duration_min)
            if end > window.end:
                continue
            frozen.append(
                Assignment(
                    operation_id=op_id,
                    work_center_id=op.eligible_wc_ids[0],
                    start_time=start,
                    end_time=end,
                    setup_minutes=0,
                )
            )
    return frozen


def extract_frozen_from_result(
    problem: GridPlanProblem,
    *,
    result_assignments: list[Assignment],
    id_map: dict[str, UUID],
    job_ids: list[UUID] | None = None,
    reason: str = "base_plan",
) -> list[FrozenAssignment]:
    """Build FrozenAssignment rows from a solved schedule (for subsequent repair)."""

    op_to_job = {id_map[f"job:{j.id}"]: j.id for j in problem.jobs if f"job:{j.id}" in id_map}
    wc_to_crew = {id_map[f"crew:{c.id}"]: c.id for c in problem.crews if f"crew:{c.id}" in id_map}
    wanted = set(job_ids) if job_ids is not None else None
    out: list[FrozenAssignment] = []
    for asn in result_assignments:
        job_id = op_to_job.get(asn.operation_id)
        crew_id = wc_to_crew.get(asn.work_center_id)
        if job_id is None or crew_id is None:
            continue
        if wanted is not None and job_id not in wanted:
            continue
        out.append(
            FrozenAssignment(
                job_id=job_id,
                crew_id=crew_id,
                start=asn.start_time,
                end=asn.end_time,
                source="solved_plan",
                frozen_reason=reason,
                immutable=True,
                data_provenance="experiment",
            )
        )
    return out


def to_schedule_problem(problem: GridPlanProblem) -> tuple[ScheduleProblem, dict[str, UUID]]:
    """Compile a GridPlan problem into a SynAPS schedule problem.

    Returns the schedule problem and an id map
    (``job:<uuid>`` → operation id, ``crew:<uuid>`` → work-center id, …).

    Cross-job precedence is compiled into a single SynAPS ``Order`` with
    sequenced operations — SynAPS forbids ``predecessor_op_id`` across orders.
    """

    id_map: dict[str, UUID] = {}
    assets_by_id = {asset.id: asset for asset in problem.assets}
    crews_by_id = {crew.id: crew for crew in problem.crews}

    location_codes = sorted(
        {
            *(asset.location_code or asset.code for asset in problem.assets),
            *(crew.home_location_code or crew.code for crew in problem.crews),
            "idle",
        }
    )
    states: list[State] = []
    state_by_loc: dict[str, UUID] = {}
    for loc in location_codes:
        state = State(id=_sid("state", loc), code=f"loc:{loc}", label=loc)
        states.append(state)
        state_by_loc[loc] = state.id
        id_map[f"state:{loc}"] = state.id

    work_centers: list[WorkCenter] = []
    for crew in problem.crews:
        wc = WorkCenter(
            id=_sid("crew", str(crew.id)),
            code=crew.code,
            capability_group=",".join(sorted(crew.qualifications)) or "general",
            max_parallel=crew.max_parallel,
            domain_attributes={
                "gridplan_crew_id": str(crew.id),
                "home_location_code": crew.home_location_code,
                "qualifications": list(crew.qualifications),
            },
        )
        work_centers.append(wc)
        id_map[f"crew:{crew.id}"] = wc.id

    spare_resources: list[AuxiliaryResource] = []
    # SynAPS AuxiliaryResource.pool_size is concurrent capacity, not stock.
    # Use usable stock when >0; pool_size minimum is 1 by SynAPS contract.
    # Consumable shortages are enforced by GridPlan post-checks.
    for spare in problem.spare_parts:
        usable = spare.usable_quantity
        pool = max(1, usable) if usable > 0 else 1
        aux = AuxiliaryResource(
            id=_sid("spare", str(spare.id)),
            code=spare.code,
            resource_type="spare_part",
            pool_size=pool,
            domain_attributes={
                "gridplan_spare_id": str(spare.id),
                "stock_qty": spare.stock_qty,
                "available_quantity": spare.available_quantity,
                "usable_quantity": usable,
                "unavailable": usable <= 0,
                "semantics": "concurrent_pool_proxy_consumable_postcheck",
            },
        )
        spare_resources.append(aux)
        id_map[f"spare:{spare.id}"] = aux.id

    skill_counts: dict[str, int] = {}
    for crew in problem.crews:
        for skill in crew.qualifications:
            skill_counts[skill] = skill_counts.get(skill, 0) + max(1, crew.max_parallel)
    skill_resources: list[AuxiliaryResource] = []
    for skill, count in sorted(skill_counts.items()):
        aux = AuxiliaryResource(
            id=_sid("skill", skill),
            code=f"skill:{skill}",
            resource_type="qualification",
            pool_size=max(1, count),
            domain_attributes={"skill": skill},
        )
        skill_resources.append(aux)
        id_map[f"skill:{skill}"] = aux.id

    windows_by_asset: dict[UUID, list] = defaultdict(list)
    for window in problem.outage_windows:
        windows_by_asset[window.asset_id].append(window)

    chains = _job_chains(problem.jobs)
    orders: list[Order] = []
    operations: list[Operation] = []
    aux_requirements: list[OperationAuxRequirement] = []

    for chain in chains:
        head = chain[0]
        priority = max(_synaps_priority(job, assets_by_id[job.asset_id]) for job in chain)

        release = head.release_date
        due = head.due_date
        union_starts: list = []
        union_ends: list = []
        for job in chain:
            earliest, latest = _job_clearance_bounds(job, windows_by_asset.get(job.asset_id, []))
            if earliest is not None:
                union_starts.append(earliest)
            if latest is not None:
                union_ends.append(latest)
        if union_starts:
            release = min(union_starts)
        if union_ends:
            due = max(union_ends)

        order = Order(
            id=_sid("order", *(str(job.id) for job in chain)),
            external_ref="+".join(job.external_ref for job in chain),
            release_date=release or problem.planning_horizon_start,
            due_date=due or problem.planning_horizon_end,
            priority=priority,
            domain_attributes={
                "gridplan_job_ids": [str(job.id) for job in chain],
                "chain_len": len(chain),
            },
        )
        orders.append(order)
        id_map[f"order:{head.id}"] = order.id

        prev_op_id: UUID | None = None
        for seq, job in enumerate(chain):
            job_asset = assets_by_id[job.asset_id]
            loc = job_asset.location_code or job_asset.code
            eligible = list(job.eligible_crew_ids) or _eligible_crews(job, problem)
            eligible_wc_ids = [id_map[f"crew:{crew_id}"] for crew_id in eligible]
            op_earliest, op_latest = _job_clearance_bounds(
                job, windows_by_asset.get(job.asset_id, [])
            )

            operation = Operation(
                id=_sid("job", str(job.id)),
                order_id=order.id,
                seq_in_order=seq,
                state_id=state_by_loc[loc],
                base_duration_min=job.duration_min,
                eligible_wc_ids=eligible_wc_ids,
                predecessor_op_id=prev_op_id,
                earliest_start=op_earliest,
                latest_finish=op_latest,
                domain_attributes={
                    "gridplan_job_id": str(job.id),
                    "location_code": loc,
                    "asset_code": job_asset.code,
                    "kind": job.kind.value,
                    "risk_score": (
                        job.risk_override.risk_score
                        if job.risk_override is not None
                        else job_asset.risk.risk_score
                    ),
                },
            )
            operations.append(operation)
            id_map[f"job:{job.id}"] = operation.id
            prev_op_id = operation.id

            for skill in job.required_qualifications:
                skill_key = f"skill:{skill}"
                if skill_key in id_map:
                    aux_requirements.append(
                        OperationAuxRequirement(
                            operation_id=operation.id,
                            aux_resource_id=id_map[skill_key],
                            quantity_needed=1,
                        )
                    )
            for spare_id in job.spare_part_ids:
                spare_key = f"spare:{spare_id}"
                if spare_key in id_map:
                    aux_requirements.append(
                        OperationAuxRequirement(
                            operation_id=operation.id,
                            aux_resource_id=id_map[spare_key],
                            # one stock unit per listed spare; BOM quantity is out of scope
                            quantity_needed=1,
                        )
                    )

    setup_matrix: list[SetupEntry] = []
    for wc in work_centers:
        crew_id = UUID(str(wc.domain_attributes["gridplan_crew_id"]))
        home = crews_by_id[crew_id].home_location_code or crews_by_id[crew_id].code
        for from_loc, from_state in state_by_loc.items():
            for to_loc, to_state in state_by_loc.items():
                if from_loc == to_loc:
                    minutes = 0
                else:
                    minutes = _lookup_travel_minutes(
                        problem, from_loc=from_loc, to_loc=to_loc, home=home
                    )
                setup_matrix.append(
                    SetupEntry(
                        id=_sid("setup", str(wc.id), str(from_state), str(to_state)),
                        work_center_id=wc.id,
                        from_state_id=from_state,
                        to_state_id=to_state,
                        setup_minutes=max(0, minutes),
                    )
                )

    schedule = ScheduleProblem(
        states=states,
        orders=orders,
        operations=operations,
        work_centers=work_centers,
        setup_matrix=setup_matrix,
        auxiliary_resources=spare_resources + skill_resources,
        aux_requirements=aux_requirements,
        planning_horizon_start=problem.planning_horizon_start,
        planning_horizon_end=problem.planning_horizon_end,
    )
    return schedule, id_map


def _job_chains(jobs: list[MaintenanceJob]) -> list[list[MaintenanceJob]]:
    """Partition jobs into predecessor chains (linear components only)."""

    by_id = {job.id: job for job in jobs}
    successors: dict[UUID, list[UUID]] = defaultdict(list)
    has_pred: set[UUID] = set()
    for job in jobs:
        for pred in job.predecessor_job_ids:
            if pred in by_id:
                successors[pred].append(job.id)
                has_pred.add(job.id)

    queue = [job.id for job in jobs if job.id not in has_pred]
    seen: set[UUID] = set()
    chains: list[list[MaintenanceJob]] = []
    deferred: list[UUID] = []

    while queue:
        job_id = queue.pop(0)
        if job_id in seen:
            continue
        chain: list[MaintenanceJob] = []
        cur: UUID | None = job_id
        while cur is not None and cur not in seen:
            chain.append(by_id[cur])
            seen.add(cur)
            nxt = successors.get(cur, [])
            if len(nxt) == 1:
                cur = nxt[0]
            else:
                for child in nxt:
                    if child not in seen:
                        deferred.append(child)
                cur = None
        chains.append(chain)

    queue.extend(deferred)
    while queue:
        job_id = queue.pop(0)
        if job_id in seen:
            continue
        chains.append([by_id[job_id]])
        seen.add(job_id)

    for job in jobs:
        if job.id not in seen:
            chains.append([job])
            seen.add(job.id)
    return chains


def _eligible_crews(job: MaintenanceJob, problem: GridPlanProblem) -> list[UUID]:
    required = set(job.required_qualifications)
    selected = [crew.id for crew in problem.crews if required.issubset(set(crew.qualifications))]
    if not selected and not required:
        return [crew.id for crew in problem.crews]
    return selected
