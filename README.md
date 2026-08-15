# SynAPS-GridPlan

Scheduler for crew- and window-constrained maintenance (ТОиР) on power-grid
assets. Thin domain layer on [SynAPS](https://github.com/KonkovDV/SynAPS),
with a Rust checker for the same constraints.

| | |
| --- | --- |
| Version | **0.1.1** |
| SynAPS pin | [`c6b8c11`](https://github.com/KonkovDV/SynAPS/commit/c6b8c11fb677118296e6537a861c3e5dc527f842) |
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

```bash
python -m synaps_gridplan synthesize --mode small --seed 42 -o feeder.json
python -m synaps_gridplan synthesize --mode gres-block --seed 42 -o gres.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
python -m synaps_gridplan report result.json --format markdown
python benchmark/jury_benchmark.py
```

Optional Rust checker:

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
benchmark/                  synthetic РЭС / jury runners
tests/
APPLICATION.md              MIK application brief (Russian)
```

## License

MIT — [LICENSE](LICENSE).
