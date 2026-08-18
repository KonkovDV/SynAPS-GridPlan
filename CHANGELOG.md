# Changelog

## 0.1.1 — 2026-08-18 (emergency-day detail pass)

The emergency-day instance is deepened to the full regulatory restoration
chain (СТО 17330282.29.240.004-2008 / Приказ Минэнерго № 289 stages):
per-apparatus локализация (switching crew) → осмотр/облёт → ремонт →
опробование/испытания → ввод в работу, ДГУ with priority to a соцобъект
(ФАП), transfer of ТП from ДГУ back to the main scheme after the feeding
center is re-energised, and the 0.4 kV private-sector tail late at night.
23 jobs / 10 assets / 8 crews (incl. оперативный персонал ОП-1).
GREED verified-clean; FIFO breaks 27 hard rules; replan of the 3-job
ВЛ-110 chain keeps the frozen ПЛ row unmoved; determinism unchanged.
Finding recorded in the internal jury pack: the adapter compiles only
linear predecessor chains (engine forbids cross-order precedence) — the
GridPlan checker catches dropped edges fail-closed; the instance is
linear by construction and a linearity guard test is added.
Report regenerated: `benchmark/results/emergency_day_report.md`.

## 0.1.1 — 2026-08-18 (emergency-day scenario)

New synthetic benchmark `benchmark/emergency_day_benchmark.py`: an
emergency-restoration day (узел «Восточный») shaped by the public
18.08.2026 news about the особый режим in the Moscow-region grid —
dispatcher-issued emergency outage windows, inspection → repair → test
chains on a 110 kV feed, ДГУ hook-up jobs for de-energised ТП, and one
pre-attack frozen ПЛ row. GREED builds the day verified-clean; calendar
FIFO breaks it (17 hard violations); replan after a repeat БПЛА survey
keeps the frozen ПЛ row unmoved; two GREED runs are bit-identical.
Guarded by `tests/test_emergency_day.py` (7 tests; 91 total).
Report: `benchmark/results/emergency_day_report.md`. Product claims
unchanged (synthetic, experiment, not a pilot).

## 0.1.1 — 2026-08-17 (application brief)

Public `APPLICATION.md` states the marathon customer (ПАО «Россети»),
team (single author; no invented expert), bottom-up TAM/SAM/SOM, and the
pilot ask. `requirements-lock.txt` pins the same SynAPS SHA on Linux
(`uv pip compile --python-platform linux`). Product claims unchanged.

## 0.1.1 — 2026-08-16 (engine pin)

Revalidated against SynAPS
[`bd09d13`](https://github.com/KonkovDV/SynAPS/commit/bd09d13561b3bd690845d07546def59b4521b16c)
after the engine CI close (native-repair skip reasons without the Rust wheel,
ALNS seed stub, ruff/mypy, control-plane 429, Fastify/AJV `num_workers: null`
coerced to 0 no longer 500s `/api/v1/solve`, function-length ratchet, `uv`
lock-check, Linux lockfile without Windows `tzdata`). Product claims unchanged.

## 0.1.1 — 2026-08-15

Public contest packet: crew- and window-constrained ТОиР scheduling on SynAPS.

- Assign crews under qualifications, outage windows, spares, precedence,
  frozen ПЛ rows, and explicit simultaneous-outage bans.
- Independent checker (Python and Rust). A plan with hard violations is not
  marked verified. Heuristic GREED/FIFO never report `optimal`.
- Synthetic РЭС «Северный»: GREED verifies, calendar FIFO does not. CP-SAT
  can prove optimal makespan on that instance (pytest marker `slow`).
- Synthetic GRES-block fixture. ISO 16290 TRL 4 (lab). Not a plant pilot.
- README documents fail-closed CLI: `solve` exit 2 means the checker
  rejected the plan (default `small --seed 42` is ASSET_OVERLAP, not a crash).
  Verified demos: `benchmark/jury_benchmark.py` or `--seed 12`.
- Native `check` accepts Python CLI JSON via `outcome.id_map`. Domain kind
  aliases (`UNKNOWN_JOB` ↔ `UNKNOWN_OPERATION`) are tabulated in the Rust
  README and guarded by `tests/test_native_parity.py`.
