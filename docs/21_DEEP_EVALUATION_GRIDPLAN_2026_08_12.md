# Deep evaluation — SynAPS-GridPlan (2026-08-12)

> **ARCHIVE. Do not attach to the MIK application.** Snapshot of public HEAD
> `23d9d08` (0.1.9) and pin `6fd3393`. Current packet is **0.1.1** / `bd09d13`.
> Use `docs/00_README.md` and `docs/02_APPLICATION_DRAFT.md`.

> Local application / Marathon evidence. Not part of the public publish surface
> (`/docs/` is gitignored). Source: stakeholder hyper-review of HEAD `23d9d08`
> (0.1.9), upstream pin `6fd3393`. Validated against repo on 2026-08-12.

## Short verdict

GridPlan moved from a demo sketch to a careful **engineering prototype** with a
subject-matter ТОиР benchmark. Strongest assets: fail-closed checks, frozen
assignments, outage windows, emergency replan, Rust contour, CP-SAT optimality
proof on a small synthetic instance.

It is **not** an industrial Россети system and **not** a full АСУ ТОиР.
Correct claim: deterministic compute core for resource-constrained maintenance /
outage campaign planning that plugs into existing АСУ ТОиР, CIM, and dispatch.

Scores (reviewer): technical base 8/10 · domain readiness 6/10 · industrial 2/10 ·
honest application readiness 7/10 · scientific idea 8/10.

Main missing layer: electrical topology + outage consequence (недоотпуск / N-1).
Commercial strategy: do not compete with АСУ ТОиР — offer them a verifiable
optimization layer.

## Alignment check (repo vs review)

| Review claim | Repo fact (2026-08-12) |
| --- | --- |
| HEAD `23d9d08`, version 0.1.9 | Confirmed |
| Upstream pin `6fd3393` | Confirmed in `versions.py` / `pyproject` |
| README may be stale | **Confirmed drift** — README still showed 0.1.3 / `1fa1470`; corrected in follow-up |
| Benchmark JSON may lag | `rosseti_res_results.json` still tagged 0.1.8 / `9694fc5` until re-run |
| CP-SAT OPTIMAL / gap 0% on makespan | Still the core Scenario D claim |
| РЭС «Северный» must not be called a real site | Enforced in README + claim tables |
| SynAPS later commit `5168fc7` (ratchet only) | Optional pin bump; functional algebra of RT-20 is in `6fd3393` |

## What to say / not say

Use the Russian positioning from the review §8–§10. Do **not** claim network
control, SAIDI cuts, industrial readiness, or a Россети pilot.

## Marathon track

Primary customer narrative: **Россети** — ремонтная кампания электросетевого
комплекса. Not Inter RAO robotics, not СберСити storage, not EL5 renewables.

## Plan until deadline (from review)

| By | Work |
| --- | --- |
| **14 Aug** | Version/README sync; pytest artifact; refresh RES JSON; claims table; FIFO/GREED/CPSAT + disruption charts; short CLI recording |
| **16 Aug** | Minimal `network_constraints` (coincidence graph — **not** N-1); optional proxy недоотпуск only with explicit inputs; pilot data request list |
| **18 Aug** | Single-scenario application pack; EAM integration story; pilot stage; economics as **methodology**, not invented ₽ |
| **20 Aug** | Legal/MIK checks; submit; archive PDF + package |

## Follow-up executed in-repo (same day)

1. README rewritten to 0.1.9 + pin `6fd3393` + claims/evidence table.
2. This evaluation archived under `docs/` (local only).
3. Further: refresh benchmark JSON, pytest log artifact, pin-consistency test —
   see working session notes.
