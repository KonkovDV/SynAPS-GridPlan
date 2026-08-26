//! Human/machine report renderers.

use crate::schedule::PlanResult;

pub fn render_markdown(plan: &PlanResult) -> String {
    let meta = &plan.metadata;
    let mut lines = vec![
        "# SynAPS-GridPlan (Rust) report".into(),
        String::new(),
        format!("- schema: `{}`", plan.schema_version),
        format!(
            "- gridplan_rs_version: `{}`",
            meta.get("gridplan_rs_version")
                .and_then(|v| v.as_str())
                .unwrap_or("?")
        ),
        format!("- solver: `{}`", plan.solver_config),
        format!("- status: **{}**", plan.status),
        format!("- claim_status: `{}`", plan.claim_status),
        format!("- verified_feasible: **{}**", plan.verified_feasible),
        format!("- hard_violations: {}", plan.hard_violation_count),
        format!(
            "- claim_level: `{}`",
            meta.get("claim_level")
                .and_then(|v| v.as_str())
                .unwrap_or("experiment")
        ),
        format!(
            "- input_hash: `{}`",
            meta.get("input_hash")
                .and_then(|v| v.as_str())
                .unwrap_or("")
        ),
        format!("- assignments: {}", plan.assignments.len()),
        String::new(),
        "## Objective".into(),
        String::new(),
        "| makespan_min | tardiness_min | coverage | unscheduled |".into(),
        "| ---: | ---: | ---: | ---: |".into(),
        format!(
            "| {:.1} | {:.1} | {:.3} | {} |",
            plan.objective.makespan_minutes,
            plan.objective.total_tardiness_minutes,
            plan.objective.coverage,
            plan.objective.unscheduled_operations
        ),
        String::new(),
        "## Violations".into(),
        String::new(),
    ];
    if plan.violations.is_empty() {
        lines.push("- none recorded at GridPlan-rs layer".into());
    } else {
        for v in plan.violations.iter().take(20) {
            lines.push(format!("- `{}`: {}", v.kind, v.message));
        }
    }
    lines.extend([
        String::new(),
        "## Applicability limits".into(),
        String::new(),
        "- Native FIFO contour only; GREED remains Python/SynAPS.".into(),
        "- Synthetic/experiment results are not industrial proof.".into(),
        "- Heuristic FEASIBLE does not imply OPTIMAL.".into(),
        String::new(),
    ]);
    lines.join("\n")
}

pub fn render_csv(plan: &PlanResult) -> String {
    let meta = &plan.metadata;
    let mut out = String::new();
    out.push_str(&format!(
        "# claim_level,{}\n",
        meta.get("claim_level")
            .and_then(|v| v.as_str())
            .unwrap_or("experiment")
    ));
    out.push_str(&format!(
        "# input_hash,{}\n",
        meta.get("input_hash")
            .and_then(|v| v.as_str())
            .unwrap_or("")
    ));
    out.push_str(&format!("# status,{}\n", plan.status));
    out.push_str(&format!("# verified_feasible,{}\n", plan.verified_feasible));
    out.push_str("job_id,crew_id,start,end,setup_minutes,status,source\n");
    for a in &plan.assignments {
        out.push_str(&format!(
            "{},{},{},{},{},{},{}\n",
            a.job_id,
            a.crew_id,
            a.start.to_rfc3339(),
            a.end.to_rfc3339(),
            a.setup_minutes,
            plan.status,
            plan.solver_config
        ));
    }
    out
}
