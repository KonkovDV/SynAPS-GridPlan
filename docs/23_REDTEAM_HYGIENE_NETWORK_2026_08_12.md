# Red Team 21 — hygiene + network_constraints (2026-08-12)

> Local. Claim level: experiment.

## Scope

Follow-up to deep evaluation of HEAD `23d9d08` (0.1.9): README drift, pin
guards, RES charts, explicit `SimultaneousOutageBan` (not N-1), pilot data list.

## Attacks attempted

| ID | Attack | Result |
| --- | --- | --- |
| H1 | README claims old pin / 0.1.3 | **Fixed** — README synced to versions.py |
| H2 | Demo runs stale site-packages | Documented + force-reinstall note; pin smoke test |
| H3 | Overclaim network as N-1 | Ban model docstring + domain_attributes forbid N-1 wording |
| H4 | Overlapping interruption on banned asset pair verifies | **Caught** — `SIMULTANEOUS_OUTAGE_BAN` + adversarial test |
| H5 | RES GREED breaks after ban on ПС-110 T-1 pair | Must stay verified (crew/day separation already serializes) |
| H6 | Charts invent numbers | Charts cite `rosseti_res_results.json` only |

## Residual risks (honest)

- Ban is combinatorial only — no load-flow, no consumer groups, no SAIDI.
- Solver does not *optimize under* bans inside GREED (post-check fail-closed);
  if GREED places a banned overlap, plan becomes error (acceptable for v0.1.10).
- Benchmark JSON remains gitignored — re-run before jury demo.

## Verdict

Ship as **0.1.10**: documentation honesty + minimal `network_constraints` surface
without pretending electrical security analysis.
