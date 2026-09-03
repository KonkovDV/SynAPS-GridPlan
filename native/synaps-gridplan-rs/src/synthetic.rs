//! Deterministic synthetic feeder (explicitly labelled synthetic).

use chrono::{Duration, TimeZone, Utc};
use serde_json::json;
use std::collections::BTreeMap;

use crate::fingerprint::stable_int;
use crate::ids::gridplan_uid;
use crate::model::{
    Asset, Crew, Criticality, FrozenAssignment, GridPlanProblem, JobKind, MaintenanceJob,
    OutageWindow, RiskProfile, SparePart,
};
use crate::SCHEMA_VERSION;

struct Lcg {
    state: u32,
}

impl Lcg {
    fn new(seed: u64) -> Self {
        Self { state: seed as u32 }
    }
    fn next(&mut self) -> u32 {
        self.state = self
            .state
            .wrapping_mul(1_664_525)
            .wrapping_add(1_013_904_223);
        self.state
    }
}

pub fn synthesize_feeder(
    mode: &str,
    seed: u64,
    n_assets: Option<usize>,
    n_jobs: Option<usize>,
    n_crews: Option<usize>,
) -> Result<GridPlanProblem, String> {
    let (n_assets, n_jobs, n_crews, horizon_days) = match mode {
        "small" => (12, 30, 4, 14),
        "medium" => (
            n_assets.unwrap_or(40),
            n_jobs.unwrap_or(200),
            n_crews.unwrap_or(10),
            30,
        ),
        "stress" => (80, 600, 15, 45),
        "disruption" => (40, 200, 10, 30),
        "infeasible" => (8, 40, 1, 7),
        "frozen-conflict" => (10, 24, 3, 14),
        "gres-block" => {
            return Err(
                "gres-block is Python-only (synaps-gridplan synthesize --mode gres-block)".into(),
            )
        }
        "dual-feed-hall" => {
            return Err(
                "dual-feed-hall is Python-only (synaps-gridplan synthesize --mode dual-feed-hall)"
                    .into(),
            )
        }
        other => return Err(format!("unknown mode: {other}")),
    };
    if n_assets < 1 || n_jobs < 1 || n_crews < 1 {
        return Err("assets, jobs, and crews must be >= 1".into());
    }

    let mut rng = Lcg::new(seed);
    let start = Utc.with_ymd_and_hms(2026, 9, 1, 6, 0, 0).unwrap();
    let end = start + Duration::days(horizon_days);

    let skills = ["electro", "relay", "line", "switchgear"];
    let mut crews = Vec::new();
    for i in 0..n_crews {
        let q = vec![
            skills[i % skills.len()].to_string(),
            skills[(i + 1) % skills.len()].to_string(),
        ];
        crews.push(Crew {
            id: gridplan_uid(seed, &["crew", &i.to_string()]),
            code: format!("CREW-{:02}", i + 1),
            qualifications: q,
            max_parallel: 1,
            home_location_code: format!("DEPOT-{}", (i % 3) + 1),
            service_area: String::new(),
            shift_calendar: Vec::new(),
            availability: Vec::new(),
            data_provenance: "synthetic".into(),
            domain_attributes: serde_json::Value::Null,
        });
    }

    let criticalities = [
        Criticality::Low,
        Criticality::Medium,
        Criticality::High,
        Criticality::Critical,
    ];
    let mut assets = Vec::new();
    for i in 0..n_assets {
        let crit = criticalities[i % criticalities.len()].clone();
        let pof = (rng.next() % 1000) as f64 / 1000.0;
        assets.push(Asset {
            id: gridplan_uid(seed, &["asset", &i.to_string()]),
            external_ref: format!("A-{i:04}"),
            code: format!("ASSET-{i:04}"),
            name: format!("Feeder asset {i}"),
            asset_class: "equipment".into(),
            voltage_level: if i % 2 == 0 { "10kV" } else { "0.4kV" }.into(),
            location_code: format!("LOC-{}", (i % 5) + 1),
            service_area: String::new(),
            risk: RiskProfile {
                probability_of_failure: pof,
                consequence_score: 0.3 + (i % 5) as f64 * 0.1,
                criticality: crit,
                assessment_method: "synthetic_proxy".into(),
                confidence: 0.5,
                source_ref: "synthesize_feeder".into(),
                is_advisory: true,
            },
            data_provenance: "synthetic".into(),
            domain_attributes: json!({}),
        });
    }

    let mut spares = Vec::new();
    for i in 0..4 {
        spares.push(SparePart {
            id: gridplan_uid(seed, &["spare", &i.to_string()]),
            code: format!("ZIP-{i:02}"),
            stock_qty: 8,
            available_quantity: Some(8),
            reserved_quantity: 0,
            replenishment_date: None,
            data_provenance: "synthetic".into(),
        });
    }

    let mut outages = Vec::new();
    for (i, a) in assets.iter().enumerate().take(20) {
        let w_start = start + Duration::days((i as i64 % 7) + 1);
        let w_end = w_start + Duration::hours(48);
        outages.push(OutageWindow {
            id: gridplan_uid(seed, &["outage", &i.to_string()]),
            asset_id: a.id,
            start: w_start,
            end: w_end.min(end),
            approved: true,
            frozen: false,
            allowed_job_ids: vec![],
            forbidden_job_ids: vec![],
            external_ref: format!("OW-{i:03}"),
            data_provenance: "synthetic".into(),
        });
    }

    let kinds = [
        JobKind::Preventive,
        JobKind::Corrective,
        JobKind::Inspection,
        JobKind::Emergency,
    ];
    let mut jobs = Vec::new();
    for i in 0..n_jobs {
        let asset = &assets[i % n_assets];
        let needs_outage = i % 3 == 0;
        let due = start
            + Duration::days(
                ((rng.next() % (horizon_days as u32).max(2).saturating_sub(1)) + 2) as i64,
            );
        let duration = 60 + (rng.next() % 300) as i32;
        let skill = skills[i % skills.len()].to_string();
        jobs.push(MaintenanceJob {
            id: gridplan_uid(seed, &["job", &i.to_string()]),
            external_ref: format!("J-{i:04}"),
            asset_id: asset.id,
            kind: kinds[i % kinds.len()].clone(),
            duration_min: duration,
            required_qualifications: vec![skill],
            spare_part_ids: if i % 4 == 0 {
                vec![spares[i % spares.len()].id]
            } else {
                vec![]
            },
            predecessor_job_ids: vec![],
            due_date: Some(due),
            release_date: Some(start),
            latest_finish: None,
            eligible_crew_ids: vec![],
            safety_constraints: vec![],
            interruption_required: needs_outage,
            data_provenance: "synthetic".into(),
        });
    }

    for i in (0..n_jobs.saturating_sub(1).min(40)).step_by(5) {
        if i + 1 < jobs.len() {
            jobs[i + 1].predecessor_job_ids = vec![jobs[i].id];
        }
    }

    let mut travel: BTreeMap<String, i32> = BTreeMap::new();
    let mut locations: Vec<String> = assets
        .iter()
        .map(|a| a.location_code.clone())
        .chain(crews.iter().map(|c| c.home_location_code.clone()))
        .collect();
    locations.sort();
    locations.dedup();
    for a in &locations {
        for b in &locations {
            let key = format!("{a}|{b}");
            if a == b {
                travel.insert(key, 0);
            } else {
                let mins = 15 + stable_int(&[&seed.to_string(), a, b], 45) as i32;
                travel.insert(key, mins);
            }
        }
    }

    let mut frozen_rows = Vec::new();
    if mode == "infeasible" {
        let n = 8.min(jobs.len());
        for job in jobs.iter_mut().take(n) {
            job.interruption_required = true;
            job.spare_part_ids = vec![spares[0].id];
            job.duration_min = job.duration_min.max(360);
            job.required_qualifications = vec!["electro".into(), "relay".into(), "line".into()];
        }
        outages.clear();
        for s in &mut spares {
            s.available_quantity = Some(0);
            s.stock_qty = 0;
            s.reserved_quantity = 0;
        }
    }

    if mode == "frozen-conflict" {
        let job = &jobs[0];
        let crew = &crews[0];
        frozen_rows.push(FrozenAssignment {
            job_id: job.id,
            crew_id: crew.id,
            start: end - Duration::minutes(30),
            end: end + Duration::hours(6),
            source: "synthetic_conflict".into(),
            frozen_reason: "forced_horizon_overflow".into(),
            immutable: true,
            data_provenance: "synthetic".into(),
        });
    }

    Ok(GridPlanProblem {
        schema_version: SCHEMA_VERSION.to_string(),
        assets,
        crews,
        jobs,
        outage_windows: outages,
        spare_parts: spares,
        frozen_assignments: frozen_rows,
        simultaneous_outage_bans: vec![],
        travel_minutes: travel,
        planning_horizon_start: start,
        planning_horizon_end: end,
        domain_attributes: json!({
            "data_provenance": "synthetic",
            "generator": "synthesize_feeder_rs",
            "generator_mode": mode,
            "seed": seed,
            "claim_level": "experiment"
        }),
    })
}
