# SynAPS-GridPlan

Scheduler for crew- and window-constrained maintenance (ТОиР) on power-grid
assets. Thin domain layer on [SynAPS](https://github.com/KonkovDV/SynAPS),
with a Rust checker for the same constraints.

| | |
| --- | --- |
| Version | **0.1.2** |
| Default branch | `main` |
| SynAPS pin | [`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169) |
| Maturity | ISO 16290 TRL 4 (lab fixtures). Not a plant pilot. |
| Pitch | [SynAPS-GridPlan.pdf](SynAPS-GridPlan.pdf) (22 slides, Russian) |

What it does: assign crews to jobs under qualifications, outage windows,
spares (one stock unit per listed part), linear precedence, frozen ПЛ rows,
and explicit “these two assets must not be out together” bans. A second
checker, independent of the search, rejects a plan that breaks those rules.

What it does not do: SCADA, EMS, GIS, failure prediction, N-1 load-flow,
SAIDI optimisation, BOM-quantity ЗИП, join/fan-out predecessor graphs, or
replace an EAM / 1С:ТОИР suite. Risk scores in reports are advisory proxies,
not a risk engine. The SynAPS kernel night-window analog (5k ops, per-op 8 h
windows, no machine calendar) did not reach full coverage (hashed ratio
0.75–0.88 on 5k@8, three seeds); GridPlan emergency / night work is **not**
that kernel ladder and is not N-1. Kernel `WorkCenter.calendar` is encoded
by CP-SAT/ALNS/LBBD (occupancy in one shift) and clipped on greedy-family
configs. Auto-route stays `CALENDAR_AWARE`. Kernel pin is `6178c93` after the
ADR-0004 regression (fail-closed coverage, calendar encode, kernel claims-lint
on that SHA). KI-N12 stays closed; this is a new pin, not a reopen. Not the
diverged local 0.1.10 tree.

The checked campaign-shaped demo is synthetic РЭС «Северный» (55 jobs).
Generic feeder modes `medium` (200) and `stress` (600) are packed so GREED
verifies; calendar FIFO does not. 50k/500k runs in the SynAPS README are a
different domain — not this product.

GREED and FIFO are heuristics (`heuristic_feasible`). Only CP-SAT may be
called `optimal`, and only when the solver proves it.

## Evidence (synthetic)

| Result | Where |
| --- | --- |
| GREED builds a checked plan on synthetic РЭС «Северный»; FIFO does not | `tests/test_res_severny.py`, `benchmark/results/jury_report.md` |
| CP-SAT proves optimal makespan on that instance (dual bound = achieved) | `test_res_cpsat_proves_optimal_makespan` (pytest marker `slow`) |
| Local replan keeps frozen ПЛ rows | same tests, Scenario B |
| Generation-shaped fixture (GRES-block) GREED-clean; FIFO is not | `tests/test_gres_block.py` |
| Emergency-restoration day (synthetic узел «Восточный», СТО 17330282 / приказ № 289 chain): GREED clean, FIFO breaks 27 rules; frozen ПЛ row survives replan | `tests/test_emergency_day.py`, `benchmark/results/emergency_day_report.md` |
| Generic 200/600-job feeder: GREED verified-clean; FIFO breaks windows | `tests/test_scale_feeder.py`, `benchmark/results/scale_report.md` |
| Checker catches overlap, ЗИП, quals, short duration, unknown ops | `tests/test_adversarial_*.py` |

РЭС «Северный» copies public equipment *types* and industry norms. It is not
a named Россети site and not production data.

## Install

Python ≥ 3.12. SynAPS is pinned by commit, not by branch.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python -m synaps_gridplan version
python -m pytest -q -m "not slow"
```

`version` must print this checkout and SynAPS pin `6178c93…`. If `source` is a
copy under `site-packages` instead of `<repo>/src/synaps_gridplan`, reinstall:

```bash
python -m pip install -e ".[dev]" --force-reinstall --no-deps
```

## Commands

Verified jury demo (synthetic РЭС «Северный» — GREED checks clean, FIFO does not):

```bash
python benchmark/jury_benchmark.py
```

Small feeder that GREED verifies on this pin (`exit 0`):

```bash
python -m synaps_gridplan synthesize --mode small --seed 12 -o feeder.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
python -m synaps_gridplan report result.json --format markdown
```

Emergency-restoration day (synthetic узел «Восточный», regulatory chain):

```bash
python benchmark/emergency_day_benchmark.py
```

Campaign-scale feeder (200 and 600 jobs, GREED verifies):

```bash
python benchmark/scale_benchmark.py
```

Generation-shaped fixture (synthetic, not a live plant):

```bash
python -m synaps_gridplan synthesize --mode gres-block --seed 42 -o gres.json
```

Optional Rust checker. For a verified plan use the Python jury command above.

```bash
cd native/synaps-gridplan-rs
cargo test
```

`gres-block` synthesis is Python-only. Native `synthesize --mode gres-block`
exits with an error on purpose.

### Exit codes and fail-closed

`solve` always writes a plan JSON. The process exit code is the checker, not
“did GREED crash”:

| Exit | Meaning |
| --- | --- |
| **0** | Verified plan: `verified_feasible=true`, zero hard violations |
| **2** | Plan written, but the independent checker found hard violations |
| **1** | Usage / unexpected error |

GREED does not model asset exclusivity. The default small-feeder seed
(`--seed 42`) is the **fail-closed** example: **exit 2**,
`verified_feasible=false`, kind `ASSET_OVERLAP`. That is the product working,
not a broken install. The verified small seed on this pin is **12**, above.

```bash
python -m synaps_gridplan synthesize --mode small --seed 42 -o feeder.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
# exit 2, ASSET_OVERLAP — fail-closed
```

Native FIFO on the same seed also exits **2**.

## Layout

```
src/synaps_gridplan/        Python package
native/synaps-gridplan-rs/  Rust FIFO + checks
schemas/                    JSON Schema
benchmark/                  synthetic РЭС / jury / emergency-day / scale runners
tests/
APPLICATION.md              MIK application brief (Russian)
SynAPS-GridPlan.pdf         22-slide MIK pitch (Russian)
requirements-lock.txt       Linux pin of Python deps + SynAPS SHA
```

## License

MIT — [LICENSE](LICENSE).
