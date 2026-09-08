//! Domain model — JSON-compatible with Python `synaps_gridplan.model` (gridplan.v1).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, HashSet};
use uuid::Uuid;

use crate::SCHEMA_VERSION;

pub const MAX_JSON_BYTES: u64 = 32 * 1024 * 1024;
const MAX_ASSETS: usize = 20_000;
const MAX_CREWS: usize = 5_000;
const MAX_JOBS: usize = 20_000;
const MAX_WINDOWS: usize = 50_000;
const MAX_SPARES: usize = 20_000;
const MAX_FROZEN: usize = 20_000;
const MAX_BANS: usize = 50_000;
const MAX_TRAVEL_ENTRIES: usize = 2_000_000;
const MAX_CALENDAR_ROWS: usize = 10_000;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
#[serde(rename_all = "lowercase")]
pub enum Criticality {
    Low,
    #[default]
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
#[serde(rename_all = "lowercase")]
pub enum JobKind {
    #[default]
    Preventive,
    Corrective,
    Inspection,
    Emergency,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RiskProfile {
    #[serde(default)]
    pub probability_of_failure: f64,
    #[serde(default)]
    pub consequence_score: f64,
    #[serde(default)]
    pub criticality: Criticality,
    #[serde(default)]
    pub assessment_timestamp: Option<DateTime<Utc>>,
    #[serde(default)]
    pub assessment_method: String,
    #[serde(default)]
    pub confidence: f64,
    #[serde(default)]
    pub source_ref: String,
    #[serde(default = "default_true")]
    pub is_advisory: bool,
}

impl Default for RiskProfile {
    fn default() -> Self {
        Self {
            probability_of_failure: 0.0,
            consequence_score: 0.0,
            criticality: Criticality::Medium,
            assessment_timestamp: None,
            assessment_method: "unspecified".into(),
            confidence: 0.0,
            source_ref: String::new(),
            is_advisory: true,
        }
    }
}

fn default_true() -> bool {
    true
}

fn default_object() -> Value {
    serde_json::json!({})
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FailureMode {
    #[serde(default)]
    pub id: Uuid,
    pub code: String,
    #[serde(default)]
    pub label: String,
    #[serde(default)]
    pub probability_of_failure: f64,
    #[serde(default)]
    pub consequence_score: f64,
    #[serde(default = "default_object")]
    pub domain_attributes: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Asset {
    pub id: Uuid,
    #[serde(default)]
    pub external_ref: String,
    pub code: String,
    #[serde(default)]
    pub name: String,
    #[serde(default = "default_equipment")]
    pub asset_class: String,
    #[serde(default)]
    pub voltage_level: String,
    #[serde(default)]
    pub location_code: String,
    #[serde(default)]
    pub parent_asset_id: Option<Uuid>,
    #[serde(default)]
    pub service_area: String,
    #[serde(default)]
    pub coordinates: Option<BTreeMap<String, f64>>,
    #[serde(default)]
    pub risk: RiskProfile,
    #[serde(default)]
    pub failure_modes: Vec<FailureMode>,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default = "default_object")]
    pub domain_attributes: Value,
}

fn default_equipment() -> String {
    "equipment".into()
}
fn default_experiment() -> String {
    "experiment".into()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CrewCalendarWindow {
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Crew {
    pub id: Uuid,
    pub code: String,
    #[serde(default)]
    pub qualifications: Vec<String>,
    #[serde(default = "default_one")]
    pub max_parallel: i32,
    #[serde(default)]
    pub home_location_code: String,
    #[serde(default)]
    pub service_area: String,
    #[serde(default)]
    pub shift_calendar: Vec<CrewCalendarWindow>,
    #[serde(default)]
    pub availability: Vec<CrewCalendarWindow>,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default = "default_object")]
    pub domain_attributes: Value,
}

fn default_one() -> i32 {
    1
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SparePart {
    pub id: Uuid,
    pub code: String,
    #[serde(default)]
    pub stock_qty: i32,
    #[serde(default)]
    pub available_quantity: Option<i32>,
    #[serde(default)]
    pub reserved_quantity: i32,
    #[serde(default)]
    pub replenishment_date: Option<DateTime<Utc>>,
    #[serde(default)]
    pub lead_time_min: i32,
    #[serde(default)]
    pub warehouse_location: String,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default = "default_object")]
    pub domain_attributes: Value,
}

impl SparePart {
    pub fn usable_quantity(&self) -> i32 {
        let avail = self.available_quantity.unwrap_or(self.stock_qty);
        if self.stock_qty < 0 || avail < 0 || self.reserved_quantity < 0 {
            return 0;
        }
        avail.saturating_sub(self.reserved_quantity).max(0)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OutageWindow {
    pub id: Uuid,
    pub asset_id: Uuid,
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
    #[serde(default = "default_true")]
    pub approved: bool,
    #[serde(default)]
    pub frozen: bool,
    #[serde(default)]
    pub allowed_job_ids: Vec<Uuid>,
    #[serde(default)]
    pub forbidden_job_ids: Vec<Uuid>,
    #[serde(default)]
    pub external_ref: String,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default = "default_object")]
    pub domain_attributes: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MaintenanceJob {
    pub id: Uuid,
    pub external_ref: String,
    pub asset_id: Uuid,
    #[serde(default)]
    pub kind: JobKind,
    pub duration_min: i32,
    #[serde(default)]
    pub required_qualifications: Vec<String>,
    #[serde(default)]
    pub spare_part_ids: Vec<Uuid>,
    #[serde(default)]
    pub predecessor_job_ids: Vec<Uuid>,
    #[serde(default)]
    pub due_date: Option<DateTime<Utc>>,
    #[serde(default)]
    pub release_date: Option<DateTime<Utc>>,
    #[serde(default)]
    pub latest_finish: Option<DateTime<Utc>>,
    #[serde(default)]
    pub priority: Option<i32>,
    #[serde(default)]
    pub eligible_crew_ids: Vec<Uuid>,
    #[serde(default)]
    pub safety_constraints: Vec<String>,
    #[serde(default)]
    pub interruption_required: bool,
    #[serde(default)]
    pub risk_override: Option<RiskProfile>,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default = "default_object")]
    pub domain_attributes: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FrozenAssignment {
    pub job_id: Uuid,
    pub crew_id: Uuid,
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
    #[serde(default = "default_base_plan")]
    pub source: String,
    #[serde(default)]
    pub frozen_reason: String,
    #[serde(default = "default_true")]
    pub immutable: bool,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
}

fn default_base_plan() -> String {
    "base_plan".into()
}

/// Customer-declared anti-coincidence of interruption occupancy.
/// Combinatorial mutex (not N-1 / power-flow). Occupancy uses the Goel hull.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SimultaneousOutageBan {
    pub id: Uuid,
    pub asset_id_a: Uuid,
    pub asset_id_b: Uuid,
    #[serde(default)]
    pub reason: String,
    #[serde(default)]
    pub external_ref: String,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default = "default_object")]
    pub domain_attributes: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GridPlanProblem {
    #[serde(default = "default_schema")]
    pub schema_version: String,
    pub assets: Vec<Asset>,
    pub crews: Vec<Crew>,
    pub jobs: Vec<MaintenanceJob>,
    #[serde(default)]
    pub outage_windows: Vec<OutageWindow>,
    #[serde(default)]
    pub spare_parts: Vec<SparePart>,
    #[serde(default)]
    pub frozen_assignments: Vec<FrozenAssignment>,
    #[serde(default)]
    pub simultaneous_outage_bans: Vec<SimultaneousOutageBan>,
    #[serde(default)]
    pub travel_minutes: std::collections::BTreeMap<String, i32>,
    pub planning_horizon_start: DateTime<Utc>,
    pub planning_horizon_end: DateTime<Utc>,
    #[serde(default)]
    pub domain_attributes: Value,
}

