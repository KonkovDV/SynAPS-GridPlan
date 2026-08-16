# Changelog

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
