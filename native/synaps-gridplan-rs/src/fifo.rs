//! Calendar FIFO baseline — earliest due date, earliest free eligible crew.
//!
//! Transparent synthetic baseline only. Not an industrial method claim.
//! Assignments use domain job/crew UUIDs (not SynAPS operation UUIDs).

use chrono::{DateTime, Duration, Utc};
use serde_json::json;
use std::collections::{HashMap, HashSet};
use uuid::Uuid;

use crate::constraints::check_plan;
use crate::fingerprint::fingerprint_payload;
use crate::model::GridPlanProblem;
use crate::schedule::{Assignment, ObjectiveSnapshot, PlanResult};
use crate::{CLAIM_LEVEL, SCHEMA_VERSION, VERSION};

pub fn plan_fifo(problem: &GridPlanProblem) -> PlanResult {
    let mut crew_free: HashMap<Uuid, DateTime<Utc>> = problem
        .crews
        .iter()
        .map(|c| (c.id, problem.planning_horizon_start))
        .collect();

    let mut ordered: Vec<&crate::model::MaintenanceJob> = problem.jobs.iter().collect();
    ordered.sort_by(|a, b| {
        let da = a.due_date.unwrap_or(problem.planning_horizon_end);
        let db = b.due_date.unwrap_or(problem.planning_horizon_end);
        da.cmp(&db)
            .then_with(|| a.external_ref.cmp(&b.external_ref))
            .then_with(|| a.id.as_bytes().cmp(b.id.as_bytes()))
    });

    let mut assignments: Vec<Assignment> = Vec::new();
    let mut frozen_job_ids: HashSet<Uuid> = HashSet::new();
    for fr in &problem.frozen_assignments {
        if !frozen_job_ids.insert(fr.job_id) {
            continue;
        }
        assignments.push(Assignment {
            job_id: fr.job_id,
            crew_id: fr.crew_id,
            start: fr.start,
            end: fr.end,
            setup_minutes: 0,
        });
        let free_at = crew_free
            .entry(fr.crew_id)
            .or_insert(problem.planning_horizon_start);
        if fr.end > *free_at {
            *free_at = fr.end;
        }
    }

    for &job in &ordered {
        if frozen_job_ids.contains(&job.id) {
            continue;
        }
        let eligible: Vec<Uuid> = if !job.eligible_crew_ids.is_empty() {
            job.eligible_crew_ids.clone()
        } else {
            let req: std::collections::HashSet<_> =
                job.required_qualifications.iter().cloned().collect();
            let qualified: Vec<Uuid> = problem
                .crews
                .iter()
                .filter(|c| {
                    let have: std::collections::HashSet<_> =
                        c.qualifications.iter().cloned().collect();
                    req.is_empty() || req.is_subset(&have)
                })
                .map(|c| c.id)
                .collect();
            // Parity with Python: empty qualified set falls back to all crews
            // (post-check will flag QUALIFICATION_MISMATCH).
            if qualified.is_empty() {
                problem.crews.iter().map(|c| c.id).collect()
            } else {
                qualified
            }
        };

        let mut best: Option<(Uuid, DateTime<Utc>)> = None;
        let crew_code: HashMap<Uuid, &str> = problem
            .crews
            .iter()
            .map(|c| (c.id, c.code.as_str()))
            .collect();
        for crew_id in &eligible {
            let free_at = *crew_free
                .get(crew_id)
                .unwrap_or(&problem.planning_horizon_start);
            let release = job.release_date.unwrap_or(problem.planning_horizon_start);
            let start = free_at.max(release).max(problem.planning_horizon_start);
            let end = start + Duration::minutes(job.duration_min as i64);
            if end > problem.planning_horizon_end {
                continue;
            }
            match best {
                None => best = Some((*crew_id, start)),
                Some((bc, bs)) => {
                    // Tie-break on crew code (stable domain key), then UUID bytes.
                    let better = start < bs
                        || (start == bs
                            && (crew_code.get(crew_id).unwrap_or(&""), crew_id.as_bytes())
                                < (crew_code.get(&bc).unwrap_or(&""), bc.as_bytes()));
                    if better {
                        best = Some((*crew_id, start));
                    }
                }
            }
        }
        if let Some((crew_id, start)) = best {
            let end = start
                .checked_add_signed(Duration::minutes(job.duration_min as i64))
                .ok_or(0)
                .unwrap_or(problem.planning_horizon_end);
            assignments.push(Assignment {
                job_id: job.id,
                crew_id,
                start,
                end,
                setup_minutes: 0,
            });
            crew_free.insert(crew_id, end);
        }
    }

    let unscheduled = (problem.jobs.len() as i32) - (assignments.len() as i32);
    let coverage = if problem.jobs.is_empty() {
        1.0
    } else {
        assignments.len() as f64 / problem.jobs.len() as f64
    };
    let makespan = if assignments.is_empty() {
        0.0
    } else {
        let t0 = assignments.iter().map(|a| a.start).min().unwrap();
        let t1 = assignments.iter().map(|a| a.end).max().unwrap();
        (t1 - t0).num_minutes() as f64
    };
    let jobs_by_id: HashMap<_, _> = problem.jobs.iter().map(|j| (j.id, j)).collect();
    let mut tardiness = 0.0;
    for a in &assignments {
        if let Some(job) = jobs_by_id.get(&a.job_id) {
            if let Some(due) = job.due_date {
                if a.end > due {
                    tardiness += (a.end - due).num_minutes() as f64;
                }
            }
        }
    }

    let violations = check_plan(problem, &assignments, &problem.frozen_assignments);
    // Empty instance (zero jobs) is vacuously feasible, not a solver failure.
    let status = if assignments.is_empty() && !problem.jobs.is_empty() {
        "infeasible"
    } else if violations.is_empty() {
        "feasible"
    } else {
        "error"
    };
    let verified = status == "feasible" && violations.is_empty();
    let claim_status = if verified {
        "heuristic_feasible"
    } else {
        status
    };

    let input_hash = fingerprint_payload(&serde_json::to_value(problem).unwrap_or(json!({})));
    let config_hash = fingerprint_payload(&json!({
        "solver_config": "FIFO",
        "engine": "synaps_gridplan_rs",
        "version": VERSION,
        "apply_frozen": true,
    }));

    PlanResult {
        schema_version: SCHEMA_VERSION.to_string(),
        solver_config: "FIFO".into(),
        status: status.into(),
        claim_status: claim_status.into(),
        verified_feasible: verified,
        hard_violation_count: violations.len(),
        assignments,
        objective: ObjectiveSnapshot {
            makespan_minutes: makespan,
            total_tardiness_minutes: tardiness,
            coverage,
            unscheduled_operations: unscheduled,
        },
        violations,
        metadata: json!({
            "claim_level": CLAIM_LEVEL,
            "data_provenance": problem.domain_attributes
                .get("data_provenance")
                .cloned()
                .unwrap_or(json!("synthetic")),
            "gridplan_rs_version": VERSION,
            "baseline": "calendar_fifo_earliest_due",
            "metric_tag": "synthetic_experiment",
            "input_hash": input_hash,
            "config_hash": config_hash,
            "optimality_note": "Допустимое найденное решение без доказательства оптимальности",
            "applicability_limits": [
                "Native FIFO only — not SynAPS GREED/CPSAT.",
                "Synthetic/experiment results are not industrial proof.",
                "Heuristic FEASIBLE does not imply OPTIMAL.",
                "Combinatorial crew/window/mutex only; power-flow / N-1 / SAIDI are out of scope."
            ]
        }),
    }
    .with_claim_defaults()
}
