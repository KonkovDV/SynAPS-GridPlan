//! CLI: synthesize | solve | check | report | greed-bridge

use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand, ValueEnum};

use synaps_gridplan_rs::bridge::{default_bridge_note, solve_greed_via_python};
use synaps_gridplan_rs::constraints::check_plan;
use synaps_gridplan_rs::fifo::plan_fifo;
use synaps_gridplan_rs::model::{FrozenAssignment, GridPlanProblem};
use synaps_gridplan_rs::report::{render_csv, render_markdown};
use synaps_gridplan_rs::schedule::{
    assignments_from_python_cli, frozen_from_payload, looks_like_python_cli_result, Assignment,
    PlanResult,
};
use synaps_gridplan_rs::synthetic::synthesize_feeder;
use synaps_gridplan_rs::{unsupported_native_constraints, MAX_JSON_BYTES, VERSION};

#[derive(Parser, Debug)]
#[command(name = "synaps-gridplan-rs", version = VERSION)]
#[command(about = "Native GridPlan contour (FIFO + fail-closed checks). Experiment only.")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Write a synthetic feeder JSON (data_provenance=synthetic)
    Synthesize {
        #[arg(long, default_value = "small")]
        mode: String,
        #[arg(long, default_value_t = 42)]
        seed: u64,
        #[arg(short, long)]
        output: PathBuf,
    },
    /// Solve with native FIFO (or bridge GREED via Python)
    Solve {
        input: PathBuf,
        #[arg(long, value_enum, default_value_t = Engine::Fifo)]
        engine: Engine,
        #[arg(short, long)]
        output: PathBuf,
    },
    /// Re-check domain rules; unsupported engine constraints prevent verification
    Check { problem: PathBuf, plan: PathBuf },
    /// Render a saved native PlanResult without rechecking the original problem
    Report {
        input: PathBuf,
        #[arg(long, value_enum, default_value_t = ReportFmt::Markdown)]
        format: ReportFmt,
    },
}

#[derive(Clone, Debug, ValueEnum)]
enum Engine {
    Fifo,
    Greed,
}

#[derive(Clone, Debug, ValueEnum)]
enum ReportFmt {
    Json,
    Csv,
    Markdown,
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    match run(cli) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::from(1)
        }
    }
}

fn read_json_text(path: &PathBuf) -> Result<String, String> {
    let size = fs::metadata(path).map_err(|e| e.to_string())?.len();
    if size > MAX_JSON_BYTES {
        return Err(format!(
            "{} is {size} bytes; limit is {MAX_JSON_BYTES}",
            path.display()
        ));
    }
    fs::read_to_string(path).map_err(|e| e.to_string())
}

fn run(cli: Cli) -> Result<ExitCode, String> {
    match cli.command {
        Commands::Synthesize { mode, seed, output } => {
            let problem = synthesize_feeder(&mode, seed, None, None, None)?;
            problem.validate_refs()?;
            let json = serde_json::to_string_pretty(&problem).map_err(|e| e.to_string())?;
            fs::write(&output, json).map_err(|e| e.to_string())?;
            Ok(ExitCode::SUCCESS)
        }
        Commands::Solve {
            input,
            engine,
            output,
        } => match engine {
            Engine::Fifo => {
                let raw = read_json_text(&input)?;
                let problem: GridPlanProblem =
                    serde_json::from_str(&raw).map_err(|e| e.to_string())?;
                problem.validate_refs()?;
                let plan = plan_fifo(&problem);
                let json = serde_json::to_string_pretty(&plan).map_err(|e| e.to_string())?;
                fs::write(&output, json).map_err(|e| e.to_string())?;
                Ok(if plan.ok() {
                    ExitCode::SUCCESS
                } else {
                    ExitCode::from(2)
                })
            }
            Engine::Greed => {
                eprintln!("{}", default_bridge_note());
                let code = solve_greed_via_python(&input, &output).map_err(|e| e.to_string())?;
                Ok(ExitCode::from(code as u8))
            }
        },
        Commands::Check { problem, plan } => {
            let problem: GridPlanProblem =
                serde_json::from_str(&read_json_text(&problem)?).map_err(|e| e.to_string())?;
            problem.validate_refs()?;
            let (assignments, plan_frozen) = load_assignments_flexible(&plan)?;
            // The checker always includes mandatory problem commitments.
            let violations = check_plan(&problem, &assignments, &plan_frozen);
            let domain_verified_feasible = violations.is_empty();
            let unsupported_constraints = unsupported_native_constraints(&problem);
            let verified_feasible = domain_verified_feasible && unsupported_constraints.is_empty();
            let payload = serde_json::json!({
                "verified_feasible": verified_feasible,
                "domain_verified_feasible": domain_verified_feasible,
                "verification_scope": "gridplan_domain",
                "verification_origin": "independent_recheck",
                "engine_checked": false,
                "unsupported_constraints": unsupported_constraints,
                "hard_violation_count": violations.len(),
                "violations": violations,
                "claim_level": "experiment",
                "engine": "synaps_gridplan_rs"
            });
            println!("{}", serde_json::to_string_pretty(&payload).unwrap());
            Ok(if verified_feasible {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(2)
            })
        }
        Commands::Report { input, format } => {
            let mut plan: PlanResult =
                serde_json::from_str(&read_json_text(&input)?).map_err(|e| e.to_string())?;
            if plan.verified_feasible && !plan.ok() {
                return Err("saved plan has contradictory verification flags".into());
            }
            let metadata = plan
                .metadata
                .as_object_mut()
                .ok_or_else(|| "saved plan metadata must be an object".to_string())?;
            metadata.insert(
                "verification_origin".into(),
                "imported_snapshot_not_rechecked".into(),
            );
            match format {
                ReportFmt::Json => {
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&plan).map_err(|e| e.to_string())?
                    );
                }
                ReportFmt::Csv => print!("{}", render_csv(&plan)),
                ReportFmt::Markdown => println!("{}", render_markdown(&plan)),
            }
            Ok(ExitCode::SUCCESS)
        }
    }
}

fn load_assignments_flexible(
    path: &PathBuf,
) -> Result<(Vec<Assignment>, Vec<FrozenAssignment>), String> {
    let raw = read_json_text(path)?;
    let v: serde_json::Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    if looks_like_python_cli_result(&v) {
        return assignments_from_python_cli(&v);
    }
    let frozen = frozen_from_payload(&v)?;
    if let Ok(plan) = serde_json::from_value::<PlanResult>(v.clone()) {
        return Ok((plan.assignments, frozen));
    }
    if let Some(arr) = v.get("assignments").and_then(|a| a.as_array()) {
        let mut out = Vec::new();
        for item in arr {
            if item.get("job_id").is_some() {
                out.push(serde_json::from_value(item.clone()).map_err(|e| e.to_string())?);
                continue;
            }
            return Err(
                "assignments use operation_id; pass Python CLI JSON (with outcome.id_map) or native job_id rows"
                    .into(),
            );
        }
        return Ok((out, frozen));
    }
    Err("unsupported plan JSON for check".into())
}
