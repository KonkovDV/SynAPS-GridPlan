"""Domain model for grid maintenance planning (schema versions 1 and 2)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "gridplan.v1"
SCHEMA_VERSION_V2 = "gridplan.v2"

DataProvenance = Literal[
    "synthetic",
    "open_data",
    "customer_data",
    "experiment",
    "production_verified",
]
ClaimLevel = Literal["experiment", "benchmark", "pilot_candidate", "production_verified"]


class Criticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobKind(StrEnum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    INSPECTION = "inspection"
    EMERGENCY = "emergency"


class FailureMode(BaseModel):
    """Failure mode with advisory probability — never an engineering certificate."""

    id: UUID = Field(default_factory=uuid4)
    code: str
    label: str = ""
    probability_of_failure: float = Field(ge=0.0, le=1.0, default=0.0)
    consequence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    domain_attributes: dict[str, Any] = Field(default_factory=dict)


class RiskProfile(BaseModel):
    """Composite risk proxy used for prioritisation / reporting (advisory)."""

    probability_of_failure: float = Field(ge=0.0, le=1.0, default=0.0)
    consequence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    criticality: Criticality = Criticality.MEDIUM
    assessment_timestamp: datetime | None = None
    assessment_method: str = "unspecified"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    source_ref: str = ""
    is_advisory: bool = True

    @property
    def risk_score(self) -> float:
        """PoF × consequence scaled by criticality weight (deterministic proxy)."""
        weights = {
            Criticality.LOW: 0.5,
            Criticality.MEDIUM: 1.0,
            Criticality.HIGH: 1.5,
            Criticality.CRITICAL: 2.0,
        }
        return self.probability_of_failure * self.consequence_score * weights[self.criticality]


class Asset(BaseModel):
    """Energetic asset / equipment unit (GridAsset alias fields optional for v2)."""

    id: UUID = Field(default_factory=uuid4)
    external_ref: str = ""
    code: str
    name: str = ""
    asset_class: str = "equipment"
    voltage_level: str = ""
    location_code: str = ""
    parent_asset_id: UUID | None = None
    service_area: str = ""
    coordinates: dict[str, float] | None = None
    risk: RiskProfile = Field(default_factory=RiskProfile)
    failure_modes: list[FailureMode] = Field(default_factory=list)
    data_provenance: DataProvenance | str = "experiment"
    domain_attributes: dict[str, Any] = Field(default_factory=dict)

    @property
    def criticality(self) -> Criticality:
        return self.risk.criticality


class Crew(BaseModel):
    """Field crew / work center with qualifications."""

    id: UUID = Field(default_factory=uuid4)
    code: str
    qualifications: list[str] = Field(default_factory=list)
    max_parallel: int = Field(default=1, ge=1)
    home_location_code: str = ""
    shift_calendar: list[dict[str, Any]] = Field(default_factory=list)
    service_area: str = ""
    availability: list[dict[str, Any]] = Field(default_factory=list)
    data_provenance: DataProvenance | str = "experiment"
    domain_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_calendars(self) -> Self:
        for name, rows in (
            ("shift_calendar", self.shift_calendar),
            ("availability", self.availability),
        ):
            for index, row in enumerate(rows):
                if not isinstance(row, dict) or "start" not in row or "end" not in row:
                    raise ValueError(f"crew {self.code}: {name}[{index}] must have start and end")
        return self


class SparePart(BaseModel):
    """Spare part stock.

    Semantic note: SynAPS ``AuxiliaryResource.pool_size`` models *concurrent*
    capacity. Consumable stock accounting is enforced by GridPlan post-checks
    using ``available_quantity`` / ``reserved_quantity``.
    """

    id: UUID = Field(default_factory=uuid4)
    code: str
    stock_qty: int = Field(default=0, ge=0, description="legacy alias of available_quantity")
    available_quantity: int | None = Field(default=None, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    replenishment_date: datetime | None = None
    lead_time_min: int = Field(default=0, ge=0)
    warehouse_location: str = ""
    data_provenance: DataProvenance | str = "experiment"
    domain_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _sync_qty(self) -> Self:
        if self.available_quantity is None:
            object.__setattr__(self, "available_quantity", self.stock_qty)
        else:
            object.__setattr__(self, "stock_qty", self.available_quantity)
        if self.reserved_quantity > (self.available_quantity or 0):
            raise ValueError(f"spare {self.code}: reserved_quantity exceeds available")
        return self

    @property
    def usable_quantity(self) -> int:
        return max(0, (self.available_quantity or 0) - self.reserved_quantity)


class OutageWindow(BaseModel):
    """Allowed outage / clearance interval for an asset."""

    id: UUID = Field(default_factory=uuid4)
    asset_id: UUID
    start: datetime
    end: datetime
    approved: bool = True
    frozen: bool = False
    allowed_job_ids: list[UUID] = Field(default_factory=list)
    forbidden_job_ids: list[UUID] = Field(default_factory=list)
    external_ref: str = ""
    data_provenance: DataProvenance | str = "experiment"
    domain_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_interval(self) -> Self:
        if self.end <= self.start:
            raise ValueError("outage window end must be after start")
        return self


class MaintenanceJob(BaseModel):
    """One maintenance / repair work item."""

    id: UUID = Field(default_factory=uuid4)
    external_ref: str
    asset_id: UUID
    kind: JobKind = JobKind.PREVENTIVE
    duration_min: int = Field(ge=1)
    required_qualifications: list[str] = Field(default_factory=list)
    spare_part_ids: list[UUID] = Field(default_factory=list)
    predecessor_job_ids: list[UUID] = Field(default_factory=list)
    due_date: datetime | None = None
    release_date: datetime | None = None
    latest_finish: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=999)
    interruption_required: bool = False
    safety_constraints: list[str] = Field(default_factory=list)
    eligible_crew_ids: list[UUID] = Field(default_factory=list)
    risk_override: RiskProfile | None = None
    data_provenance: DataProvenance | str = "experiment"
    domain_attributes: dict[str, Any] = Field(default_factory=dict)


class FrozenAssignment(BaseModel):
    """Immutable job placement that must survive replan when ``immutable``."""

    job_id: UUID
    crew_id: UUID
    start: datetime
    end: datetime
    source: str = "base_plan"
    frozen_reason: str = ""
    immutable: bool = True
    data_provenance: DataProvenance | str = "experiment"


class DisruptionEvent(BaseModel):
    """External change triggering local repair."""

    id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime
    affected_asset_ids: list[UUID] = Field(default_factory=list)
    affected_job_ids: list[UUID] = Field(default_factory=list)
    unavailable_crew_ids: list[UUID] = Field(default_factory=list)
    unavailable_spare_ids: list[UUID] = Field(default_factory=list)
    severity: str = "medium"
    data_provenance: DataProvenance | str = "experiment"
    domain_attributes: dict[str, Any] = Field(default_factory=dict)


class SimultaneousOutageBan(BaseModel):
    """Explicit customer-declared ban on overlapping interruption occupancy.

    Combinatorial ``network_constraints`` — NOT N-1 / power-flow / topology.
    Occupancy of a precedence-connected interruption chain is the hull
    [first start, last end] (Goel et al., EJOR 2013: downtime from disconnect
    to reconnect). Independent interruption jobs (no precedence) stay separate.
    """

    id: UUID = Field(default_factory=uuid4)
    asset_id_a: UUID
    asset_id_b: UUID
    reason: str = ""
    external_ref: str = ""
    data_provenance: DataProvenance | str = "experiment"
    domain_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _distinct_assets(self) -> Self:
        if self.asset_id_a == self.asset_id_b:
            raise ValueError("simultaneous outage ban requires two distinct assets")
        return self


class GridPlanProblem(BaseModel):
    """Complete GridPlan input (schema gridplan.v1 compatible; v2 fields optional)."""

    schema_version: str = SCHEMA_VERSION
    assets: list[Asset]
    crews: list[Crew]
    jobs: list[MaintenanceJob]
    outage_windows: list[OutageWindow] = Field(default_factory=list)
    spare_parts: list[SparePart] = Field(default_factory=list)
    frozen_assignments: list[FrozenAssignment] = Field(default_factory=list)
    simultaneous_outage_bans: list[SimultaneousOutageBan] = Field(
        default_factory=list,
        description=(
            "network_constraints: explicit anti-coincidence of interruption jobs. "
            "Not N-1 / load-flow."
        ),
    )
    travel_minutes: dict[str, int] = Field(
        default_factory=dict,
        description="key = '{from_location}|{to_location}' → setup minutes",
    )
    planning_horizon_start: datetime
    planning_horizon_end: datetime
    domain_attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _cross_refs(self) -> Self:
        asset_ids = {a.id for a in self.assets}
        crew_ids = {c.id for c in self.crews}
        job_ids = {j.id for j in self.jobs}
        spare_ids = {s.id for s in self.spare_parts}
        issues: list[str] = []
        for job in self.jobs:
            if job.asset_id not in asset_ids:
                issues.append(f"job {job.external_ref} references unknown asset")
            for crew_id in job.eligible_crew_ids:
                if crew_id not in crew_ids:
                    issues.append(f"job {job.external_ref} references unknown crew {crew_id}")
            for pred in job.predecessor_job_ids:
                if pred not in job_ids:
                    issues.append(f"job {job.external_ref} references unknown predecessor")
            for spare_id in job.spare_part_ids:
                if spare_id not in spare_ids:
                    issues.append(f"job {job.external_ref} references unknown spare {spare_id}")
            if job.duration_min < 1:
                issues.append(f"job {job.external_ref} has non-positive duration")
        for window in self.outage_windows:
            if window.asset_id not in asset_ids:
                issues.append(f"outage window references unknown asset {window.asset_id}")
            for jid in window.allowed_job_ids + window.forbidden_job_ids:
                if jid not in job_ids:
                    issues.append(f"outage window references unknown job {jid}")
        for fr in self.frozen_assignments:
            if fr.job_id not in job_ids:
                issues.append(f"frozen assignment references unknown job {fr.job_id}")
            if fr.crew_id not in crew_ids:
                issues.append(f"frozen assignment references unknown crew {fr.crew_id}")
            if fr.end <= fr.start:
                issues.append(f"frozen assignment for {fr.job_id} has invalid interval")
        for ban in self.simultaneous_outage_bans:
            if ban.asset_id_a not in asset_ids or ban.asset_id_b not in asset_ids:
                issues.append(
                    f"simultaneous outage ban {ban.external_ref or ban.id} references unknown asset"
                )
        if self.planning_horizon_end <= self.planning_horizon_start:
            issues.append("planning horizon end must be after start")
        if issues:
            raise ValueError("; ".join(issues[:20]))
        return self
