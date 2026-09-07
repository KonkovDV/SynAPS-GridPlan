use serde_json::{json, Value};
use std::fs;
use std::process::{Command, Output};

fn problem() -> Value {
    json!({
        "assets": [{"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "code": "A"}],
        "crews": [{"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "code": "C"}],
        "jobs": [{
            "id": "11111111-1111-1111-1111-111111111111",
            "external_ref": "J",
            "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "duration_min": 60
        }],
        "planning_horizon_start": "2026-09-01T06:00:00Z",
        "planning_horizon_end": "2026-09-01T10:00:00Z"
    })
}

fn assignment() -> Value {
    json!({
        "job_id": "11111111-1111-1111-1111-111111111111",
        "crew_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "start": "2026-09-01T06:00:00Z",
        "end": "2026-09-01T07:00:00Z"
    })
}

fn native_result() -> Value {
    json!({
        "schema_version": "gridplan.v1",
        "solver_config": "FIFO",
        "status": "feasible",
        "claim_status": "heuristic_feasible",
        "verified_feasible": true,
        "hard_violation_count": 0,
        "assignments": [assignment()],
        "objective": {
            "makespan_minutes": 60.0,
            "total_tardiness_minutes": 0.0,
            "coverage": 1.0,
            "unscheduled_operations": 0
        },
        "violations": [],
        "metadata": {}
    })
}

fn python_result() -> Value {
    json!({
        "outcome": {
            "id_map": {
                "job:11111111-1111-1111-1111-111111111111": "22222222-2222-2222-2222-222222222222",
                "crew:cccccccc-cccc-cccc-cccc-cccccccccccc": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
            }
        },
        "schedule": {"assignments": [{
            "operation_id": "22222222-2222-2222-2222-222222222222",
            "work_center_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "start_time": "2026-09-01T06:00:00Z",
            "end_time": "2026-09-01T07:00:00Z"
        }]}
    })
}

fn check(problem: &Value, plan: &Value) -> Output {
    let dir = tempfile::tempdir().unwrap();
    let problem_path = dir.path().join("problem.json");
    let plan_path = dir.path().join("plan.json");
    fs::write(&problem_path, serde_json::to_vec(problem).unwrap()).unwrap();
    fs::write(&plan_path, serde_json::to_vec(plan).unwrap()).unwrap();
    Command::new(env!("CARGO_BIN_EXE_synaps-gridplan-rs"))
        .arg("check")
        .arg(problem_path)
        .arg(plan_path)
        .output()
        .unwrap()
}

fn assert_rejected(output: &Output, code: i32) {
    assert_eq!(output.status.code(), Some(code), "{output:?}");
    if let Ok(payload) = serde_json::from_slice::<Value>(&output.stdout) {
        assert_ne!(payload["verified_feasible"], json!(true));
    }
}

#[test]
fn check_accepts_all_three_supported_plan_shapes() {
    for plan in [
        json!({"assignments": [assignment()]}),
        native_result(),
        python_result(),
    ] {
        let output = check(&problem(), &plan);
        assert!(output.status.success(), "{output:?}");
        let payload: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(payload["verified_feasible"], json!(true));
    }
}

#[test]
fn check_does_not_let_any_plan_shape_drop_malformed_freeze() {
    for mut plan in [
        json!({"assignments": [assignment()]}),
        native_result(),
        python_result(),
    ] {
        let mut frozen = assignment();
        frozen["start"] = json!("2026-09-01T08:00:00Z");
        frozen["end"] = json!("2026-09-01T09:00:00Z");
        if plan.get("outcome").is_none() {
            plan["outcome"] = json!({});
        }
        plan["outcome"]["frozen_assignments"] = json!([frozen, {}]);
        assert_rejected(&check(&problem(), &plan), 1);
        plan["outcome"]["frozen_assignments"] = Value::Null;
        assert_rejected(&check(&problem(), &plan), 1);
    }
}

#[test]
fn check_preserves_mandatory_problem_freeze_against_plan_override() {
    let mut p = problem();
    p["frozen_assignments"] = json!([assignment()]);
    for immutable in [false, true] {
        let mut moved = assignment();
        moved["start"] = json!("2026-09-01T07:00:00Z");
        moved["end"] = json!("2026-09-01T08:00:00Z");
        let mut plan = json!({"assignments": [moved.clone()]});
        moved["immutable"] = json!(immutable);
        plan["outcome"] = json!({"frozen_assignments": [moved]});
        let output = check(&p, &plan);
        assert_rejected(&output, 2);
        let payload: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(payload["violations"][0]["kind"], "FROZEN_ASSIGNMENT_CONFLICT");
    }
}

#[test]
fn check_rejects_unknown_asset_spare_and_unsupported_schema() {
    for field in ["asset", "spare", "version"] {
        let mut p = problem();
        match field {
            "asset" => {
                p["jobs"][0]["asset_id"] = json!("99999999-9999-9999-9999-999999999999");
            }
            "spare" => {
                p["jobs"][0]["spare_part_ids"] = json!(["99999999-9999-9999-9999-999999999999"]);
            }
            _ => p["schema_version"] = json!("gridplan.future"),
        }
        assert_rejected(&check(&p, &json!({"assignments": [assignment()]})), 1);
    }
}

#[test]
fn check_rejects_duplicate_catalog_jobs_and_negative_setup() {
    let mut p = problem();
    p["jobs"]
        .as_array_mut()
        .unwrap()
        .push(problem()["jobs"][0].clone());
    assert_rejected(&check(&p, &native_result()), 1);
    let mut plan = native_result();
    plan["assignments"][0]["setup_minutes"] = json!(-1);
    assert_rejected(&check(&problem(), &plan), 2);
}

#[test]
fn check_empty_workload_is_vacuously_feasible() {
    let mut p = problem();
    p["jobs"] = json!([]);
    let output = check(&p, &json!({"assignments": []}));
    assert!(output.status.success(), "{output:?}");
}
