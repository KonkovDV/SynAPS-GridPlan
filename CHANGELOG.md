# Changelog

## Unreleased

## 0.1.4 — 2026-09-03

- World-practice mapping locked in ``PRACTICE.md`` and
  ``synaps_gridplan.practice`` (verified citations: Hydro-Québec TMS CP 2022,
  Energies 2025 mutex/windows, Goel & Meisel EJOR 2013 downtime hull, SOGL/OPC
  freeze vs OPI, Hexaly/ČEZ as a *different* FSM class). Plan JSON and
  markdown reports carry ``practice.layer`` /
  ``electrical_security=out_of_scope``. CLI ``practice``. Not a power-flow,
  N-1, SAIDI, or plant-pilot claim.

## 0.1.3 — 2026-09-03

- Canonical tree is origin ``main`` (this pin). The diverged local 0.1.10 /
  0.1.11 lab checkout is not the product.
- FIFO (Python and Rust): a problem with zero jobs is vacuously ``feasible``,
  not ``infeasible``. Guarded by overlap + native integration tests.

## 0.1.2 — 2026-08-30

- SynAPS pin bumped to
  [`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169)
  (ADR-0004). Regression: fail-closed coverage, CP-SAT/ALNS/LBBD encode a
  non-empty `WorkCenter.calendar` (greedy still clips), kernel claims-lint
  on that SHA. Not a courtesy float on ``main``. Not the diverged local
  0.1.10 / ``6fd3393`` tree. KI-N12 stays closed.
- Previous origin pin was
  [`54ebf9f`](https://github.com/KonkovDV/SynAPS/commit/54ebf9f32bc871cc27283331d7536c1068c7e606)
  (GridPlan #7). CI push trigger remains ``main`` only.

## 0.1.1 — 2026-08-18

Public contest packet on SynAPS
[`bd09d13`](https://github.com/KonkovDV/SynAPS/commit/bd09d13561b3bd690845d07546def59b4521b16c).
ISO 16290 TRL 4. Not a plant pilot.

- Crew- and window-constrained ТОиР on an independent fail-closed checker
  (Python and Rust). Heuristic GREED/FIFO never report `optimal`.
- Synthetic РЭС «Северный»: GREED verifies, calendar FIFO does not (107 hard
  violations). CP-SAT can prove optimal makespan (`slow`).
- Synthetic GRES-block. CLI `small --seed 42` is the fail-closed example
  (`ASSET_OVERLAP`); verified small seed on this pin is `--seed 12`.
- Emergency-restoration day (узел «Восточный»): full regulatory chain
  (СТО 17330282.29.240.004-2008 / приказ Минэнерго № 289), 23 jobs / 8 crews.
  GREED verified-clean; FIFO 27 hard violations; replan keeps the frozen ПЛ
  row. Lab instance, not a reconstruction of a live branch.
- Generic feeder `medium`/`stress` (200/600 jobs): packed as a campaign
  (one chain per asset, one outage, stock ≥ demand). GREED verifies; FIFO
  does not. `small --seed 42` remains the fail-closed ASSET_OVERLAP demo.
  50k engine runs are a different domain.
- Contest pitch PDF at repo root: `SynAPS-GridPlan.pdf` (22 slides, Russian).
- CLI `version` prints GridPlan version and the SynAPS pin. Editable install
  follows `src/` (no hatch `force-include` snapshot in `site-packages`).
  Emergency-day console banner is ASCII so Windows cp1251 demos do not crash.
- Honest limits in `APPLICATION.md`: linear predecessor chains only, ЗИП as
  one stock unit per listed part, KPI baseline taken from the DZO curator
  on P0 (not invented here).
- `APPLICATION.md` states the marathon customer (ПАО «Россети»), single
  author, bottom-up TAM/SAM/SOM. `requirements-lock.txt` pins the same
  SynAPS SHA on Linux.

## 0.1.1 — 2026-08-15

First public contest tree: independent checker, synthetic РЭС, native FIFO,
fail-closed CLI, kind aliases tabulated in the Rust README.
