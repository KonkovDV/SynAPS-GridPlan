//! Same crew predicate as ``synaps_gridplan.eligibility``.
//!
//! Qualifications form the pool. A non-empty safety list must sit in the union
//! of qualifications and the string entries of ``safety_clearances``. A
//! non-string clearance is not a clearance. Service areas apply only when both
//! strings are set. When the filter would leave nobody, the previous pool is
//! kept.

use std::collections::{HashMap, HashSet};
use uuid::Uuid;

use crate::model::{Asset, Crew, GridPlanProblem, MaintenanceJob};

pub struct SearchIndex<'a> {
    crews: HashMap<Uuid, &'a Crew>,
    crew_order: Vec<Uuid>,
    quals: HashMap<Uuid, HashSet<&'a str>>,
    assets: HashMap<Uuid, &'a Asset>,
}

impl<'a> SearchIndex<'a> {
    pub fn build(problem: &'a GridPlanProblem) -> Self {
        let mut crews = HashMap::with_capacity(problem.crews.len());
        let mut quals = HashMap::with_capacity(problem.crews.len());
        let mut crew_order = Vec::with_capacity(problem.crews.len());
        for crew in &problem.crews {
            crews.insert(crew.id, crew);
            quals.insert(
                crew.id,
                crew.qualifications.iter().map(String::as_str).collect(),
            );
            crew_order.push(crew.id);
        }
        let assets = problem
            .assets
            .iter()
            .map(|asset| (asset.id, asset))
            .collect();
        Self {
            crews,
            crew_order,
            quals,
            assets,
        }
    }

    pub fn crews_for_search(&self, job: &MaintenanceJob) -> Vec<Uuid> {
        let pool = if !job.eligible_crew_ids.is_empty() {
            job.eligible_crew_ids
                .iter()
                .copied()
                .filter(|crew_id| self.crews.contains_key(crew_id))
                .collect()
        } else {
            let required: HashSet<&str> = job
                .required_qualifications
                .iter()
                .map(String::as_str)
                .collect();
            let selected: Vec<Uuid> = self
                .crew_order
                .iter()
                .copied()
                .filter(|crew_id| {
                    self.quals
                        .get(crew_id)
                        .is_some_and(|have| required.is_subset(have))
                })
                .collect();
            if selected.is_empty() && required.is_empty() {
                self.crew_order.clone()
            } else {
                selected
            }
        };
        let asset = self.assets.get(&job.asset_id).copied();
        let legal: Vec<Uuid> = pool
            .iter()
            .copied()
            .filter(|crew_id| {
                let Some(crew) = self.crews.get(crew_id) else {
                    return false;
                };
                covers_safety(job, crew) && covers_service_area(crew, asset)
            })
            .collect();
        if legal.is_empty() {
            pool
        } else {
            legal
        }
    }
}

pub fn covers_safety(job: &MaintenanceJob, crew: &Crew) -> bool {
    if job.safety_constraints.is_empty() {
        return true;
    }
    let have = clearance_strings(crew);
    job.safety_constraints.iter().all(|item| {
        crew.qualifications.iter().any(|qual| qual == item) || have.contains(item.as_str())
    })
}

pub fn covers_service_area(crew: &Crew, asset: Option<&Asset>) -> bool {
    let Some(asset) = asset else {
        return true;
    };
    if asset.service_area.is_empty() || crew.service_area.is_empty() {
        return true;
    }
    asset.service_area == crew.service_area
}

fn clearance_strings(crew: &Crew) -> HashSet<&str> {
    let Some(extra) = crew
        .domain_attributes
        .get("safety_clearances")
        .and_then(serde_json::Value::as_array)
    else {
        return HashSet::new();
    };
    extra.iter().filter_map(|item| item.as_str()).collect()
}
