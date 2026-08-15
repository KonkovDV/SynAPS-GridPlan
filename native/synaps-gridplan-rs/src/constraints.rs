//! Fail-closed GridPlan post-checks (domain layer).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use uuid::Uuid;

use crate::model::{Asset, Crew, FrozenAssignment, GridPlanProblem, MaintenanceJob};
use crate::schedule::Assignment;
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Violation {
    pub kind: String,
    pub message: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub job_id: Option<Uuid>,
}

type OccupancySpan = (DateTime<Utc>, DateTime<Utc>, Uuid, String);
type ScheduledSpan<'a> = (DateTime<Utc>, DateTime<Utc>, &'a MaintenanceJob);

/// Union problem frozen rows with plan-supplied freeze. Plan wins on the same
/// ``job_id``. Empty plan freeze keeps the problem list (does not wipe it).
pub fn merge_expected_frozen(
    problem_frozen: &[FrozenAssignment],
    plan_frozen: &[FrozenAssignment],
) -> Vec<FrozenAssignment> {
    if plan_frozen.is_empty() {
        return problem_frozen.to_vec();
    }
    let extra: HashSet<Uuid> = plan_frozen.iter().map(|f| f.job_id).collect();
    let mut out: Vec<FrozenAssignment> = problem_frozen
        .iter()
        .filter(|f| !extra.contains(&f.job_id))
        .cloned()
        .collect();
    out.extend(plan_frozen.iter().cloned());
    out
}

pub fn check_plan(
    problem: &GridPlanProblem,
    assignments: &[Assignment],
    expected_frozen: &[FrozenAssignment],
) -> Vec<Violation> {
    let mut out = Vec::new();
    let jobs_by_id: HashMap<_, _> = problem.jobs.iter().map(|j| (j.id, j)).collect();
    let crews_by_id: HashMap<_, _> = problem.crews.iter().map(|c| (c.id, c)).collect();
    let assets_by_id: HashMap<_, _> = problem.assets.iter().map(|a| (a.id, a)).collect();
    let spares_by_id: HashMap<_, _> = problem.spare_parts.iter().map(|s| (s.id, s)).collect();

    let mut by_job: HashMap<Uuid, &Assignment> = HashMap::new();
    for a in assignments {
        if by_job.insert(a.job_id, a).is_some() {
            out.push(Violation {
                kind: "DUPLICATE_JOB_ASSIGNMENT".into(),
                message: format!("job {} assigned more than once", a.job_id),
                job_id: Some(a.job_id),
            });
        }
        let Some(job) = jobs_by_id.get(&a.job_id) else {
            out.push(Violation {
                kind: "UNKNOWN_JOB".into(),
                message: format!("assignment references unknown job {}", a.job_id),
                job_id: Some(a.job_id),
            });
            continue;
        };
        let Some(crew) = crews_by_id.get(&a.crew_id) else {
            out.push(Violation {
                kind: "UNKNOWN_CREW".into(),
                message: format!("job {} maps to unknown crew", job.external_ref),
                job_id: Some(job.id),
            });
            continue;
        };
        let required: HashSet<_> = job.required_qualifications.iter().cloned().collect();
        let have: HashSet<_> = crew.qualifications.iter().cloned().collect();
        let mut sorted_req: Vec<_> = required.iter().cloned().collect();
        let mut sorted_have: Vec<_> = have.iter().cloned().collect();
        sorted_req.sort();
        sorted_have.sort();
        if !required.is_empty() && !required.is_subset(&have) {
            out.push(Violation {
                kind: "QUALIFICATION_MISMATCH".into(),
                message: format!(
                    "job {} requires {:?} but crew {} has {:?}",
                    job.external_ref, sorted_req, crew.code, sorted_have
                ),
                job_id: Some(job.id),
            });
        }
        if !job.eligible_crew_ids.is_empty() && !job.eligible_crew_ids.contains(&a.crew_id) {
            out.push(Violation {
                kind: "ELIGIBLE_CREW_MISMATCH".into(),
                message: format!(
                    "job {} assigned to crew {} outside eligible_crew_ids",
                    job.external_ref, crew.code
                ),
                job_id: Some(job.id),
            });
        }
        out.extend(catalog_field_violations(
            job,
            crew,
            assets_by_id.get(&job.asset_id).copied(),
            a.start,
            a.end,
        ));
        if let Some(release) = job.release_date {
            if a.start < release {
                out.push(Violation {
                    kind: "RELEASE_DATE_VIOLATION".into(),
                    message: format!("job {} starts before release_date", job.external_ref),
                    job_id: Some(job.id),
                });
            }
        }
        if let Some(latest) = job.latest_finish {
            if a.end > latest {
                out.push(Violation {
                    kind: "LATEST_FINISH_VIOLATION".into(),
                    message: format!("job {} ends after latest_finish", job.external_ref),
                    job_id: Some(job.id),
                });
            }
        }
        if a.start < problem.planning_horizon_start || a.end > problem.planning_horizon_end {
            out.push(Violation {
                kind: "HORIZON_VIOLATION".into(),
                message: format!("job {} outside planning horizon", job.external_ref),
                job_id: Some(job.id),
            });
        }
        if a.end <= a.start || job.duration_min < 1 {
            out.push(Violation {
                kind: "INVALID_DURATION".into(),
                message: format!("job {} non-positive scheduled duration", job.external_ref),
                job_id: Some(job.id),
            });
        } else if (a.end - a.start).num_minutes() < i64::from(job.duration_min) {
            out.push(Violation {
                kind: "SHORT_DURATION".into(),
                message: format!(
                    "job {} scheduled shorter than duration_min={}",
                    job.external_ref, job.duration_min
                ),
                job_id: Some(job.id),
            });
        }
        out.extend(outage_violations(problem, job, a.start, a.end));
    }

    out.extend(precedence_violations(problem, &by_job));
    out.extend(spare_violations(problem, assignments, &spares_by_id));
    out.extend(frozen_violations(expected_frozen, &by_job, &jobs_by_id));
    out.extend(crew_overlap_violations(assignments, &crews_by_id));
    out.extend(asset_overlap_violations(problem, assignments));
    out.extend(simultaneous_outage_ban_violations(problem, assignments));
    // Completeness: every job must be scheduled exactly once.
    for job in &problem.jobs {
        if !by_job.contains_key(&job.id) {
            out.push(Violation {
                kind: "UNSCHEDULED_JOB".into(),
                message: format!(
                    "job {} has no assignment — solver dropped it",
                    job.external_ref
                ),
                job_id: Some(job.id),
            });
        }
    }
    out
}

