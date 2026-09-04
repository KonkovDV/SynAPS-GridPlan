use chrono::Duration;
use synaps_gridplan_rs::constraints::{check_plan, merge_expected_frozen};
use synaps_gridplan_rs::fifo::plan_fifo;
use synaps_gridplan_rs::fingerprint::{fingerprint_payload, stable_int};
use synaps_gridplan_rs::ids::gridplan_uid;
use synaps_gridplan_rs::model::{FrozenAssignment, GridPlanProblem};
use synaps_gridplan_rs::schedule::{assignments_from_python_cli, Assignment};
use synaps_gridplan_rs::synthetic::synthesize_feeder;
use uuid::Uuid;

#[test]
fn synthesize_small_is_synthetic_and_valid() {
    let p = synthesize_feeder("small", 42, None, None, None).unwrap();
    assert_eq!(p.assets.len(), 12);
    assert_eq!(p.jobs.len(), 30);
    assert_eq!(p.crews.len(), 4);
    p.validate_refs().unwrap();
    assert_eq!(
        p.domain_attributes["data_provenance"],
        serde_json::json!("synthetic")
    );
}

#[test]
fn fifo_deterministic_same_seed() {
    let p = synthesize_feeder("small", 7, None, None, None).unwrap();
    let a = plan_fifo(&p);
    let b = plan_fifo(&p);
    assert_eq!(a.status, b.status);
    assert_eq!(
        serde_json::to_value(&a.assignments).unwrap(),
        serde_json::to_value(&b.assignments).unwrap()
    );
    assert!(a.metadata["claim_level"] == "experiment");
}

#[test]
fn infeasible_mode_not_verified() {
    let p = synthesize_feeder("infeasible", 3, None, None, None).unwrap();
    let plan = plan_fifo(&p);
    assert!(!plan.verified_feasible);
}

#[test]
fn empty_jobs_fifo_is_feasible() {
    let mut p = synthesize_feeder("small", 1, None, None, None).unwrap();
    p.jobs.clear();
    p.frozen_assignments.clear();
    let plan = plan_fifo(&p);
    assert_eq!(plan.status, "feasible");
    assert!(plan.verified_feasible);
    assert_eq!(plan.objective.unscheduled_operations, 0);
}

#[test]
fn frozen_conflict_detected_on_check() {
    let p = synthesize_feeder("frozen-conflict", 9, None, None, None).unwrap();
    assert!(!p.frozen_assignments.is_empty());
    let plan = plan_fifo(&p);
    let v = check_plan(&p, &plan.assignments, &p.frozen_assignments);
    assert!(v.iter().any(|x| x.kind == "FROZEN_ASSIGNMENT_CONFLICT") || !plan.verified_feasible);
}

#[test]
fn python_parity_tokens() {
    assert_eq!(stable_int(&["42", "LOC-1", "LOC-2"], 45), 34);
    assert_eq!(
        gridplan_uid(42, &["crew", "0"]),
        Uuid::parse_str("5a64a413-e2cc-5aec-9336-a229cf7cfecd").unwrap()
    );
    let h = fingerprint_payload(&serde_json::json!({"b": 2, "a": 1}));
    assert_eq!(
        h,
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    );
}

#[test]
fn short_duration_is_fail_closed() {
    let mut p = synthesize_feeder("small", 1, None, None, None).unwrap();
    p.jobs.truncate(1);
    p.jobs[0].duration_min = 60;
    let a = Assignment {
        job_id: p.jobs[0].id,
        crew_id: p.crews[0].id,
        start: p.planning_horizon_start,
        end: p.planning_horizon_start + Duration::minutes(10),
        setup_minutes: 0,
    };
    let v = check_plan(&p, &[a], &[]);
    assert!(v.iter().any(|x| x.kind == "SHORT_DURATION"));
    assert!(!v.iter().any(|x| x.kind == "INVALID_DURATION"));
}

#[test]
fn fifo_pins_immutable_frozen() {
    let mut p = synthesize_feeder("small", 2, None, None, None).unwrap();
    p.jobs.truncate(2);
    let start = p.planning_horizon_start + Duration::hours(4);
    let end = start + Duration::minutes(i64::from(p.jobs[0].duration_min));
    p.frozen_assignments = vec![FrozenAssignment {
        job_id: p.jobs[0].id,
        crew_id: p.crews[0].id,
        start,
        end,
        source: "test".into(),
        frozen_reason: "pin".into(),
        immutable: true,
        data_provenance: "synthetic".into(),
    }];
    let plan = plan_fifo(&p);
    let a = plan
        .assignments
        .iter()
        .find(|x| x.job_id == p.jobs[0].id)
        .expect("frozen job scheduled");
    assert_eq!(a.start, start);
    assert_eq!(a.end, end);
    assert_eq!(a.crew_id, p.crews[0].id);
}

