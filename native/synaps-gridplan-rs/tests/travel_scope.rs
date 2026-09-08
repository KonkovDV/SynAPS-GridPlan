use serde_json::{json, Value};
use std::fs;
use std::process::Command;
use synaps_gridplan_rs::{plan_fifo, GridPlanProblem};

fn problem() -> Value {
    json!({
        "assets": [
            {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "code": "A", "location_code": "A"},
            {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "code": "B", "location_code": "B"}
        ],
        "crews": [{
            "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "code": "C",
            "home_location_code": "A"
        }],
        "jobs": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "external_ref": "J1",
                "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "duration_min": 60
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "external_ref": "J2",
                "asset_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "predecessor_job_ids": ["11111111-1111-1111-1111-111111111111"],
                "duration_min": 60
            }
        ],
        "planning_horizon_start": "2026-09-01T06:00:00Z",
        "planning_horizon_end": "2026-09-01T10:00:00Z"
    })
}

#[test]
fn fifo_does_not_certify_an_unsupported_travel_matrix() {
    let empty: GridPlanProblem = serde_json::from_value(problem()).unwrap();
    assert!(plan_fifo(&empty).ok());
    for minutes in [30, 0] {
        let mut raw = problem();
        raw["travel_minutes"] = json!({"A|A": 0, "A|B": minutes, "B|A": minutes, "B|B": 0});
        let p: GridPlanProblem = serde_json::from_value(raw).unwrap();
        let result = plan_fifo(&p);
        assert!(result.violations.is_empty(), "{:?}", result.violations);
        assert!(!result.verified_feasible);
        assert!(!result.ok());
        assert_eq!(result.status, "error");
        assert_eq!(result.hard_violation_count, 0);
        assert_eq!(result.metadata["domain_verified_feasible"], json!(true));
        assert_eq!(
            result.metadata["unsupported_constraints"],
            json!(["travel_minutes"])
        );
    }
}

#[test]
fn cli_does_not_certify_back_to_back_jobs_at_different_sites() {
    let raw = problem();
    let empty: GridPlanProblem = serde_json::from_value(raw.clone()).unwrap();
    let zero_travel_plan = plan_fifo(&empty);
    assert!(zero_travel_plan.ok());
    assert_eq!(
        zero_travel_plan.assignments[0].end,
        zero_travel_plan.assignments[1].start
    );
    let dir = tempfile::tempdir().unwrap();
    let problem_path = dir.path().join("problem.json");
    let plan_path = dir.path().join("plan.json");
    fs::write(&plan_path, serde_json::to_vec(&zero_travel_plan).unwrap()).unwrap();
    for minutes in [30, 0] {
        let mut p = raw.clone();
        p["travel_minutes"] = json!({"A|A": 0, "A|B": minutes, "B|A": minutes, "B|B": 0});
        fs::write(&problem_path, serde_json::to_vec(&p).unwrap()).unwrap();
        let output = Command::new(env!("CARGO_BIN_EXE_synaps-gridplan-rs"))
            .arg("check")
            .arg(&problem_path)
            .arg(&plan_path)
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(2), "{output:?}");
        let payload: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(payload["violations"], json!([]));
        assert_eq!(payload["domain_verified_feasible"], json!(true));
        assert_eq!(payload["verified_feasible"], json!(false));
        assert_eq!(
            payload["unsupported_constraints"],
            json!(["travel_minutes"])
        );
    }
}
