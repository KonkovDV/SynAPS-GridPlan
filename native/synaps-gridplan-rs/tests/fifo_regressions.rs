use chrono::{DateTime, Duration, Utc};
use serde_json::json;
use synaps_gridplan_rs::{plan_fifo, synthesize_feeder, GridPlanProblem};

fn problem() -> GridPlanProblem {
    let mut p = synthesize_feeder("small", 42, None, None, None).unwrap();
    p.jobs.truncate(1);
    p.jobs[0].duration_min = 60;
    p.jobs[0].interruption_required = false;
    p.jobs[0].spare_part_ids.clear();
    p.jobs[0].required_qualifications.clear();
    p.jobs[0].release_date = None;
    p
}

fn freeze_first(p: &mut GridPlanProblem, immutable: bool) {
    let row = serde_json::from_value(json!({
        "job_id": p.jobs[0].id,
        "crew_id": p.crews[0].id,
        "start": p.planning_horizon_start,
        "end": p.planning_horizon_start + Duration::hours(1),
        "immutable": immutable
    }))
    .unwrap();
    p.frozen_assignments = vec![row];
}

#[test]
fn advisory_freeze_does_not_override_release_or_reserve_crew() {
    let mut p = problem();
    let release = p.planning_horizon_start + Duration::hours(2);
    p.jobs[0].release_date = Some(release);
    freeze_first(&mut p, false);
    let result = plan_fifo(&p);
    assert!(result.ok(), "{:?}", result.violations);
    assert_eq!(result.assignments[0].start, release);

    p.jobs[0].release_date = None;
    p.frozen_assignments[0].start = release;
    p.frozen_assignments[0].end = release + Duration::hours(1);
    let result = plan_fifo(&p);
    assert!(result.ok());
    assert_eq!(result.assignments[0].start, p.planning_horizon_start);
}

#[test]
fn mandatory_freeze_remains_pinned_even_when_infeasible() {
    let mut p = problem();
    p.jobs[0].release_date = Some(p.planning_horizon_start + Duration::hours(2));
    freeze_first(&mut p, true);
    let result = plan_fifo(&p);
    assert!(!result.ok());
    assert_eq!(result.assignments[0].start, p.frozen_assignments[0].start);
    assert!(result
        .violations
        .iter()
        .any(|v| v.kind == "RELEASE_DATE_VIOLATION"));
}

#[test]
fn fifo_rejects_duplicate_jobs_instead_of_claiming_partial_coverage_feasible() {
    let mut p = problem();
    freeze_first(&mut p, true);
    let duplicate = p.jobs[0].clone();
    p.jobs[0].duration_min = 120;
    p.jobs.push(duplicate);
    let result = plan_fifo(&p);
    assert_eq!(result.status, "error");
    assert!(!result.verified_feasible);
    assert!(result.assignments.is_empty());
    assert_eq!(result.violations[0].kind, "INVALID_PROBLEM");
}

#[test]
fn fifo_rejects_zero_capacity_and_phantom_stock_at_entry() {
    let mut p = problem();
    p.crews[0].max_parallel = 0;
    assert_eq!(plan_fifo(&p).violations[0].kind, "INVALID_PROBLEM");
    let mut p = problem();
    p.spare_parts[0].available_quantity = Some(0);
    p.spare_parts[0].reserved_quantity = -1;
    p.jobs[0].spare_part_ids = vec![p.spare_parts[0].id];
    assert_eq!(plan_fifo(&p).violations[0].kind, "INVALID_PROBLEM");
}

#[test]
fn chrono_upper_bound_cannot_panic_or_clip_duration() {
    let mut p = problem();
    p.planning_horizon_end = DateTime::<Utc>::MAX_UTC;
    p.planning_horizon_start = p.planning_horizon_end - Duration::minutes(30);
    p.validate_refs().unwrap();
    let result = plan_fifo(&p);
    assert!(!result.verified_feasible);
    assert!(result.assignments.is_empty());
    assert_eq!(result.objective.unscheduled_operations, 1);
    assert!(result.violations.iter().any(|v| v.kind == "UNSCHEDULED_JOB"));
}