fn default_schema() -> String {
    SCHEMA_VERSION.to_string()
}

impl GridPlanProblem {
    pub fn validate_refs(&self) -> Result<(), String> {
        let asset_ids: HashSet<_> = self.assets.iter().map(|a| a.id).collect();
        let crew_ids: HashSet<_> = self.crews.iter().map(|c| c.id).collect();
        let job_ids: HashSet<_> = self.jobs.iter().map(|j| j.id).collect();
        let spare_ids: HashSet<_> = self.spare_parts.iter().map(|s| s.id).collect();
        let window_ids: HashSet<_> = self.outage_windows.iter().map(|w| w.id).collect();
        let ban_ids: HashSet<_> = self.simultaneous_outage_bans.iter().map(|b| b.id).collect();
        let frozen_ids: HashSet<_> = self.frozen_assignments.iter().map(|f| f.job_id).collect();
        let mut issues = Vec::new();
        if !matches!(self.schema_version.as_str(), "gridplan.v1" | "gridplan.v2") {
            issues.push(format!(
                "unsupported schema_version {}",
                self.schema_version
            ));
        }
        for (kind, total, unique) in [
            ("asset", self.assets.len(), asset_ids.len()),
            ("crew", self.crews.len(), crew_ids.len()),
            ("job", self.jobs.len(), job_ids.len()),
            ("spare", self.spare_parts.len(), spare_ids.len()),
            ("outage window", self.outage_windows.len(), window_ids.len()),
            (
                "outage ban",
                self.simultaneous_outage_bans.len(),
                ban_ids.len(),
            ),
            (
                "frozen job",
                self.frozen_assignments.len(),
                frozen_ids.len(),
            ),
        ] {
            if total != unique {
                issues.push(format!("duplicate {kind} id"));
            }
        }
        for asset in &self.assets {
            for value in [
                asset.risk.probability_of_failure,
                asset.risk.consequence_score,
                asset.risk.confidence,
            ] {
                if !value.is_finite() || !(0.0..=1.0).contains(&value) {
                    issues.push(format!("asset {} invalid risk value", asset.code));
                }
            }
        }
        for crew in &self.crews {
            if crew.max_parallel < 1 {
                issues.push(format!("crew {} invalid max_parallel", crew.code));
            }
            validate_calendar_rows(
                &crew.shift_calendar,
                &crew.code,
                "shift_calendar",
                &mut issues,
            );
            validate_calendar_rows(&crew.availability, &crew.code, "availability", &mut issues);
        }
        for (kind, total, limit) in [
            ("assets", self.assets.len(), MAX_ASSETS),
            ("crews", self.crews.len(), MAX_CREWS),
            ("jobs", self.jobs.len(), MAX_JOBS),
            ("outage windows", self.outage_windows.len(), MAX_WINDOWS),
            ("spares", self.spare_parts.len(), MAX_SPARES),
            ("frozen jobs", self.frozen_assignments.len(), MAX_FROZEN),
            ("outage bans", self.simultaneous_outage_bans.len(), MAX_BANS),
            (
                "travel entries",
                self.travel_minutes.len(),
                MAX_TRAVEL_ENTRIES,
            ),
        ] {
            if total > limit {
                issues.push(format!("{kind} count {total} exceeds lab limit {limit}"));
            }
        }
        for spare in &self.spare_parts {
            let available = spare.available_quantity.unwrap_or(spare.stock_qty);
            if spare.stock_qty < 0
                || available < 0
                || spare.reserved_quantity < 0
                || spare.reserved_quantity > available
            {
                issues.push(format!("spare {} invalid quantities", spare.code));
            }
        }
        if self.travel_minutes.values().any(|minutes| *minutes < 0) {
            issues.push("negative travel_minutes".into());
        }
        for job in &self.jobs {
            if !asset_ids.contains(&job.asset_id) {
                issues.push(format!("job {} unknown asset", job.external_ref));
            }
            if job.duration_min < 1 {
                issues.push(format!("job {} non-positive duration", job.external_ref));
            }
            for sid in &job.spare_part_ids {
                if !spare_ids.contains(sid) {
                    issues.push(format!("job {} unknown spare", job.external_ref));
                }
            }
            for pred in &job.predecessor_job_ids {
                if !job_ids.contains(pred) {
                    issues.push(format!("job {} unknown predecessor", job.external_ref));
                }
            }
            for cid in &job.eligible_crew_ids {
                if !crew_ids.contains(cid) {
                    issues.push(format!("job {} unknown crew", job.external_ref));
                }
            }
        }
        for window in &self.outage_windows {
            if !asset_ids.contains(&window.asset_id) {
                issues.push("outage window unknown asset".into());
            }
            if window.end <= window.start {
                issues.push("outage window invalid interval".into());
            }
            for id in window
                .allowed_job_ids
                .iter()
                .chain(&window.forbidden_job_ids)
            {
                if !job_ids.contains(id) {
                    issues.push("outage window unknown job".into());
                }
            }
        }
        for fr in &self.frozen_assignments {
            if !job_ids.contains(&fr.job_id) {
                issues.push("frozen unknown job".into());
            }
            if !crew_ids.contains(&fr.crew_id) {
                issues.push("frozen unknown crew".into());
            }
            if fr.end <= fr.start {
                issues.push("frozen invalid interval".into());
            }
        }
        for ban in &self.simultaneous_outage_bans {
            if !asset_ids.contains(&ban.asset_id_a) || !asset_ids.contains(&ban.asset_id_b) {
                issues.push("outage ban unknown asset".into());
            }
            if ban.asset_id_a == ban.asset_id_b {
                issues.push("outage ban requires distinct assets".into());
            }
        }
        if self.planning_horizon_end <= self.planning_horizon_start {
            issues.push("invalid planning horizon".into());
        }
        if issues.is_empty() {
            Ok(())
        } else {
            Err(issues[..issues.len().min(20)].join("; "))
        }
    }
}

fn validate_calendar_rows(
    rows: &[CrewCalendarWindow],
    crew: &str,
    name: &str,
    issues: &mut Vec<String>,
) {
    if rows.len() > MAX_CALENDAR_ROWS {
        issues.push(format!(
            "crew {crew} {name} exceeds {MAX_CALENDAR_ROWS} rows"
        ));
        return;
    }
    for (index, row) in rows.iter().enumerate() {
        if row.end <= row.start {
            issues.push(format!(
                "crew {crew} {name}[{index}] needs RFC3339 start/end with offset"
            ));
        }
    }
}
