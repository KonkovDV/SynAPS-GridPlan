# RED TEAM — Rust contour 0.1.0 × Marathon (2026-08-11)

**Scope audited:** `native/synaps-gridplan-rs` + packaging in SynAPS-GridPlan 0.1.3.  
**Mode:** adversarial. Kill overclaims before a Marathon expert does.

## Verdict

Rust wedge is a **legitimate engineering maturity upgrade** (native FIFO +
fail-closed checks + parity tokens). It does **not** move Marathon hard-gates:
no 2024–2025 deployment case, no УГТ 6, no “no analogs”, no Россети pilot.

Honest effect on scoring: **+0 to УГТ narrative (still 4–5)**, maybe slight
“technological maturity” color for День заказчика — **zero** on критерий
«кейс внедрения».

## Attack surface (what we must not say)

| Claim temptation | Red Team kill | Honest wording |
| --- | --- | --- |
| «Переписали ядро на Rust / быстрее всех» | GREED/CPSAT/LBBD still Python SynAPS | «Нативный контур проверки + FIFO; поиск — SynAPS» |
| «УГТ 6 потому что Rust+CI» | УГТ 6 = пилот на инфре партнёра | УГТ 4–5: код+CI+синтетика |
| «Нет аналогов» | Hexaly@ČEZ, Maximo Optimizer, Timefold | Аналоги в мире есть; РФ-ниша — EAM без combo-ядра |
| «Внедрено / экономия ₽» | Только synthetic_experiment | Experiment / synthetic only |
| «Rust = доказательство оптимальности» | FIFO is heuristic | `heuristic_feasible` |

## Technical audit (code)

| Check | Result |
| --- | --- |
| `stable_int` / fingerprint / uuid5 parity with Python | PASS (fixtures locked) |
| FIFO deterministic | PASS |
| `infeasible` / `frozen-conflict` fail-closed | PASS |
| GREED in Rust | ABSENT by design — subprocess bridge only |
| Claims in README/crate docs | Experiment-bounded |
| Marathon docs published | NO (`/docs/` gitignored) |

## Residual risks

1. Expert asks «где кейс 2024–2025?» — Rust silent.  
2. Expert compares to Hexaly DSO case — we must concede industry analog.  
3. Bridge GREED fails if Python env missing — document, do not hide.  
4. Domain FIFO ≠ Python FIFO assignment IDs (job/crew vs SynAPS op/wc) — document; metrics comparable, not byte-identical schedules.

## Go / no-go for push

**GO** to publish code as 0.1.3 engineering release.  
**NO-GO** to change Marathon application claims based on this commit alone.
