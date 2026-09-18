# RED TEAM — 0.1.4 deep audit + optimization (2026-08-11)

**Scope:** Python `synaps_gridplan` 0.1.3→0.1.4 + Rust `synaps-gridplan-rs` 0.1.0.  
**Mode:** adversarial. Kill overclaims and fail-closed holes before Marathon expert does.

## Verdict

0.1.4 closes the worst P0s found in the dual audit. **Still not** a Marathon
hard-gate pass: no 2024–2025 deployment case, УГТ stays 4–5, no “no analogs”.
Rust is a verification contour, not a SynAPS port.

## P0 fixed in 0.1.4

| # | Bug | Fix |
|---|---|---|
| 1 | Heuristic `status="optimal"` leaked into `PlanOutcome.status` | Downgrade to `feasible` for heuristic prefixes |
| 2 | Adapter outage bounds used unapproved/forbidden windows | Mirror `_outage_violations` filters; non-interruption jobs keep own bounds |
| 3 | `config_hash` omitted solve kwargs / frozen set | Include full effective envelope |
| 4 | Disrupt did not freeze rest of base plan | Auto-freeze non-disrupted assignments |
| 5 | Rust `check` CLI ignored problem frozen | Always enforce `problem.frozen_assignments` |
| 6 | GREED bridge masked exit code 2 as success | Propagate exit code |
| 7 | Rust no crew-overlap / duplicate-job check | Added `CREW_OVERLAP` + `DUPLICATE_JOB_ASSIGNMENT` |
| 8 | Rust FIFO empty-eligibility diverged from Python | Fall back to all crews (post-check flags mismatch) |
| 9 | Rust FIFO tie-break used UUID bytes | Tie-break on `crew.code` then UUID |
| 10 | Risk metric `unserved_critical_assets` counted jobs | Renamed `unserved_critical_jobs` |

## P1 fixed / improved

- Rust release profile: `lto=fat`, `codegen-units=1`, `panic=abort`, `strip=true`, `opt-level=3`
- Rust FIFO: no full `jobs.clone()`; sorted `&MaintenanceJob` refs
- Rust: `checked_add_signed` for duration; horizon underflow guard
- Rust: sorted qualification lists in violation messages (deterministic)
- Python: `risk_metrics` late-job exposure kept in `overdue_risk_exposure`

## Still open (documented, not hidden)

| Risk | Honest boundary |
|---|---|
| Precedence DAG not fully compiled into SynAPS | Only linear chains; post-check catches rest |
| Rust synthetic ≠ Python synthetic instance | Different generator; parity is primitive-level |
| Rust `input_hash` ≠ Python `input_hash` | Different serde shape; document |
| `replan_after_disruption` `solver_config` label only | SynAPS repair API does not accept config |
| Legacy frozen-window over-pin | Prefer explicit `FrozenAssignment` |
| No crew-overlap in Python post-check | Rust only; Python relies on SynAPS checker |

## Marathon claim boundary (unchanged)

- УГТ 4–5, not 6+
- Experiment / synthetic only
- No deployment case 2024–2025
- Competitors exist (Hexaly, Maximo, Timefold)
- Rust = engineering maturity, not product proof

## Go / no-go

**GO** to publish 0.1.4 as engineering release.  
**NO-GO** to upgrade Marathon application claims.
