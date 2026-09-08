# Changelog

## 0.1.6 — 2026-09-08

Second fail-closed pass on the published 0.1.5 tree. SynAPS pin remains
[`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169).
Self-assessed ISO 16290 TRL 4. Not a plant pilot.

### Verification

- Legacy ``outage_windows[].frozen`` is a domain obligation on independent
  ``check`` (Python and native), not only a compile-time pin for solve.
- Naive assignment timestamps are ``INVALID_ASSIGNMENT_TIME``, not a
  ``TypeError``. Native ``check`` no longer appends ``Z`` to naive Python
  assignment instants.
- Outcome ``iso16290_trl`` is the package self-assessment. A different value
  in ``domain_attributes`` is recorded as ``claimed_iso16290_trl`` only.
- CLI reads apply the byte quota to bytes actually read. Markdown reports
  flatten newlines and backticks in interpolated text.
- Native documents reject unknown top-level fields and extra calendar keys.
- Synthetic ``small`` feeders no longer set ``outage_windows[].frozen``;
  that flag is a real lock on independent check. Use ``frozen-conflict`` or
  explicit ``FrozenAssignment`` rows when the demo is about ПЛ.

### Lab gates

- Committed Pydantic nested schema inventory, pattern secret scan, pytest
  120s timeout and CI ``timeout-minutes``. These are laboratory controls, not
  SSDF attestation, cgroup memory quotas or a licensed secret-scanning product.

## 0.1.5 — 2026-09-08

Fail-closed audit from [PR #12](https://github.com/KonkovDV/SynAPS-GridPlan/pull/12) /
[PR #13](https://github.com/KonkovDV/SynAPS-GridPlan/pull/13), plus the remaining
closable release gates. SynAPS pin remains
[`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169).
Self-assessed ISO 16290 TRL 4. Not a plant pilot.

### Breaking input contracts (migration)

- Domain instants must be ISO-8601 **with offset** (`Z` or `+03:00`). Unix
  timestamps, booleans and naive local datetimes are rejected, including crew
  `shift_calendar` / `availability`.
- Unknown JSON fields on GridPlan documents are rejected. Extensions belong in
  `domain_attributes`.
- A nonempty `travel_minutes` map must contain the actual site-to-site leg;
  missing A→B is not replaced by home→B. Empty map remains explicit zero travel.
- Native FIFO/`check` will not set overall `verified_feasible` when travel is
  present on a nonempty workload, including an all-zero matrix.
- `report` is rendering only. Re-verification is `python -m synaps_gridplan check PROBLEM RESULT`.
- Lab size quotas apply to JSON files and catalog counts. They are not capacity SLAs.

### Verification and repair

- Incomplete, non-injective or mutated ID maps cannot erase work from checking.
- Immutable ПЛ rows survive import, check, disruption and diff; `immutable:false`
  is not a hard lock. Repair recompiles the current problem and names
  `INCREMENTAL_REPAIR`.
- Clearance windows intersect release/latest. Setup matrices are sized against
  the upstream 2 000 000-entry cap before allocation.
- Solve payloads may embed `problem` so `check` can detect a swapped constraint set.
- Jury, emergency-day and scale demos exit 2 unless their positive claims hold.

### Supply chain and docs

- CI runs mypy (package), pip-audit on the installed tree, cargo-audit, and a
  lockfile CycloneDX inventory under `sbom/`. That is not a complete SSDF
  attestation, secret scan or license legal opinion.
- `AUDIT.md` and `ACADEMY_APPLICATION.md` record remaining gates: kernel review,
  authenticated provenance, shadow-pilot, Academy IP/rubric, PDF regeneration.

## 0.1.4 — 2026-09-04

Public contest tree on SynAPS
[`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169).
ISO 16290 TRL 4. Not a plant pilot.

- World-practice mapping in ``PRACTICE.md`` and ``synaps_gridplan.practice``
  (Hydro-Québec TMS CP 2022, Energies 2025 mutex/windows, Goel & Meisel EJOR
  2013 downtime hull, SOGL/OPC freeze vs OPI, Uptime Tier III concurrent
  maintainability, Hexaly/ČEZ as a different FSM class). Plan JSON carries
  ``practice.layer`` / ``electrical_security=out_of_scope``. CLI ``practice``.
- Synthetic dual-feed hall: declared two-path mutex. Public MMTS-9 (18 Aug
  2026) is an incident *class*, not a reconstruction.
- Independent fail-closed checker (Python and Rust). GREED/FIFO never report
  ``optimal``. Empty FIFO is vacuously feasible.
- Synthetic РЭС «Северный»: GREED verifies, calendar FIFO does not. CP-SAT
  can prove optimal makespan (``slow``).
- Synthetic GRES-block. CLI ``small --seed 42`` is the fail-closed
  ``ASSET_OVERLAP`` demo; verified small seed is ``--seed 12``.
- Emergency-restoration day (узел «Восточный»): GREED verified-clean; FIFO
  27 hard violations; replan keeps the frozen ПЛ row. Lab instance.
- Generic feeder ``medium``/``stress`` (200/600 jobs): GREED verifies; FIFO
  does not. 50k engine runs are a different domain.
- Contest pitch: ``SynAPS-GridPlan.pdf``. Honest limits in ``APPLICATION.md``.
