# Engineering Audit — SynAPS-GridPlan (2026-08-11)

**Authority:** code inspection of local working trees + GitHub remotes.  
**Claim level:** engineering audit only. Not a customer pilot report.

## 1. Commits

| Repo | Branch | Commit | Note |
| --- | --- | --- | --- |
| [SynAPS-GridPlan](https://github.com/KonkovDV/SynAPS-GridPlan) | `main` | `02f3d73a1b76cc53b5f3ec2a36365b2e2f6177d7` | Package 0.1.0; commit message is an auto-checkpoint (cosmetic debt) |
| [SynAPS](https://github.com/KonkovDV/SynAPS) | `master` | `1fa147087d03a2c7598c0ff7af0bbbb8db584153` | Wave-14 RHC→ALNS / early-greedy fix |

Pre-fix GridPlan `pyproject.toml` depended on `SynAPS@master` (floating). Audit requires pinning to the SynAPS SHA above.

## 2. Repository structure (publish surface)

```
.github/workflows/ci.yml
.gitignore                 # /docs/ and most *.md excluded from publish
README.md, LICENSE, SECURITY.md, CHANGELOG.md
pyproject.toml
schemas/                   # v1 JSON Schema (loose)
src/synaps_gridplan/       # product package
tests/                     # 5 core tests at audit time
docs/                      # LOCAL ONLY — not published to GitHub
```

## 3. Modules and status

| Component | Path | Status | Evidence |
| --- | --- | --- | --- |
| Domain model v1 | `model.py` | IMPLEMENTED | Asset, FailureMode, RiskProfile, Crew, SparePart, OutageWindow, MaintenanceJob, GridPlanProblem + cross-ref validator |
| Risk → priority | `risk.py` | PARTIAL | `risk_score` → Order.priority only; not an objective / post-plan exposure metric |
| Adapter | `adapter.py` | PARTIAL | Compiles to ScheduleProblem; precedence → same-Order chains; travel → setup matrix; skills/spares → AuxiliaryResource |
| Frozen from windows | `adapter.frozen_assignments_from_windows` | PARTIAL | Picks **first eligible crew**; invents start at window.start — not true FrozenAssignment identity |
| Planner | `planner.py` | PARTIAL | `solve_schedule` / `repair_schedule` + FeasibilityChecker fail-closed; repair reuses base problem ids |
| Synthetic generator | `synthetic.py` | PARTIAL / EXPERIMENTAL | LCG seed OK; **`hash()` for travel** process-unstable; **`uuid4` defaults** make JSON non-reproducible |
| Reports | `report.py` | PARTIAL | JSON/CSV/Markdown; missing fingerprints, risk proxy table, crew util, spare shortages |
| CLI | `cli.py` | PARTIAL | `synthesize`, `solve`, `report`, `disrupt`; report path omits `schedule_problem` round-trip |
| Schemas v1 | `schemas/*.json` | PARTIAL | Thin envelopes; not field-complete |
| Schemas v2 | — | MISSING | |
| Outage containment check | — | MISSING | Windows only nudge release/due |
| Consumable ЗИП post-check | — | MISSING | SynAPS `pool_size` = concurrent capacity, not stock depletion |
| Plan diff / DisruptionEvent | — | MISSING | |
| Benchmark harness | — | MISSING | |
| Customer / EAM / SCADA / GIS | — | BLOCKED_BY_CUSTOMER_DATA | |
| CVaR / RUL / time-varying PoF | — | MISSING | Must not be claimed |
| Crew routing / VRP | — | MISSING | Travel minutes only |
| Shift calendars | — | MISSING | |

## 4. CLI commands (as of audit)

| Command | Status |
| --- | --- |
| `synthesize` | IMPLEMENTED |
| `solve` | IMPLEMENTED |
| `report` | PARTIAL |
| `disrupt` | PARTIAL (needs base `schedule_problem` in payload for correct repair) |

## 5. Tests (audit baseline)

`tests/test_gridplan_core.py` — synthesize provenance, adapter validity, risk ordering, GREED smoke, repair smoke.  
**MISSING at audit:** determinism, outage containment, frozen identity, spare shortage, CLI exit codes, schema v1 freeze, infeasible fail-closed cases.

## 6. Public schemas

- `gridplan-problem.schema.json` — `schema_version: gridplan.v1`
- `gridplan-result.schema.json` — outcome + schedule envelope

## 7. Solvers actually reachable via GridPlan

GridPlan passes `solver_config` through to SynAPS `solve_schedule`. **Supported if SynAPS supports them** (not re-implemented here):

| Config family | Status in SynAPS | Proven via GridPlan tests |
| --- | --- | --- |
| GREED | IMPLEMENTED | EXPERIMENTAL (smoke only) |
| CPSAT-* | IMPLEMENTED upstream | MISSING in GridPlan CI |
| BEAM / ALNS / LBBD / RHC-* | IMPLEMENTED upstream | MISSING in GridPlan CI |
| IncrementalRepair (`repair_schedule`) | IMPLEMENTED upstream | EXPERIMENTAL (smoke) |

Heuristic FEASIBLE ≠ OPTIMAL. Only CP-SAT/LBBD may claim optimality when SynAPS returns `optimal`.

## 8. Constraints — truth table

| # | Constraint | Status |
| --- | --- | --- |
| 1 | Unknown crew | PARTIAL (eligible list empty → may fail solve) |
| 2 | Qualifications | PARTIAL (eligible crews + skill aux) |
| 3 | No dual-book crew | IMPLEMENTED via SynAPS WC capacity |
| 4 | Horizon | PARTIAL (SynAPS horizon) |
| 5 | Precedence | PARTIAL (linear chains only) |
| 6 | Job inside allowed outage | MISSING (hard interval check) |
| 7 | Forbidden window | MISSING |
| 8 | Frozen immutable | MISSING (identity not stored) |
| 9 | Non-negative duration | IMPLEMENTED (Pydantic `ge=1`) |
| 10–12 | ЗИП stock / reserve / replenishment | MISSING / wrong semantics |
| 13 | Shift availability | MISSING |
| 14 | Travel time | PARTIAL (setup matrix) |
| 15 | Fail-closed hard violations | PARTIAL (SynAPS + GridPlan wrap) |

## 9. README promises vs proof

| README claim | Proof status |
| --- | --- |
| Domain model + adapter | IMPLEMENTED |
| Synthetic feeder | PARTIAL (non-deterministic IDs/travel) |
| Independent feasibility | IMPLEMENTED (via SynAPS checker) |
| Industrial deployment | Correctly **not claimed** |
| Customer validation | Correctly **not claimed** |
| “Risk-aware” (pyproject description) | PARTIAL — priority proxy only |

## 10. Must NOT claim

- Deployment at Россети / any DSO  
- ₽ savings, SAIDI/SAIFI improvement proven  
- PoF prediction / diagnostic certificate  
- SCADA / EAM / OMS / GIS integration  
- Full ТОиР platform / 1С:ТОИР replacement  
- Heuristic optimality without proof  
- Accuracy > 90%  
- Consumable ЗИП correctness until post-check exists  
- Outage-window compliance until hard check exists  

## 11. Allowed claim (current)

> On a **synthetic** feeder scenario, GridPlan compiles a maintenance problem to SynAPS, searches a schedule, and independently checks hard feasibility. Results are an **experiment**, not industrial proof.

## 12. Immediate remediation queue (priority)

1. Replace `hash()` + make UUIDs deterministic from seed. **DONE (0.1.1)**
2. Pin SynAPS dependency to commit SHA. **DONE (0.1.1)**
3. Hard outage-window containment for interruption jobs. **DONE (0.1.1)**
4. Explicit `FrozenAssignment` with immutability checks on repair. **DONE (0.1.1)**
5. ЗИП consumable post-check + honest limitation note. **DONE (0.1.1)**
6. Fingerprints in reports + reproducibility tests. **DONE (0.1.1)**

---

*Generated 2026-08-11. Updated after 0.1.1 remediation. Update again when HEAD moves.*
