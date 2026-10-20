# Benchmark protocol

## Purpose

Run solvers on **synthetic** GridPlan instances and keep each report next to
the command that wrote it. Metrics carry `synthetic_experiment`. A number
reaches the README only through `docs/CLAIMS_REGISTRY.md`. Instances from
different generators do not add up to one scale.

## Solvers

- `FIFO`: calendar baseline. Earliest `due_date` first, on the eligible crew
  that frees up first, after `release_date`, inside the horizon and
  `latest_finish`. It does not wait for shifts, outage windows, or travel.
- `FIFO-W`: the same earliest-due order among ready jobs, placed inside the
  shift and the approved outage window, after travel. A successor waits for
  its predecessor.
- `GREED`: the SynAPS heuristic on the compiled `ScheduleProblem`.
- `CPSAT-10`, `CPSAT-30`: OR-Tools CP-SAT through SynAPS with a 10 s or 30 s
  budget.
- `replan_after_disruption`: local replan that keeps frozen ПЛ rows.

Other SynAPS portfolio names pass through `plan_with_config`. Names starting
with `FIFO`, `GREED`, `BEAM`, `ALNS`, `RHC`, or `repair:` get
`claim_status = heuristic_feasible` and never `optimal`.

## Scripts

| Script | Instance | What it writes |
| --- | --- | --- |
| `benchmark/jury_benchmark.py` | РЭС «Северный» (`res_severny_benchmark.build_res_problem`) | `results/jury_report.md`. A: FIFO and GREED. B: two frozen ПЛ rows, a disrupted set, a replan. C: GREED twice. D, with `--cpsat`: CPSAT-30 on the same JSON. E: FIFO-W on the same JSON. F: a separate 08–17 shift slice under GREED and CPSAT-10 |
| `benchmark/emergency_day_benchmark.py` | Emergency restoration day, узел «Восточный» | `results/emergency_day_report.md`: FIFO and GREED, a replan around a frozen ПЛ row, a repeat run |
| `benchmark/scale_benchmark.py` | Campaign feeder, `medium` and `stress`, seed 12 | `results/scale_report.md`: GREED and FIFO |
| `benchmark/scale_budget.py` | `scale-2k`, `scale-5k` | Wall time and tracemalloc peak on stdout. A process log, not a registry row |
| `benchmark/res_severny_benchmark.py` | РЭС «Северный» | `results/res_severny_report.md`, not committed: A to C as in the jury run, then CPSAT-30 twice and the GREED makespan gap to the dual bound |
| `benchmark/run_benchmark.py` | `small` feeder, seeds 42 and 7 | `instances/feeder-*.json`, `scenarios/disruption.json`, `results/latest.json`: FIFO and GREED rows. CPSAT-10 only through `run(try_cpsat=True)` |

The jury, emergency-day, and scale reports are committed. Rerun the jury
report with `--cpsat`; without it section D disappears, and the tests require
it. Wall-time cells change on every run: that is the machine of the run, not
an SLA. Any other diff in a committed report is a change to read.

## Recorded fields

Every plan's metadata carries `input_hash` and `config_hash` (SHA-256 of the
canonical JSON), `gridplan_version`, `synaps_commit`, `data_provenance`,
`claim_level`, `claim_status`, the engine and GridPlan violation kinds, and
`unenforced_fields`. Reports add `verified_feasible`, the hard-violation
count with its breakdown, wall time, and a SHA-256 plan fingerprint where a
repeat run is compared. `run_benchmark.py` rows also keep seed, coverage,
tardiness, makespan, and the risk-proxy delta.

## Forbidden interpretations

Do not convert synthetic deltas into currency savings, SAIDI claims, or
«ready for deployment» statements. A heuristic plan is not an optimum.
CP-SAT `optimal` is an optimum of the compiled model and its makespan: asset
exclusivity, pair bans, and spare stock stay in the post-check.