#[test]
fn merge_frozen_is_additive_plan_wins() {
    let p = synthesize_feeder("frozen-conflict", 9, None, None, None).unwrap();
    let problem_row = p.frozen_assignments[0].clone();
    let mut plan_row = problem_row.clone();
    plan_row.start = p.planning_horizon_start;
    plan_row.end = p.planning_horizon_start + Duration::minutes(30);
    let merged = merge_expected_frozen(&p.frozen_assignments, &[plan_row.clone()]);
    assert_eq!(merged.len(), 1);
    assert_eq!(merged[0].start, plan_row.start);
    let keep_problem = merge_expected_frozen(&p.frozen_assignments, &[]);
    assert_eq!(keep_problem[0].start, problem_row.start);
}

#[test]
fn synthesize_gres_block_is_python_only() {
    let err = synthesize_feeder("gres-block", 1, None, None, None).unwrap_err();
    assert!(err.contains("Python-only"), "{err}");
}

#[test]
fn synthesize_dual_feed_hall_is_python_only() {
    let err = synthesize_feeder("dual-feed-hall", 1, None, None, None).unwrap_err();
    assert!(err.contains("Python-only"), "{err}");
}

#[test]
fn chain_hull_occupies_gap_under_outage_ban() {
    let p: GridPlanProblem = serde_json::from_value(serde_json::json!({
        "assets": [
            {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1", "code": "A1"},
            {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2", "code": "A2"}
        ],
        "crews": [
            {"id": "cccccccc-cccc-cccc-cccc-ccccccccccc1", "code": "C1"},
            {"id": "cccccccc-cccc-cccc-cccc-ccccccccccc2", "code": "C2"}
        ],
        "jobs": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "external_ref": "ISO-A",
                "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
                "duration_min": 120,
                "interruption_required": true
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "external_ref": "TEST-A",
                "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
                "duration_min": 180,
                "interruption_required": true,
                "predecessor_job_ids": ["11111111-1111-1111-1111-111111111111"]
            },
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "external_ref": "ISO-B",
                "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
                "duration_min": 120,
                "interruption_required": true
            }
        ],
        "outage_windows": [
            {
                "id": "dddddddd-dddd-dddd-dddd-ddddddddddd1",
                "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
                "start": "2026-09-01T06:00:00Z",
                "end": "2026-09-02T06:00:00Z",
                "approved": true
            },
            {
                "id": "dddddddd-dddd-dddd-dddd-ddddddddddd2",
                "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
                "start": "2026-09-01T06:00:00Z",
                "end": "2026-09-02T06:00:00Z",
                "approved": true
            }
        ],
        "simultaneous_outage_bans": [{
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "asset_id_a": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            "asset_id_b": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
            "reason": "not N-1"
        }],
        "planning_horizon_start": "2026-09-01T06:00:00Z",
        "planning_horizon_end": "2026-09-02T06:00:00Z"
    }))
    .unwrap();
    let assignments = vec![
        Assignment {
            job_id: p.jobs[0].id,
            crew_id: p.crews[0].id,
            start: p.planning_horizon_start,
            end: p.planning_horizon_start + Duration::minutes(120),
            setup_minutes: 0,
        },
        Assignment {
            job_id: p.jobs[1].id,
            crew_id: p.crews[0].id,
            start: p.planning_horizon_start + Duration::hours(10),
            end: p.planning_horizon_start + Duration::hours(13),
            setup_minutes: 0,
        },
        Assignment {
            job_id: p.jobs[2].id,
            crew_id: p.crews[1].id,
            start: p.planning_horizon_start + Duration::hours(4),
            end: p.planning_horizon_start + Duration::hours(6),
            setup_minutes: 0,
        },
    ];
    let kinds: Vec<_> = check_plan(&p, &assignments, &[])
        .into_iter()
        .map(|v| v.kind)
        .collect();
    assert!(
        kinds.iter().any(|k| k == "SIMULTANEOUS_OUTAGE_BAN"),
        "{kinds:?}"
    );
    assert!(!kinds.iter().any(|k| k == "OUTAGE_WINDOW_VIOLATION"));
}

#[test]
fn python_cli_json_maps_operation_id_via_id_map() {
    let op = Uuid::parse_str("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0").unwrap();
    let wc = Uuid::parse_str("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb0").unwrap();
    let job = Uuid::parse_str("cccccccc-cccc-cccc-cccc-ccccccccccc0").unwrap();
    let crew = Uuid::parse_str("dddddddd-dddd-dddd-dddd-ddddddddddd0").unwrap();
    let root = serde_json::json!({
        "outcome": {
            "id_map": {
                "job:cccccccc-cccc-cccc-cccc-ccccccccccc0": op,
                "crew:dddddddd-dddd-dddd-dddd-ddddddddddd0": wc
            },
            "frozen_assignments": []
        },
        "schedule": {
            "assignments": [{
                "operation_id": op,
                "work_center_id": wc,
                "start_time": "2026-09-01T06:00:00+00:00",
                "end_time": "2026-09-01T07:00:00+00:00",
                "setup_minutes": 5
            }]
        }
    });
    let (assignments, frozen) = assignments_from_python_cli(&root).expect("map");
    assert!(frozen.is_empty());
    assert_eq!(assignments.len(), 1);
    assert_eq!(assignments[0].job_id, job);
    assert_eq!(assignments[0].crew_id, crew);
    assert_eq!(assignments[0].setup_minutes, 5);
}
