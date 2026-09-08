use serde_json::{json, Value};
use std::fs;
use std::process::{Command, Output};
use synaps_gridplan_rs::report::{render_csv, render_markdown};
use synaps_gridplan_rs::PlanResult;

fn plan() -> PlanResult {
    serde_json::from_value(json!({
        "schema_version": "gridplan.v1",
        "solver_config": "FIFO",
        "status": "feasible",
        "claim_status": "heuristic_feasible",
        "verified_feasible": true,
        "hard_violation_count": 0,
        "assignments": [{
            "job_id": "11111111-1111-1111-1111-111111111111",
            "crew_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "start": "2026-09-01T06:00:00Z",
            "end": "2026-09-01T07:00:00Z"
        }],
        "objective": {
            "makespan_minutes": 60.0,
            "total_tardiness_minutes": 0.0,
            "coverage": 1.0,
            "unscheduled_operations": 0
        },
        "violations": [],
        "metadata": {}
    }))
    .unwrap()
}

fn report(p: &PlanResult) -> Output {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("plan.json");
    let original = serde_json::to_vec(p).unwrap();
    fs::write(&path, &original).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_synaps-gridplan-rs"))
        .arg("report")
        .arg(&path)
        .arg("--format")
        .arg("json")
        .output()
        .unwrap();
    assert_eq!(fs::read(path).unwrap(), original);
    output
}

#[test]
fn csv_protects_preamble_and_assignment_cells() {
    for (raw, encoded) in [
        ("plain", "plain"),
        ("=1+1", "'=1+1"),
        ("  +CMD", "'  +CMD"),
        ("-1", "'-1"),
        ("\u{feff}@X", "'\u{feff}@X"),
        ("\tcmd", "'\tcmd"),
        ("\rcmd", "\"'\rcmd\""),
        ("\ncmd", "\"'\ncmd\""),
        ("safe,\n\"x\"", "\"safe,\n\"\"x\"\"\""),
    ] {
        let mut p = plan();
        p.solver_config = raw.into();
        p.status = raw.into();
        p.verified_feasible = false;
        p.metadata = json!({"claim_level": raw, "input_hash": raw});
        let csv = render_csv(&p);
        assert!(
            csv.contains(&format!("# claim_level,{encoded}\n")),
            "{csv:?}"
        );
        assert!(
            csv.contains(&format!("# input_hash,{encoded}\n")),
            "{csv:?}"
        );
        assert!(csv.contains(&format!("# status,{encoded}\n")), "{csv:?}");
        assert!(csv.ends_with(&format!(",{encoded},{encoded}\n")), "{csv:?}");
    }
}

#[test]
fn renderers_disclose_that_they_do_not_reverify() {
    let p = plan();
    assert!(render_csv(&p).contains("does not recheck the plan"));
    assert!(render_markdown(&p).contains("does not recheck the plan"));
}

#[test]
fn report_cli_marks_snapshots_and_rejects_inconsistent_flags() {
    let mut p = plan();
    p.metadata["verification_origin"] = json!("live_checker");
    let output = report(&p);
    assert!(output.status.success(), "{output:?}");
    let payload: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        payload["metadata"]["verification_origin"],
        "imported_snapshot_not_rechecked"
    );
    for field in ["status", "hard_count", "violations", "metadata"] {
        let mut bad = plan();
        match field {
            "status" => bad.status = "error".into(),
            "hard_count" => bad.hard_violation_count = 1,
            "violations" => bad.violations.push(synaps_gridplan_rs::Violation {
                kind: "TEST".into(),
                message: "must not be ignored".into(),
                job_id: None,
            }),
            _ => bad.metadata = json!([]),
        }
        let output = report(&bad);
        assert_eq!(output.status.code(), Some(1), "{field}: {output:?}");
    }
}
