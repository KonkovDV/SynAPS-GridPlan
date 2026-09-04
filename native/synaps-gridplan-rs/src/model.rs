//! Domain model — JSON-compatible with Python `synaps_gridplan.model` (gridplan.v1).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use uuid::Uuid;

use crate::SCHEMA_VERSION;

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
pub struct RiskProfile {
    #[serde(default)]
    pub probability_of_failure: f64,
    #[serde(default)]
    pub consequence_score: f64,
    #[serde(default)]
    pub criticality: Criticality,
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

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    pub service_area: String,
    #[serde(default)]
    pub risk: RiskProfile,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default)]
    pub domain_attributes: Value,
}

fn default_equipment() -> String {
    "equipment".into()
}
fn default_experiment() -> String {
    "experiment".into()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    pub shift_calendar: Vec<Value>,
    #[serde(default)]
    pub availability: Vec<Value>,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
    #[serde(default)]
    pub domain_attributes: Value,
}

fn default_one() -> i32 {
    1
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
}

impl SparePart {
    pub fn usable_quantity(&self) -> i32 {
        let avail = self.available_quantity.unwrap_or(self.stock_qty);
        (avail - self.reserved_quantity).max(0)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    pub eligible_crew_ids: Vec<Uuid>,
    #[serde(default)]
    pub safety_constraints: Vec<String>,
    #[serde(default)]
    pub interruption_required: bool,
    #[serde(default = "default_experiment")]
    pub data_provenance: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
        let asset_ids: std::collections::HashSet<_> = self.assets.iter().map(|a| a.id).collect();
        let crew_ids: std::collections::HashSet<_> = self.crews.iter().map(|c| c.id).collect();
        let job_ids: std::collections::HashSet<_> = self.jobs.iter().map(|j| j.id).collect();
        let spare_ids: std::collections::HashSet<_> =
            self.spare_parts.iter().map(|s| s.id).collect();
        let mut issues = Vec::new();
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
