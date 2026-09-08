use serde_json::{json, Value};
use synaps_gridplan_rs::schedule::{
    assignments_from_python_cli, frozen_from_payload, invert_python_id_map, PlanResult,
};

fn payload() -> Value {
    json!({
        "outcome": {
            "id_map": {
                "job:cccccccc-cccc-cccc-cccc-ccccccccccc0": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0",
                "crew:dddddddd-dddd-dddd-dddd-ddddddddddd0": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb0"
            }
        },
        "schedule": {
            "assignments": [{
                "operation_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0",
                "work_center_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb0",
                "start_time": "2026-09-01T06:00:00Z",
                "end_time": "2026-09-01T07:00:00Z"
            }]
        }
    })
}

fn frozen_row() -> Value {
    json!({
        "job_id": "cccccccc-cccc-cccc-cccc-ccccccccccc0",
        "crew_id": "dddddddd-dddd-dddd-dddd-ddddddddddd0",
        "start": "2026-09-01T08:00:00Z",
        "end": "2026-09-01T09:00:00Z",
        "immutable": true
    })
}

#[test]
fn malformed_freeze_never_becomes_an_empty_commitment_list() {
    let mut reversed = frozen_row();
    reversed["end"] = reversed["start"].clone();
    for value in [
        Value::Null,
        json!({}),
        json!([{}]),
        json!([frozen_row(), {}]),
        json!([frozen_row(), frozen_row()]),
        json!([reversed]),
    ] {
        let mut p = payload();
        p["outcome"]["frozen_assignments"] = value;
        assert!(assignments_from_python_cli(&p).is_err(), "{p}");
    }
    assert!(frozen_from_payload(&json!({"outcome": null})).is_err());
}

#[test]
fn absent_empty_and_valid_freeze_remain_accepted() {
    let mut p = payload();
    assert!(assignments_from_python_cli(&p).unwrap().1.is_empty());
    p["outcome"]["frozen_assignments"] = json!([]);
    assert!(assignments_from_python_cli(&p).unwrap().1.is_empty());
    p["outcome"]["frozen_assignments"] = json!([frozen_row()]);
    assert_eq!(assignments_from_python_cli(&p).unwrap().1.len(), 1);
}

#[test]
fn setup_requires_a_nonnegative_i32_instead_of_defaulting_or_wrapping() {
    for value in [
        Value::Null,
        json!("5"),
        json!(true),
        json!(1.5),
        json!(-1),
        json!(i64::from(i32::MAX) + 1),
        json!(i64::MAX),
    ] {
        let mut p = payload();
        p["schedule"]["assignments"][0]["setup_minutes"] = value;
        assert!(assignments_from_python_cli(&p).is_err(), "{p}");
    }
    let mut p = payload();
    assert_eq!(
        assignments_from_python_cli(&p).unwrap().0[0].setup_minutes,
        0
    );
    p["schedule"]["assignments"][0]["setup_minutes"] = json!(i32::MAX);
    assert_eq!(
        assignments_from_python_cli(&p).unwrap().0[0].setup_minutes,
        i32::MAX
    );
}

#[test]
fn mapping_rejects_target_collisions_and_uuid_key_aliases() {
    for (key, value) in [
        (
            "job:eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0",
        ),
        (
            "crew:eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb0",
        ),
        (
            "job:CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCC0",
            "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        ),
        (
            "crew:DDDDDDDD-DDDD-DDDD-DDDD-DDDDDDDDDDD0",
            "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        ),
    ] {
        let mut p = payload();
        p["outcome"]["id_map"][key] = json!(value);
        assert!(invert_python_id_map(&p["outcome"]["id_map"]).is_err());
    }
}

#[test]
fn malformed_assignment_time_is_rejected() {
    let mut p = payload();
    p["schedule"]["assignments"][0]["start_time"] = json!("NaN");
    assert!(assignments_from_python_cli(&p).is_err());
}

#[test]
fn ok_cannot_accept_inconsistent_violation_metadata() {
    let mut plan: PlanResult = serde_json::from_value(json!({
        "schema_version": "gridplan.v1",
        "solver_config": "FIFO",
        "status": "feasible",
        "claim_status": "heuristic_feasible",
        "verified_feasible": true,
        "hard_violation_count": 0,
        "assignments": [],
        "objective": {
            "makespan_minutes": 0.0,
            "total_tardiness_minutes": 0.0,
            "coverage": 1.0,
            "unscheduled_operations": 0
        },
        "violations": [],
        "metadata": {}
    }))
    .unwrap();
    assert!(plan.ok());
    plan.hard_violation_count = 1;
    assert!(!plan.ok());
    plan.hard_violation_count = 0;
    plan.violations.push(synaps_gridplan_rs::Violation {
        kind: "TEST".into(),
        message: "must not be ignored".into(),
        job_id: None,
    });
    assert!(!plan.ok());
}
