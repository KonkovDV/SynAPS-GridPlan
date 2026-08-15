//! Native GridPlan contour: JSON I/O, FIFO, post-checks, synthetic feeder.
//! GREED/CP-SAT stay in the Python package.

pub mod bridge;
pub mod constraints;
pub mod fifo;
pub mod fingerprint;
pub mod ids;
pub mod model;
pub mod report;
pub mod schedule;
pub mod synthetic;

pub use constraints::{check_plan, merge_expected_frozen, Violation};
pub use fifo::plan_fifo;
pub use fingerprint::{fingerprint_payload, stable_digest, stable_int};
pub use model::GridPlanProblem;
pub use schedule::PlanResult;
pub use synthetic::synthesize_feeder;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");
pub const SCHEMA_VERSION: &str = "gridplan.v1";
pub const CLAIM_LEVEL: &str = "experiment";