fn crew_overlap_violations(
    assignments: &[Assignment],
    crews_by_id: &HashMap<Uuid, &crate::model::Crew>,
) -> Vec<Violation> {
    let mut by_crew: HashMap<Uuid, Vec<&Assignment>> = HashMap::new();
    for a in assignments {
        by_crew.entry(a.crew_id).or_default().push(a);
    }
    let mut out = Vec::new();
    for (crew_id, rows) in by_crew {
        // Sweep-line: a violation is concurrency above max_parallel, not any
        // pairwise overlap (crews may field several technicians at once).
        let max_parallel = crews_by_id
            .get(&crew_id)
            .map(|c| c.max_parallel.max(1))
            .unwrap_or(1);
        let mut events: Vec<(DateTime<Utc>, i64, Uuid)> = Vec::new();
        for a in &rows {
            events.push((a.start, 1, a.job_id));
            events.push((a.end, -1, a.job_id));
        }
        // End before start at the same instant (half-open intervals).
        events.sort_by_key(|(t, delta, _)| (*t, *delta));
        let mut active: Vec<Uuid> = Vec::new();
        let mut reported = false;
        for (_, delta, job_id) in events {
            if delta > 0 {
                active.push(job_id);
            } else {
                active.retain(|j| *j != job_id);
            }
            if active.len() as i32 > max_parallel && !reported {
                out.push(Violation {
                    kind: "CREW_OVERLAP".into(),
                    message: format!(
                        "crew {} runs {} assignments in parallel (max {})",
                        crew_id,
                        active.len(),
                        max_parallel
                    ),
                    job_id: Some(job_id),
                });
                reported = true; // one signal per crew is enough
            }
        }
    }
    out
}

fn asset_overlap_violations(
    problem: &GridPlanProblem,
    assignments: &[Assignment],
) -> Vec<Violation> {
    // Two interruption jobs on the same asset cannot overlap in time.
    let jobs_by_id: HashMap<_, _> = problem.jobs.iter().map(|j| (j.id, j)).collect();
    let mut by_asset: HashMap<Uuid, Vec<(&Assignment, &MaintenanceJob)>> = HashMap::new();
    for a in assignments {
        if let Some(job) = jobs_by_id.get(&a.job_id) {
            if job.interruption_required {
                by_asset.entry(job.asset_id).or_default().push((a, *job));
            }
        }
    }
    let mut out = Vec::new();
    for (asset_id, mut rows) in by_asset {
        rows.sort_by_key(|(a, _)| a.start);
        for pair in rows.windows(2) {
            let (first, first_job) = pair[0];
            let (second, second_job) = pair[1];
            if first.end > second.start {
                out.push(Violation {
                    kind: "ASSET_OVERLAP".into(),
                    message: format!(
                        "asset {}: jobs {} and {} overlap — one asset, one outage at a time",
                        asset_id, first_job.external_ref, second_job.external_ref
                    ),
                    job_id: Some(second_job.id),
                });
            }
        }
    }
    out
}

