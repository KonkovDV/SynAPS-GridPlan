//! Optional GREED bridge: shell out to Python `synaps-gridplan` CLI.
//!
//! This is intentionally thin. Native crate does not reimplement SynAPS.

use std::path::{Path, PathBuf};
use std::process::Command;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum BridgeError {
    #[error("python gridplan CLI failed: {0}")]
    Command(String),
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
}

/// Resolve python executable (override with GRIDPLAN_PYTHON).
pub fn python_bin() -> String {
    std::env::var("GRIDPLAN_PYTHON").unwrap_or_else(|_| "python".into())
}

/// Run `python -m synaps_gridplan solve <input> --solver GREED -o <output>`.
/// Returns the process exit code (0 = ok, 2 = fail-closed/infeasible with JSON).
pub fn solve_greed_via_python(input: &Path, output: &Path) -> Result<i32, BridgeError> {
    let status = Command::new(python_bin())
        .args([
            "-m",
            "synaps_gridplan",
            "solve",
            &input.display().to_string(),
            "--solver",
            "GREED",
            "-o",
            &output.display().to_string(),
        ])
        .status()?;
    let code = status.code().unwrap_or(1);
    if output.exists() {
        Ok(code)
    } else {
        Err(BridgeError::Command(format!(
            "exit={code}; ensure `pip install -e .` in SynAPS-GridPlan"
        )))
    }
}

pub fn default_bridge_note() -> &'static str {
    "GREED bridge uses Python SynAPS-GridPlan; Rust owns FIFO + post-checks only."
}

pub fn suggest_install_path(repo_root: &Path) -> PathBuf {
    repo_root.to_path_buf()
}
