# GridPlan Red Team 22 — GRES-block (2026-08-15)

Local RFC (gitignored under `docs/`). Publish surface: `CHANGELOG.md` 0.1.13,
`tests/test_gres_block.py`.

## Scope

Synthetic generation ТОиР on the existing `GridPlanProblem` contour.
Not live EL5 / Konakovskaya. Not N-1. Not SAIDI. Not unit-commitment.

Prior attacks reused: RT19 C1 unscheduled, RT20 G1 asset overlap / G2 crew /
ban, RT21 G11 per-op windows / G10 GREED≠optimal, G13 short duration,
consumable ЗИП (not SynAPS aux pool).

## Attacks

| ID | Attack | Result |
| --- | --- | --- |
| GRES-1 | GREED on stock seed=42 | **Holds.** `heuristic_feasible`, 9/9, empty notary. Status ≠ optimal. |
| GRES-2 | FIFO Python | **Fail-closed.** Windows / precedence / `ASSET_OVERLAP` / ban. Same class as РЭС A. |
| GRES-3 | Native FIFO+check on Python JSON | **Fail-closed** (parsed; 16 violations). Not a native synthesizer. |
| GRES-4 | Overlap both GTU isolations with **aligned** ПЛ windows | **`SIMULTANEOUS_OUTAGE_BAN`**, no `OUTAGE_WINDOW_VIOLATION`. Combinatorial, not load-flow. |
| GRES-5 | Weak forge into the other unit's day | BAN **and** window miss — insufficient as a BAN-only proof; GRES-4 is the proof. |
| GRES-6 | Online ПЭН overlapping GTU isolation | Ban **does not fire** (interruption-only). Residual, not N-1. |
| GRES-7 | Blade `available_quantity=1` | **`SPARE_PART_SHORTAGE`.** Consumable count, not concurrent pool. Stagger does not save qty=1. |
| GRES-8 | G11: three jobs, one 14 h window | GREED serializes isolate→repair→test inside clearance (touching OK). |
| GRES-9 | `seed` | UUID salt only. Topology (refs, days, ban pair) stable. |
| GRES-10 | CLI `--mode gres-block --assets 99` | **P0 closed.** Was silent ignore; now exit 2, no file. |
| GRES-11 | Claim leakage (EL5, N-1, SAIDI, OPTIMAL) | Labels `not_live_el5`, ban reason `not N-1`, GREED `heuristic_feasible`. |

## Residuals (do not “fix” into overclaim)

- Ban ≠ N-1 / topology / consumer undersupply.
- Online BOP unconstrained vs GTU outage.
- One mechanical crew is the bottleneck; instance is GREED-sized.
- Native `synthesize` has no `gres-block`.
- Empty shift/calendar/safety still unconstrained (notary-only when non-empty).
- `ASSET_OVERLAP` still interruption-only (pre-existing RT20 G1).
- Risk remains an advisory proxy.

## Forbidden statements after this wave

Live EL5, Konakovskaya dump, N-1, SAIDI, “FIFO solves GRES”, “GREED is optimal”,
“qty=1 is enough because outages do not overlap”, “we replaced 1С:ТОИР”.
