use chrono::Duration;
use serde_json::json;
use synaps_gridplan_rs::model::GridPlanProblem;
use synaps_gridplan_rs::synthesize_feeder;
use uuid::Uuid;

fn problem() -> GridPlanProblem {
    synthesize_feeder("small", 42, None, None, None).unwrap()
}

#[test]
fn supported_versions_and_empty_workload_remain_valid() {
    let mut p = problem();
    for version in ["gridplan.v1", "gridplan.v2"] {
        p.schema_version = version.into();
        p.validate_refs().unwrap();
    }
    p.jobs.clear();
    p.validate_refs().unwrap();
    p.schema_version = "gridplan.future".into();
    assert!(p
        .validate_refs()
        .unwrap_err()
        .contains("unsupported schema"));
}

#[test]
fn duplicate_catalog_and_frozen_ids_are_rejected() {
    let mut p = problem();
    p.frozen_assignments.push(
        serde_json::from_value(json!({
            "job_id": p.jobs[0].id,
            "crew_id": p.crews[0].id,
            "start": p.planning_horizon_start,
            "end": p.planning_horizon_start + Duration::hours(1)
        }))
        .unwrap(),
    );
    p.simultaneous_outage_bans.push(
        serde_json::from_value(json!({
            "id": Uuid::nil(),
            "asset_id_a": p.assets[0].id,
            "asset_id_b": p.assets[1].id
        }))
        .unwrap(),
    );
    p.validate_refs().unwrap();
    for field in [
        "assets",
        "crews",
        "jobs",
        "spare_parts",
        "outage_windows",
        "frozen_assignments",
        "simultaneous_outage_bans",
    ] {
        let mut raw = serde_json::to_value(&p).unwrap();
        let rows = raw[field].as_array_mut().unwrap();
        let duplicate = rows[0].clone();
        rows.push(duplicate);
        let bad: GridPlanProblem = serde_json::from_value(raw).unwrap();
        assert!(
            bad.validate_refs().unwrap_err().contains("duplicate"),
            "{field}"
        );
    }
}

#[test]
fn capacity_and_quantity_ranges_are_rejected_without_overflow() {
    for capacity in [0, -1, i32::MIN] {
        let mut p = problem();
        p.crews[0].max_parallel = capacity;
        assert!(p.validate_refs().is_err());
    }
    for (stock, available, reserved) in [
        (0, Some(0), -1),
        (-1, None, 0),
        (0, Some(-1), 0),
        (0, Some(i32::MIN), 1),
        (0, Some(0), 1),
        (0, Some(i32::MAX), i32::MIN),
    ] {
        let mut p = problem();
        let spare = &mut p.spare_parts[0];
        spare.stock_qty = stock;
        spare.available_quantity = available;
        spare.reserved_quantity = reserved;
        assert_eq!(spare.usable_quantity(), 0);
        assert!(p.validate_refs().is_err());
    }
    let mut p = problem();
    p.spare_parts[0].available_quantity = Some(i32::MAX);
    p.spare_parts[0].reserved_quantity = 1;
    assert_eq!(p.spare_parts[0].usable_quantity(), i32::MAX - 1);
    p.validate_refs().unwrap();
}

#[test]
fn unknown_window_references_and_invalid_intervals_are_rejected() {
    for field in ["asset_id", "allowed_job_ids", "forbidden_job_ids", "end"] {
        let mut raw = serde_json::to_value(problem()).unwrap();
        raw["outage_windows"][0][field] = match field {
            "asset_id" => json!(Uuid::nil()),
            "end" => raw["outage_windows"][0]["start"].clone(),
            _ => json!([Uuid::nil()]),
        };
        let p: GridPlanProblem = serde_json::from_value(raw).unwrap();
        assert!(p.validate_refs().is_err(), "{field}");
    }
}

#[test]
fn outage_bans_require_known_distinct_assets() {
    let mut p = problem();
    for other in [p.assets[0].id, Uuid::nil()] {
        let ban = serde_json::from_value(json!({
            "id": Uuid::nil(),
            "asset_id_a": p.assets[0].id,
            "asset_id_b": other
        }))
        .unwrap();
        p.simultaneous_outage_bans = vec![ban];
        assert!(p.validate_refs().is_err());
    }
}

#[test]
fn negative_travel_and_nonfinite_risk_are_rejected() {
    let mut p = problem();
    p.travel_minutes.insert("A|B".into(), -1);
    assert!(p.validate_refs().is_err());
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, -0.1, 1.1] {
        let mut p = problem();
        p.assets[0].risk.probability_of_failure = value;
        assert!(p.validate_refs().is_err());
    }
}

#[test]
fn serde_rejects_unknown_enums_malformed_times_and_numeric_overflow() {
    let raw = serde_json::to_value(problem()).unwrap();
    for (pointer, value) in [
        ("/jobs/0/kind", json!("unrecognized")),
        ("/assets/0/risk/criticality", json!("unrecognized")),
        ("/planning_horizon_start", json!("NaN")),
        ("/jobs/0/duration_min", json!(i64::from(i32::MAX) + 1)),
    ] {
        let mut bad = raw.clone();
        *bad.pointer_mut(pointer).unwrap() = value;
        assert!(
            serde_json::from_value::<GridPlanProblem>(bad).is_err(),
            "{pointer}"
        );
    }
}
