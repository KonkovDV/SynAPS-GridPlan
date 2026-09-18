# GridPlan Red Team 23 — chain occupancy and TRL 4 (2026-08-15)

Local RFC (gitignored). Publish surface: `CHANGELOG.md` 0.1.14, `README.md`,
`tests/test_gres_block.py`, `tests/test_adversarial_rt20.py`, native
`constraints.rs`.

## Requirements mapped

| Source | Requirement | GridPlan response |
| --- | --- | --- |
| Product | Fail-closed ТОиР contour on SynAPS | unchanged kernel; notary semantics tightened |
| МИК «Энергия будущего» (i.moscow, to 20.08.2026) | TRL 4+ | ISO 16290 TRL **4** laboratory breadboard. Not a filed-win claim. |
| Россети (press, 2026-07) | digitalisation, automation, data, cyber, equipment | Core is scheduling automation. Not cyber, not OEM. |
| ISO 16290:2013 | TRL 4 = lab breadboard; TRL 6 = relevant/pilot model | Explicit `ISO16290_TRL = 4`. Forbid УГТ 6+. |
| Goel et al., EJOR 2013 | Asset down from first disconnect to last reconnect | Ban occupancy = precedence-chain hull |
| Rodriguez et al., IEEE TPWRS 2018 | Unit unavailable under maintenance; crews; windows | Encoded; not hydro MILP |
| Fu/Shahidehpour 2007; Wang/Zhong 2015; 2025–26 IEEE N-1 GMS | N-1 / reserve / CVaR | **Refused.** Explicit ban only. |

## P0 closed

Pairwise job intervals missed a GTU-2 isolation sitting in the gap of a GTU-1
isolate→test chain. Hull of the precedence component now occupies that gap.
Independent jobs without a predecessor edge are not hulled (control in RT20).

Python + Rust. GREED on stock GRES still verifies (no gap). RES GREED must
remain green (hull does not invent edges).

## Residuals

N-1, SAIDI, live EL5, CVaR, unit commitment, ISO 55000 certification,
shift-aware construction, native `gres-block` synthesizer.
