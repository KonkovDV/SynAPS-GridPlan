# Changelog

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
