//! Schedule result types for the native contour (job/crew domain IDs).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::constraints::Violation;
use crate::CLAIM_LEVEL;
use crate::VERSION;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Assignment {
    pub job_id: Uuid,
    pub crew_id: Uuid,
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
    #[serde(default)]
    pub setup_minutes: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObjectiveSnapshot {
    pub makespan_minutes: f64,
    pub total_tardiness_minutes: f64,
    pub coverage: f64,
    pub unscheduled_operations: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanResult {
    pub schema_version: String,
    pub solver_config: String,
    pub status: String,
    pub claim_status: String,
    pub verified_feasible: bool,
    pub hard_violation_count: usize,
    pub assignments: Vec<Assignment>,
    pub objective: ObjectiveSnapshot,
    pub violations: Vec<Violation>,
    pub metadata: Value,
}

impl PlanResult {
    pub fn ok(&self) -> bool {
        self.verified_feasible && matches!(self.status.as_str(), "feasible" | "optimal")
    }

    pub fn with_claim_defaults(mut self) -> Self {
        if self.metadata.get("claim_level").is_none() {
            self.metadata["claim_level"] = json!(CLAIM_LEVEL);
        }
        if self.metadata.get("gridplan_rs_version").is_none() {
            self.metadata["gridplan_rs_version"] = json!(VERSION);
        }
        if self.metadata.get("data_provenance").is_none() {
            self.metadata["data_provenance"] = json!("synthetic");
        }
        self
    }
}
