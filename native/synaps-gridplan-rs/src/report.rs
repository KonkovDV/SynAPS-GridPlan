//! Human/machine report renderers. Rendering is not a fresh verification.

use crate::schedule::PlanResult;

pub fn render_markdown(plan: &PlanResult) -> String {
    let meta = &plan.metadata;
    let mut lines = vec![
        "# SynAPS-GridPlan (Rust) report".into(),
        String::new(),
        "> Rendering only: this report does not recheck the plan.".into(),
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
            "- verification_scope: `{}`",
            meta.get("verification_scope")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
        ),
        format!(
            "- verification_origin: `{}`",
            meta.get("verification_origin")
                .and_then(|v| v.as_str())
                .unwrap_or("unspecified")
        ),
        format!(
            "- unsupported_constraints: `{}`",
            meta.get("unsupported_constraints")
                .unwrap_or(&serde_json::Value::Null)
        ),
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
        "- A nonempty travel matrix requires Python/SynAPS verification.".into(),
        "- Synthetic/experiment results are not industrial proof.".into(),
        "- Heuristic FEASIBLE does not imply OPTIMAL.".into(),
        "- Combinatorial crew/window/mutex only; power-flow / N-1 / SAIDI are out of scope.".into(),
        String::new(),
    ]);
    lines.join("\n")
}

fn csv_cell(value: &str) -> String {
    let trimmed = value.trim_start_matches(|c: char| c.is_whitespace() || c == '\u{feff}');
    let formula = matches!(trimmed.chars().next(), Some('=' | '+' | '-' | '@'))
        || matches!(value.chars().next(), Some('\t' | '\r' | '\n'));
    let text = if formula {
        format!("'{value}")
    } else {
        value.to_string()
    };
    if text.chars().any(|c| matches!(c, ',' | '"' | '\r' | '\n')) {
        format!("\"{}\"", text.replace('"', "\"\""))
    } else {
        text
    }
}

pub fn render_csv(plan: &PlanResult) -> String {
    let meta = &plan.metadata;
    let mut out = String::new();
    for (key, default) in [
        ("claim_level", "experiment"),
        ("input_hash", ""),
        ("verification_scope", "unknown"),
        ("verification_origin", "unspecified"),
    ] {
        let value = meta.get(key).and_then(|v| v.as_str()).unwrap_or(default);
        out.push_str(&format!("# {key},{}\n", csv_cell(value)));
    }
    let unsupported = meta
        .get("unsupported_constraints")
        .map(ToString::to_string)
        .unwrap_or_else(|| "unknown".into());
    out.push_str(&format!(
        "# unsupported_constraints,{}\n",
        csv_cell(&unsupported)
    ));
    out.push_str("# verification_note,Rendering only: this report does not recheck the plan.\n");
    out.push_str(&format!("# status,{}\n", csv_cell(&plan.status)));
    out.push_str(&format!("# verified_feasible,{}\n", plan.verified_feasible));
    out.push_str("job_id,crew_id,start,end,setup_minutes,status,source\n");
    for a in &plan.assignments {
        out.push_str(&format!(
            "{},{},{},{},{},{},{}\n",
            a.job_id,
            a.crew_id,
            csv_cell(&a.start.to_rfc3339()),
            csv_cell(&a.end.to_rfc3339()),
            a.setup_minutes,
            csv_cell(&plan.status),
            csv_cell(&plan.solver_config)
        ));
    }
    out
}
