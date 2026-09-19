# Changelog

## Unreleased

- **docs**: marathon pitch PDF left the repo root (sliced at 0.1.4 /
  `94b5048`). Path: `_SUBMIT_MIK_2026_08_18/SynAPS-GridPlan-marathon-0.1.4.pdf`.
  Dropped from the sdist include list. Not an Energotechhub packet.

- **docs**: pitch rebuild `python scripts/build_deck.py` reads
  `jury_report.md` + `versions.py` + `git describe`; footer is not a
  hardcoded 0.1.8. Extracted text: `docs/DECK_TEXT.txt`.

- **docs**: CI-gated claims table in `docs/CLAIMS_REGISTRY.md` (`claim_id`,
  artifact, reproduce command, status). `tests/test_claims_registry.py`
  fails when a tagged lab number in README/deck builder lacks its id.

- **docs**: executable banned-claim list (`docs/BANNED_CLAIMS.txt`,
  `python scripts/lint_claims.py`). Live pack uses the `versions.py` TRL
  sentence. Pytest count is `docs/TEST_COUNT.txt` from
  `python scripts/export_test_count.py`, not a hardcoded 3/3 or 183.

- **test**: native `check` on synthetic `res_severny` GREED/FIFO — domain kind
  multiset matches Python; nonempty `travel_minutes` keeps
  `verified_feasible` false (`tests/test_native_parity.py`). Jury-facing
  limits: `docs/LIMITS.md`.

- **bench**: committed ``jury_report.md`` now includes scenario D from a live
  ``CPSAT-30`` run on the same synthetic ``res_severny`` instance (status
  ``optimal``, 0 hard violations, dual bound = makespan, plan SHA-256).
  ``python benchmark/jury_benchmark.py --cpsat`` is the regeneration command;
  CI claim fixtures use it. Snapshot pin in ``test_committed_jury_report_matches_pin``.

- **docs**: Energotechhub working note (`docs/ETECHHUB_APPLICATION.md`):
  live URL `/accelerator` (not `/accelerator2026`), official broker names,
  v7 pitch retracts, no second claims file at repo root. 25 Sep is this
  accelerator, not Academy «10th stream». Honest 12-slide deck
  ``SynAPS_v8_Evidence.pptx`` (``scripts/build_pitch_v8.js``). Retracted
  unverifiable Sep 2026 «Zhao / Gupta TPWRS» rows from ``PRACTICE.md``.

- **docs**: truth pass 2026-09-18 — claims registry, GOST R 58048 vs ISO 16290,
  187-FZ not claimed as attestation, no GridPlan–Россети partnership, market
  figures marked assumption/target, one ТОиР scenario, UGT/IP/pilot notes,
  red-team brief. Evidence command: `python scripts/evidence_bundle.py`
  (CP-SAT on the same `res_severny` instance as FIFO/GREED).

## 0.1.8 — 2026-09-18

Red Team 0.1.8–0.1.9 closures. SynAPS pin unchanged
[`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169).
Self-assessed ISO 16290 TRL 4. Not a plant pilot.

- **perf**: `_job_chains` uses `deque.popleft()` instead of `list.pop(0)` —
  O(n²) → O(n) for MAX_JOBS = 20 000 inputs (PR #20).
- **fix**: `plan_fifo` now skips a (crew, slot) pair when
  `start + duration_min > job.latest_finish`. The post-checker remains
  authoritative; this makes the baseline honest (PR #21).
- **fix**: `_as_markdown` adds an italicised continuation line when
  `gridplan_violations` or `engine_violations` exceed 20 entries —
  silent truncation would mislead a reviewer reading only the markdown
  output (PR #18). Constant extracted as `_TRUNCATION_LIMIT = 20`.
- **fix**: `GridPlanProblem._cross_refs` appends an overflow count when
  more than 20 validation errors are raised (PR #23).
- **test**: Red Team 0.1.8 suite — 500-job chain correctness, markdown
  truncation note, FIFO `latest_finish` boundary, outage-window boundary
  smoke (PR #19).
- **test**: Red Team 0.1.9 suite — diamond topology, `_cross_refs`
  overflow, sparse precedence (PR #24).
- **docs**: Barral CPAIOR 2024 stable Springer DOI and September 2026
  SOTA notes in ``PRACTICE.md`` (PR #22).
- **deps**: native ``uuid`` 1.24.1 → 1.26.1 (PR #17).

## 0.1.7 — 2026-09-08

Completes the laboratory closures named in 0.1.6. SynAPS pin remains
[`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169).
Self-assessed ISO 16290 TRL 4. Not a plant pilot.

- Native CLI reads apply the byte quota to bytes actually read (same TOCTOU
  bound as Python). Nested native catalogs use ``deny_unknown_fields`` after
  accepting the optional Python-parity fields; extra crew-calendar keys fail
  at parse.
- Markdown interpolation is a dedicated flattener (newlines, backticks, ``<``
  / ``>``). That is not a general HTML sanitizer.
- Committed Pydantic nested schema is checked with ``jsonschema`` against
  synthesized dumps, plus an unknown-field matrix. Not a byte-for-byte
  round-trip or a standalone Draft 2020-12 norm for arbitrary future v2.
- Pattern secret scan covers additional high-risk shapes. Still not entropy
  analysis or a licensed product. Ruff in CI includes ``scripts``.
- Synthetic ``small`` still does not set ``window.frozen``; seed 12 is a
  regression, not a decorative flag.

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
