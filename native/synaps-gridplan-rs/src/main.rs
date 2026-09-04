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
    assignments_from_python_cli, looks_like_python_cli_result, Assignment, PlanResult,
};
use synaps_gridplan_rs::synthetic::synthesize_feeder;
use synaps_gridplan_rs::VERSION;

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
    /// Re-check assignments JSON against a problem (fail-closed)
    Check { problem: PathBuf, plan: PathBuf },
    /// Render a native PlanResult JSON
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
                let raw = fs::read_to_string(&input).map_err(|e| e.to_string())?;
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
                serde_json::from_str(&fs::read_to_string(&problem).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
            let (assignments, plan_frozen) = load_assignments_flexible(&plan)?;
            // Problem freeze always applies; plan freeze is additive
            // (plan wins on the same job_id). Empty plan freeze keeps the problem list.
            let frozen = synaps_gridplan_rs::constraints::merge_expected_frozen(
                &problem.frozen_assignments,
                &plan_frozen,
            );
            let violations = check_plan(&problem, &assignments, &frozen);
            let payload = serde_json::json!({
                "verified_feasible": violations.is_empty(),
                "hard_violation_count": violations.len(),
                "violations": violations,
                "claim_level": "experiment",
                "engine": "synaps_gridplan_rs"
            });
            println!("{}", serde_json::to_string_pretty(&payload).unwrap());
            Ok(if violations.is_empty() {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(2)
            })
        }
        Commands::Report { input, format } => {
            let plan: PlanResult =
                serde_json::from_str(&fs::read_to_string(&input).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
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
    let raw = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let v: serde_json::Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    if looks_like_python_cli_result(&v) {
        return assignments_from_python_cli(&v);
    }
    if let Ok(plan) = serde_json::from_value::<PlanResult>(v.clone()) {
        return Ok((plan.assignments, vec![]));
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
        let frozen = v
            .pointer("/outcome/frozen_assignments")
            .cloned()
            .and_then(|x| serde_json::from_value::<Vec<FrozenAssignment>>(x).ok())
            .unwrap_or_default();
        return Ok((out, frozen));
    }
    Err("unsupported plan JSON for check".into())
}
