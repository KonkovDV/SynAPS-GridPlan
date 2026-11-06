"""Crews the search may use, and the same predicate the domain checker repeats.

Qualifications stay the pool. A non-empty ``safety_constraints`` list must sit
in the union of ``qualifications`` and the string entries of
``domain_attributes.safety_clearances``. A non-string clearance is not a
clearance. Service areas constrain the crew only when both strings are set.
When that filter would leave nobody, the previous pool is kept: the pinned
engine reads an empty ``eligible_wc_ids`` as every work center. The checker
still rejects a crew the predicate does not accept.
"""

from __future__ import annotations

from uuid import UUID

from synaps_gridplan.model import Asset, Crew, GridPlanProblem, MaintenanceJob


def qualification_crew_ids(job: MaintenanceJob, problem: GridPlanProblem) -> list[UUID]:
    required = set(job.required_qualifications)
    selected = [crew.id for crew in problem.crews if required.issubset(set(crew.qualifications))]
    if not selected and not required:
        return [crew.id for crew in problem.crews]
    return selected


def clearance_strings(crew: Crew) -> set[str]:
    extra = crew.domain_attributes or {}
    listed = extra.get("safety_clearances", [])
    if not isinstance(listed, list):
        return set()
    return {item for item in listed if isinstance(item, str)}


def covers_safety(job: MaintenanceJob, crew: Crew) -> bool:
    required = set(job.safety_constraints)
    if not required:
        return True
    return required.issubset(set(crew.qualifications) | clearance_strings(crew))


def covers_service_area(crew: Crew, asset: Asset | None) -> bool:
    if asset is None:
        return True
    asset_area = asset.service_area or ""
    crew_area = crew.service_area or ""
    if not asset_area or not crew_area:
        return True
    return asset_area == crew_area


def crews_for_search(job: MaintenanceJob, problem: GridPlanProblem) -> list[UUID]:
    """Crews handed to the solver.

    An explicit ``eligible_crew_ids`` list is the pool. Otherwise the pool is
    the qualification rule. Crews that fail safety or service area drop out
    when at least one crew in the pool still passes.
    """

    by_id = {crew.id: crew for crew in problem.crews}
    asset = next((item for item in problem.assets if item.id == job.asset_id), None)
    if job.eligible_crew_ids:
        pool = [crew_id for crew_id in job.eligible_crew_ids if crew_id in by_id]
    else:
        pool = [crew_id for crew_id in qualification_crew_ids(job, problem) if crew_id in by_id]
    legal = [
        crew_id
        for crew_id in pool
        if covers_safety(job, by_id[crew_id]) and covers_service_area(by_id[crew_id], asset)
    ]
    return legal if legal else pool