fn find_root(parent: &mut HashMap<Uuid, Uuid>, x: Uuid) -> Uuid {
    let p = *parent.get(&x).unwrap_or(&x);
    if p != x {
        let r = find_root(parent, p);
        parent.insert(x, r);
        r
    } else {
        x
    }
}

fn chain_occupancy_spans(
    jobs: &[&MaintenanceJob],
    scheduled: &HashMap<Uuid, ScheduledSpan<'_>>,
) -> Vec<OccupancySpan> {
    // Hull of a precedence-connected interruption chain on one asset.
    if jobs.is_empty() {
        return vec![];
    }
    let mut parent: HashMap<Uuid, Uuid> = jobs.iter().map(|j| (j.id, j.id)).collect();
    let ids: HashSet<Uuid> = parent.keys().copied().collect();
    for job in jobs {
        for pred in &job.predecessor_job_ids {
            if ids.contains(pred) {
                let ra = find_root(&mut parent, job.id);
                let rb = find_root(&mut parent, *pred);
                if ra != rb {
                    parent.insert(rb, ra);
                }
            }
        }
    }
    let mut groups: HashMap<Uuid, Vec<&MaintenanceJob>> = HashMap::new();
    for job in jobs {
        let root = find_root(&mut parent, job.id);
        groups.entry(root).or_default().push(*job);
    }
    let mut out = Vec::new();
    for members in groups.values() {
        let mut timed = Vec::new();
        for m in members {
            if let Some(span) = scheduled.get(&m.id) {
                timed.push(*span);
            }
        }
        if timed.is_empty() {
            continue;
        }
        let start = timed.iter().map(|t| t.0).min().unwrap();
        let end = timed.iter().map(|t| t.1).max().unwrap();
        let rep = timed
            .iter()
            .max_by_key(|t| t.1)
            .map(|t| (t.2.id, t.2.external_ref.clone()))
            .unwrap();
        out.push((start, end, rep.0, rep.1));
    }
    out
}

fn simultaneous_outage_ban_violations(
    problem: &GridPlanProblem,
    assignments: &[Assignment],
) -> Vec<Violation> {
    if problem.simultaneous_outage_bans.is_empty() {
        return vec![];
    }
    let jobs_by_id: HashMap<_, _> = problem.jobs.iter().map(|j| (j.id, j)).collect();
    let mut scheduled: HashMap<Uuid, ScheduledSpan<'_>> = HashMap::new();
    for a in assignments {
        if let Some(job) = jobs_by_id.get(&a.job_id) {
            if job.interruption_required {
                scheduled.insert(job.id, (a.start, a.end, *job));
            }
        }
    }
    let mut by_asset: HashMap<Uuid, Vec<&MaintenanceJob>> = HashMap::new();
    for job in &problem.jobs {
        if job.interruption_required {
            by_asset.entry(job.asset_id).or_default().push(job);
        }
    }
    let mut occupancy: HashMap<Uuid, Vec<OccupancySpan>> = HashMap::new();
    for (asset_id, jobs) in &by_asset {
        occupancy.insert(*asset_id, chain_occupancy_spans(jobs, &scheduled));
    }
    let mut out = Vec::new();
    for ban in &problem.simultaneous_outage_bans {
        let left = occupancy.get(&ban.asset_id_a).cloned().unwrap_or_default();
        let right = occupancy.get(&ban.asset_id_b).cloned().unwrap_or_default();
        for (a_start, a_end, _a_id, a_ref) in &left {
            for (b_start, b_end, b_id, b_ref) in &right {
                if a_start < b_end && b_start < a_end {
                    out.push(Violation {
                        kind: "SIMULTANEOUS_OUTAGE_BAN".into(),
                        message: format!(
                            "chain occupancy of {a_ref} and {b_ref} overlap under simultaneous-outage ban"
                        ),
                        job_id: Some(*b_id),
                    });
                }
            }
        }
    }
    out
}

