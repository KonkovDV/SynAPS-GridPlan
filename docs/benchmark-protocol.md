# Benchmark protocol

## Purpose

Compare solvers on **synthetic** feeders. Tag all metrics `synthetic_experiment`.

## Methods

1. GREED (baseline heuristic)
2. CPSAT-* when OR-Tools is available in the environment
3. RHC / ALNS on larger instances (optional)
4. Incremental repair after disruption

FIFO / calendar baselines can be added without changing the GridPlan core.

## Recorded fields

`input_hash`, `seed`, `solver_config`, versions, `wall_time`, status,
`verified_feasible`, assignments, hard violations, risk proxy, plan churn
(via diff).

## Forbidden interpretations

Do not convert synthetic deltas into currency savings, SAIDI claims, or
«ready for deployment» statements.
