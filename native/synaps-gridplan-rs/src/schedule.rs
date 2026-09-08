//! Schedule result types for the native contour (job/crew domain IDs).

use std::collections::{HashMap, HashSet};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::constraints::Violation;
use crate::model::FrozenAssignment;
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
        self.verified_feasible
            && matches!(self.status.as_str(), "feasible" | "optimal")
            && self.hard_violation_count == 0
            && self.violations.is_empty()
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

fn parse_dt(raw: &str) -> Result<DateTime<Utc>, String> {
    DateTime::parse_from_rfc3339(raw)
        .map(|dt| dt.with_timezone(&Utc))
        .map_err(|e| format!("datetime {raw}: {e}"))
}

fn uuid_field(item: &Value, key: &str) -> Result<Uuid, String> {
    item.get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("assignment missing {key}"))?
        .parse()
        .map_err(|e| format!("{key}: {e}"))
}

type OpToJob = HashMap<Uuid, Uuid>;
type WcToCrew = HashMap<Uuid, Uuid>;

/// Invert Python ``outcome.id_map`` (`job:{uuid}` / `crew:{uuid}` → SynAPS ids).
pub fn invert_python_id_map(id_map: &Value) -> Result<(OpToJob, WcToCrew), String> {
    let obj = id_map
        .as_object()
        .ok_or_else(|| "id_map must be an object".to_string())?;
    let mut op_to_job = HashMap::new();
    let mut wc_to_crew = HashMap::new();
    let mut job_ids = HashSet::new();
    let mut crew_ids = HashSet::new();
    for (key, value) in obj {
        let mapped: Uuid = value
            .as_str()
            .ok_or_else(|| format!("id_map[{key}] not a string"))?
            .parse()
            .map_err(|e| format!("id_map[{key}]: {e}"))?;
        if let Some(rest) = key.strip_prefix("job:") {
            let job: Uuid = rest.parse().map_err(|e| format!("job key {key}: {e}"))?;
            if !job_ids.insert(job) || op_to_job.insert(mapped, job).is_some() {
                return Err(format!("duplicate job/operation mapping: {key}"));
            }
        } else if let Some(rest) = key.strip_prefix("crew:") {
            let crew: Uuid = rest.parse().map_err(|e| format!("crew key {key}: {e}"))?;
            if !crew_ids.insert(crew) || wc_to_crew.insert(mapped, crew).is_some() {
                return Err(format!("duplicate crew/work-center mapping: {key}"));
            }
        }
    }
    Ok((op_to_job, wc_to_crew))
}

/// Missing freeze is optional; malformed or contradictory structure is not.
pub fn frozen_from_payload(root: &Value) -> Result<Vec<FrozenAssignment>, String> {
    let Some(outcome) = root.get("outcome") else {
        return Ok(vec![]);
    };
    let outcome = outcome
        .as_object()
        .ok_or_else(|| "outcome must be an object".to_string())?;
    let rows: Vec<FrozenAssignment> = outcome
        .get("frozen_assignments")
        .map(|value| serde_json::from_value(value.clone()))
        .transpose()
        .map_err(|e| format!("invalid outcome.frozen_assignments: {e}"))?
        .unwrap_or_default();
    let mut seen = HashSet::new();
    for row in &rows {
        if row.end <= row.start || !seen.insert(row.job_id) {
            return Err("invalid or duplicate outcome.frozen_assignments row".into());
        }
    }
    Ok(rows)
}

/// Map Python CLI solve JSON (`operation_id` + `id_map`) onto native assignments.
pub fn assignments_from_python_cli(
    root: &Value,
) -> Result<(Vec<Assignment>, Vec<FrozenAssignment>), String> {
    let id_map = root
        .pointer("/outcome/id_map")
        .ok_or_else(|| "Python CLI JSON missing outcome.id_map".to_string())?;
    let (op_to_job, wc_to_crew) = invert_python_id_map(id_map)?;
    let arr = root
        .pointer("/schedule/assignments")
        .and_then(Value::as_array)
        .ok_or_else(|| "Python CLI JSON missing schedule.assignments".to_string())?;
    let mut out = Vec::with_capacity(arr.len());
    for item in arr {
        let op_id = uuid_field(item, "operation_id")?;
        let wc_id = uuid_field(item, "work_center_id")?;
        let job_id = *op_to_job
            .get(&op_id)
            .ok_or_else(|| format!("operation_id {op_id} not in id_map"))?;
        let crew_id = *wc_to_crew
            .get(&wc_id)
            .ok_or_else(|| format!("work_center_id {wc_id} not in id_map"))?;
        let start = parse_dt(
            item.get("start_time")
                .and_then(Value::as_str)
                .ok_or_else(|| "assignment missing start_time".to_string())?,
        )?;
        let end = parse_dt(
            item.get("end_time")
                .and_then(Value::as_str)
                .ok_or_else(|| "assignment missing end_time".to_string())?,
        )?;
        let setup_minutes = match item.get("setup_minutes") {
            None => 0,
            Some(value) => {
                let minutes = value
                    .as_i64()
                    .ok_or_else(|| "setup_minutes must be an integer".to_string())?;
                if minutes < 0 {
                    return Err("setup_minutes must be non-negative".into());
                }
                i32::try_from(minutes).map_err(|_| "setup_minutes overflow".to_string())?
            }
        };
        out.push(Assignment {
            job_id,
            crew_id,
            start,
            end,
            setup_minutes,
        });
    }
    Ok((out, frozen_from_payload(root)?))
}

pub fn looks_like_python_cli_result(root: &Value) -> bool {
    root.pointer("/outcome/id_map").is_some() && root.pointer("/schedule/assignments").is_some()
}