fn outage_violations(
    problem: &GridPlanProblem,
    job: &MaintenanceJob,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
) -> Vec<Violation> {
    if !job.interruption_required {
        return vec![];
    }
    let windows: Vec<_> = problem
        .outage_windows
        .iter()
        .filter(|w| w.asset_id == job.asset_id && w.approved)
        .collect();

    for w in &windows {
        if w.forbidden_job_ids.contains(&job.id) && start < w.end && end > w.start {
            return vec![Violation {
                kind: "FORBIDDEN_OUTAGE_WINDOW".into(),
                message: format!(
                    "job {} intersects forbidden outage {}",
                    job.external_ref,
                    if w.external_ref.is_empty() {
                        w.id.to_string()
                    } else {
                        w.external_ref.clone()
                    }
                ),
                job_id: Some(job.id),
            }];
        }
    }

    let allowed: Vec<_> = windows
        .into_iter()
        .filter(|w| {
            if w.forbidden_job_ids.contains(&job.id) {
                return false;
            }
            if !w.allowed_job_ids.is_empty() && !w.allowed_job_ids.contains(&job.id) {
                return false;
            }
            true
        })
        .collect();

    if allowed.is_empty() {
        return vec![Violation {
            kind: "OUTAGE_WINDOW_MISSING".into(),
            message: format!(
                "job {} requires interruption but has no approved outage window",
                job.external_ref
            ),
            job_id: Some(job.id),
        }];
    }

    for w in &allowed {
        if start >= w.start && end <= w.end {
            return vec![];
        }
    }

    vec![Violation {
        kind: "OUTAGE_WINDOW_VIOLATION".into(),
        message: format!(
            "job {} scheduled outside all allowed outage windows",
            job.external_ref
        ),
        job_id: Some(job.id),
    }]
}

fn precedence_violations(
    problem: &GridPlanProblem,
    by_job: &HashMap<Uuid, &Assignment>,
) -> Vec<Violation> {
    let mut out = Vec::new();
    let jobs_by_id: HashMap<_, _> = problem.jobs.iter().map(|j| (j.id, j)).collect();
    for job in &problem.jobs {
        let Some(asn) = by_job.get(&job.id) else {
            continue;
        };
        for pred in &job.predecessor_job_ids {
            match by_job.get(pred) {
                None => out.push(Violation {
                    kind: "PRECEDENCE_VIOLATION".into(),
                    message: format!(
                        "job {} starts without scheduled predecessor {}",
                        job.external_ref,
                        jobs_by_id
                            .get(pred)
                            .map(|j| j.external_ref.as_str())
                            .unwrap_or("?")
                    ),
                    job_id: Some(job.id),
                }),
                Some(p) if asn.start < p.end => out.push(Violation {
                    kind: "PRECEDENCE_VIOLATION".into(),
                    message: format!("job {} overlaps predecessor {}", job.external_ref, pred),
                    job_id: Some(job.id),
                }),
                _ => {}
            }
        }
    }
    out
}

fn spare_violations(
    problem: &GridPlanProblem,
    assignments: &[Assignment],
    spares_by_id: &HashMap<Uuid, &crate::model::SparePart>,
) -> Vec<Violation> {
    let assigned: HashSet<_> = assignments.iter().map(|a| a.job_id).collect();
    let start_by_job: HashMap<_, _> = assignments.iter().map(|a| (a.job_id, a.start)).collect();
    let mut consumption: HashMap<Uuid, i32> =
        problem.spare_parts.iter().map(|s| (s.id, 0)).collect();

    // A replenishment-date miss must not hide the shortage count.
    let mut out = Vec::new();
    for job in &problem.jobs {
        if !assigned.contains(&job.id) {
            continue;
        }
        let start = start_by_job[&job.id];
        for spare_id in &job.spare_part_ids {
            let Some(spare) = spares_by_id.get(spare_id) else {
                continue;
            };
            if let Some(rep) = spare.replenishment_date {
                if start < rep {
                    out.push(Violation {
                        kind: "SPARE_PART_NOT_YET_AVAILABLE".into(),
                        message: format!(
                            "job {} uses {} before replenishment",
                            job.external_ref, spare.code
                        ),
                        job_id: Some(job.id),
                    });
                }
            }
            *consumption.entry(*spare_id).or_insert(0) += 1;
        }
    }

    for spare in &problem.spare_parts {
        let used = *consumption.get(&spare.id).unwrap_or(&0);
        if used > spare.usable_quantity() {
            out.push(Violation {
                kind: "SPARE_PART_SHORTAGE".into(),
                message: format!(
                    "spare {}: consumed {} > usable {}",
                    spare.code,
                    used,
                    spare.usable_quantity()
                ),
                job_id: None,
            });
        }
    }
    out
}

