# SynAPS-GridPlan

Scheduler for crew- and window-constrained maintenance (ТОиР) on power-grid
assets. Thin domain layer on [SynAPS](https://github.com/KonkovDV/SynAPS),
with a Rust checker for the same constraints.

| | |
| --- | --- |
| Version | **0.1.1** |
| SynAPS pin | [`bd09d13`](https://github.com/KonkovDV/SynAPS/commit/bd09d13561b3bd690845d07546def59b4521b16c) |
| Maturity | ISO 16290 TRL 4 (lab fixtures). Not a plant pilot. |

What it does: assign crews to jobs under qualifications, outage windows,
spares, precedence, frozen ПЛ rows, and explicit “these two assets must not
be out together” bans. A second checker, independent of the search, rejects
a plan that breaks those rules.

What it does not do: SCADA, EMS, GIS, failure prediction, N-1 load-flow,
SAIDI optimisation, or replace an EAM / 1С:ТОИР suite.

## Evidence (synthetic)

| Result | Where |
| --- | --- |
| GREED builds a checked plan on synthetic РЭС «Северный»; FIFO does not | `tests/test_res_severny.py`, `benchmark/results/jury_report.md` |
| CP-SAT proves optimal makespan on that instance (dual bound = achieved) | `test_res_cpsat_proves_optimal_makespan` (pytest marker `slow`) |
| Local replan keeps frozen ПЛ rows | same tests, Scenario B |
| Generation-shaped fixture (GRES-block) GREED-clean; FIFO is not | `tests/test_gres_block.py` |
| Emergency-restoration day (synthetic, shaped by public 18.08.2026 news): full chain «localize → repair → test → re-energize»; GREED clean, FIFO breaks 27 rules; frozen ПЛ row survives replan | `tests/test_emergency_day.py`, `benchmark/results/emergency_day_report.md` |
| Checker catches overlap, ЗИП, quals, short duration, unknown ops | `tests/test_adversarial_*.py` |

РЭС «Северный» copies public equipment *types* and industry norms. It is not
a named Россети site and not production data.

GREED and FIFO are heuristics (`heuristic_feasible`). Only CP-SAT may be
called `optimal`, and only when the solver proves it.

## Install

Python ≥ 3.12. SynAPS is pinned by commit, not by branch.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python -m pytest -q -m "not slow"
```

On Windows after `git pull`, reinstall the editable package — hatchling can
leave a stale copy in `site-packages`.

### Exit codes and fail-closed

`solve` always writes a plan JSON. The process exit code is the checker, not
“did GREED crash”:

| Exit | Meaning |
| --- | --- |
| **0** | Verified plan: `verified_feasible=true`, zero hard violations |
| **2** | Plan written, but the independent checker found hard violations |
| **1** | Usage / unexpected error |

GREED does not model asset exclusivity. On the default small feeder
(`--seed 42`) it returns **exit 2**, `verified_feasible=false`, kind
`ASSET_OVERLAP`. That is the product working, not a broken install.

### Commands

Jury demo (synthetic РЭС «Северный» — GREED verifies, FIFO does not):

```bash
python benchmark/jury_benchmark.py
```

Emergency-restoration day (synthetic узел «Восточный», shaped by public
18.08.2026 news):

```bash
python benchmark/emergency_day_benchmark.py
```

Small feeder — expected fail-closed on the default seed:

```bash
python -m synaps_gridplan synthesize --mode small --seed 42 -o feeder.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
# exit 2, ASSET_OVERLAP — fail-closed
```

Same generator, seed that GREED verifies on this pin:

```bash
python -m synaps_gridplan synthesize --mode small --seed 12 -o feeder.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
python -m synaps_gridplan report result.json --format markdown
```

Generation-shaped fixture (synthetic, not a live plant):

```bash
python -m synaps_gridplan synthesize --mode gres-block --seed 42 -o gres.json
```

Optional Rust checker (FIFO on `small --seed 42` also exits **2** — same
fail-closed). For a verified plan use the Python jury command above.

```bash
cd native/synaps-gridplan-rs
cargo test
cargo run -- synthesize --mode small --seed 42 -o feeder.json
cargo run -- solve feeder.json --engine fifo -o plan.json
```

`gres-block` synthesis is Python-only. Native `synthesize --mode gres-block`
exits with an error on purpose.

## Layout

```
src/synaps_gridplan/        Python package
native/synaps-gridplan-rs/  Rust FIFO + checks
schemas/                    JSON Schema
benchmark/                  synthetic РЭС / jury / emergency-day runners
tests/
APPLICATION.md              MIK application brief (Russian)
requirements-lock.txt       Linux pin of Python deps + SynAPS SHA
```

## License

MIT — [LICENSE](LICENSE).