fn frozen_violations(
    frozen: &[FrozenAssignment],
    by_job: &HashMap<Uuid, &Assignment>,
    jobs_by_id: &HashMap<Uuid, &MaintenanceJob>,
) -> Vec<Violation> {
    let mut out = Vec::new();
    for fr in frozen {
        if !fr.immutable {
            continue;
        }
        let label = jobs_by_id
            .get(&fr.job_id)
            .map(|j| j.external_ref.as_str())
            .unwrap_or("?");
        match by_job.get(&fr.job_id) {
            None => out.push(Violation {
                kind: "FROZEN_ASSIGNMENT_CONFLICT".into(),
                message: format!("frozen job {label} missing from schedule"),
                job_id: Some(fr.job_id),
            }),
            Some(a) if a.crew_id != fr.crew_id || a.start != fr.start || a.end != fr.end => out
                .push(Violation {
                    kind: "FROZEN_ASSIGNMENT_CONFLICT".into(),
                    message: format!("frozen job {label} changed vs immutable commitment"),
                    job_id: Some(fr.job_id),
                }),
            _ => {}
        }
    }
    out
}

fn parse_calendar_instant(value: Option<&Value>) -> Option<DateTime<Utc>> {
    let raw = value?;
    let text = raw.as_str()?;
    DateTime::parse_from_rfc3339(text)
        .ok()
        .map(|parsed| parsed.with_timezone(&Utc))
}

fn calendar_verdict(
    rows: &[Value],
    start: DateTime<Utc>,
    end: DateTime<Utc>,
) -> Option<&'static str> {
    if rows.is_empty() {
        return None;
    }
    let mut parsed = Vec::new();
    for row in rows {
        let Some(obj) = row.as_object() else {
            return Some("MALFORMED");
        };
        let Some(window_start) = parse_calendar_instant(obj.get("start")) else {
            return Some("MALFORMED");
        };
        let Some(window_end) = parse_calendar_instant(obj.get("end")) else {
            return Some("MALFORMED");
        };
        if window_end <= window_start {
            return Some("MALFORMED");
        }
        parsed.push((window_start, window_end));
    }
    if parsed
        .iter()
        .any(|(window_start, window_end)| start >= *window_start && end <= *window_end)
    {
        return None;
    }
    Some("OUTSIDE")
}

fn catalog_field_violations(
    job: &MaintenanceJob,
    crew: &Crew,
    asset: Option<&Asset>,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
) -> Vec<Violation> {
    let mut out = Vec::new();
    for (name, rows, kind) in [
        (
            "shift_calendar",
            crew.shift_calendar.as_slice(),
            "SHIFT_CALENDAR",
        ),
        ("availability", crew.availability.as_slice(), "AVAILABILITY"),
    ] {
        match calendar_verdict(rows, start, end) {
            Some("MALFORMED") => out.push(Violation {
                kind: format!("{kind}_MALFORMED"),
                message: format!(
                    "crew {} {name} entries must have parseable start/end",
                    crew.code
                ),
                job_id: Some(job.id),
            }),
            Some("OUTSIDE") => out.push(Violation {
                kind: format!("{kind}_VIOLATION"),
                message: format!(
                    "job {} assignment is outside crew {} {name}",
                    job.external_ref, crew.code
                ),
                job_id: Some(job.id),
            }),
            _ => {}
        }
    }

    if !job.safety_constraints.is_empty() {
        let mut clearances: HashSet<String> = crew.qualifications.iter().cloned().collect();
        if let Some(extra) = crew
            .domain_attributes
            .get("safety_clearances")
            .and_then(Value::as_array)
        {
            for item in extra {
                if let Some(text) = item.as_str() {
                    clearances.insert(text.to_string());
                }
            }
        }
        let required: HashSet<String> = job.safety_constraints.iter().cloned().collect();
        if !required.is_subset(&clearances) {
            out.push(Violation {
                kind: "SAFETY_CONSTRAINT_MISMATCH".into(),
                message: format!(
                    "job {} safety_constraints are not covered by crew {}",
                    job.external_ref, crew.code
                ),
                job_id: Some(job.id),
            });
        }
    }

    let asset_area = asset.map(|a| a.service_area.as_str()).unwrap_or("");
    if !asset_area.is_empty() && !crew.service_area.is_empty() && asset_area != crew.service_area {
        out.push(Violation {
            kind: "SERVICE_AREA_MISMATCH".into(),
            message: format!(
                "job {} asset area does not match crew {} area",
                job.external_ref, crew.code
            ),
            job_id: Some(job.id),
        });
    }
    out
}
