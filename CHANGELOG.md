# Changelog

## Unreleased

- **fix**: `report` no longer dies on a legacy console code page. `main`
  switches stdout and stderr to UTF-8 before printing. A stream that refuses
  the switch still exits 2.

- **docs**: the landing page no longer says the checker verifies an electrical
  safety group or that a crew works one asset at a time. `QUALIFICATION_MISMATCH`
  compares qualification lists. `CREW_OVERLAP` compares concurrent jobs with
  `max_parallel`.

- **fix**: `synthesize --help` names the real modes. `--assets`, `--jobs`,
  and `--crews` size `--mode medium` only and are rejected on `gres-block`
  and `dual-feed-hall`. Named contest instances stay in the benchmark
  scripts. AUDIT records the 20 October reproduction slice, including 61
  `#[test]` functions in the current Rust tree.

- **docs**: the install line names the real lockfile, `requirements-lock.txt`.
  `requirements.lock` does not exist, so the first README command failed.
  The CI paragraph says what CI runs: a fresh `pip install -e ".[dev]"` from
  `pyproject.toml` with the slow CP-SAT tests, while the `lockfile` job only
  compares `requirements-lock.txt` with `uv pip compile`. `FIFO` is described
  as earliest due date first, the order `plan_fifo` sorts by.
  `CONTRIBUTING.md` lists the CI gates and treats unnumbered `docs/` files as
  living. `docs/benchmark-protocol.md` describes the scripts that exist,
  FIFO and FIFO-W included. The ГОСТ Р 58048 matrix no longer calls
  `docs/architecture.md` an archive, and the ТОиР scenario dates its target
  programme to the 1 October check instead of «сейчас».

- **bench**: `jury_benchmark.py` renders section E itself. FIFO-W runs on
  the same РЭС «Северный» instance, and the section sits between D and F.
  Section E had been written into `jury_report.md` by hand, so a fresh run
  dropped it and `test_fifo_w_section_matches_the_same_res_severny_instance`
  failed. The report now says «у всех бригад», the condition the generator
  checks, and ends with one newline. On 20 October 2026 a `--cpsat` rerun at
  the pin changed only the wall-time cells of the jury, emergency-day, and
  scale reports.
  `benchmark/results/README.md` regenerates the jury report with `--cpsat`,
  because a run without it drops section D. `test_emergency_report_renders_verified`
  writes into `tmp_path`, so `pytest` no longer rewrites the committed
  emergency-day report.

- **docs**: the copy-paste CLI matches `argparse`. `synthesize` has no
  `res-severny` or `emergency-day` mode; those instances stay in
  `benchmark/jury_benchmark.py` and `benchmark/emergency_day_benchmark.py`.
  `disrupt` requires `--job-id`, `report` writes to stdout, and schema or
  quota failures exit 2. The skill pool and the setup-matrix cap
  (`MAX_SCHEDULE_SETUP_ENTRIES`, 2 000 000 on pin `6178c93`) are named next
  to the compile boundary.

- **docs**: the JSON intake is named in full. `extract_problem` refuses
  `invalid_json`, `not_an_object`, `prose`, `envelope`, `blank_quantity`,
  and `invalid_problem`. README, the architecture note, the limitations
  list, and the 2026 literature review now list the same six reasons.

- **docs**: the model section of the README no longer uses inline TeX.
  GitHub and the editor preview were splitting subscripts and TeX
  commands into broken math. The same statements are now plain sentences
  and field names. The remaining TeX scraps in the notes are plain text too:
  the jury sum is `X1 + … + X6`, the deferred ABI is `p(o, m)`, and the
  pitch figure is `16 790 USD/год`.

- **docs**: rewritten `README.md` and `docs/sota-cp-2026.md` following the
  `SynAPS` / `SynAPS-MobiRoute` domain repository standard (ADR-0004):
  formal compilation algebra, solver portfolio semantics, two-layer grid
  maintenance literature, DRCP proof-logging boundaries, and 2025–2026
  LLM-to-CP benchmarks (`CP-Bench`, `CP-Agent`, `ConstraintBench`). External
  benchmark percentages are cited as literature context, not product claims.
  Removed internal AI work-plan scratch files from `docs/`.

- **feat**: fail-closed JSON intake (`synaps_gridplan.extract`) rejects prose
  (`reason=prose` or `invalid_json`) and a spare with neither
  `available_quantity` nor `stock_qty` (`blank_quantity`). On the two-item
  labeled intake fixture, 1/2 of emitted JSON candidates pass `PlanOutcome.ok`
  (regression test only, not a claims-registry row).

- **docs**: bibliographic records in `docs/sota-cp-2026.md` and the README
  algebra now follow `practice.py` and the papers as published. CP 2026 is
  LIPIcs vol. 379, article 24. ConstraintBench's 65.0% is full-solution
  feasibility, not a share of individual constraints. Invented module names,
  intake reason codes, and the mis-tagged FIFO-W row are gone.

- **docs**: added `docs/ru_software_registry.md` summarizing Russian software
  registry rules (Decrees No. 1236 and No. 1875). Registry inclusion is not
  claimed, and no registry entry number exists in the repository.

- **docs**: added `docs/pp86_horizon_analogy.md` comparing annual/monthly
  outage approval milestones in Government Decree No. 86 with `OutageWindow`
  and `FrozenAssignment` in GridPlan. Regulatory compliance is not claimed.

- **docs**: expanded `docs/data-contract-v2.md` with the flat-table exchange
  mapping, `AuxiliaryResource.pool_size` vs warehouse stock distinction, and
  `WorkCenter.calendar` intersection semantics (`shift_calendar ∩ availability`).

- **docs**: recorded the 18 October 2026 `SynAPS` pin review in `AUDIT.md` §10;
  `SynAPS` remains pinned at `6178c93` because upstream `8921ead` still starts
  `AuxiliaryResource` occupancy at `start - setup_minutes`.

- **docs**: tracked `index.html` in the repository and extended
  `scripts/lint_claims.py` to scan `.html` files.

- **docs**: section D of `jury_report.md` and `docs/limitations.md` state
  explicitly that a `CPSAT-30` optimum applies to the compiled model (asset
  exclusivity, simultaneous outage bans, and consumable spare stock remain
  independent domain post-checks).

- **ci**: increased the `scale-5k` workflow wall budget to 1200s. The pinned
  GREED cap stops the search; the workflow measures the subsequent domain
  verification of that partial schedule under `--allow-unverified` (diagnostic
  probe, not a claims-registry row).

- **bench**: added synthetic modes `scale-2k` and `scale-5k` (2 000 and 5 000
  jobs, campaign packing) and `benchmark/scale_budget.py` (wall time and
  `tracemalloc` peak). CI requires a verified GREED schedule on `scale-2k`.

- **ci**: extended `ruff check` to `benchmark/` and wrapped overlong template
  lines in `jury_benchmark.py` and `res_severny_benchmark.py` without changing
  rendered markdown.

- **docs**: `AUDIT.md` §9 records the 1 October 2026 documentation audit
  (58 `#[test]` functions in `native/synaps-gridplan-rs` vs 48 on historical
  `6dde1ce`; Energotechhub intake window through 2 October 2026 inclusive).

- **ci**: Dependabot lockfile pull requests regenerate `sbom/` with the base
  commit generator and push updated CycloneDX inventories back to the PR branch.
- **fix**: decoupled `checker.py` from `compiler.py` by moving
  `legacy_window_frozen_assignments` into `legacy_freeze.py`.

- **fix**: compiled crew shift calendars into `WorkCenter.calendar` as the
  intersection of `shift_calendar` and `availability` (both empty ⇒ 24/7;
  disjoint non-empty lists ⇒ closed crew calendar, never 24/7). Both Python
  and Rust checkers verify occupancy `[start - setup, end]` within a single
  open interval; multi-day jobs split into a chain of daily operations with
  outage hull `[first start, last end]`.

- **fix**: non-linear precedence graphs (cycles, joins, fan-out) are rejected
  at problem load in both Python and Rust.

- **fix**: zero on-hand spare stock with `lead_time_min > 0` and no
  `replenishment_date` rejects job starts before
  `planning_horizon_start + lead_time_min` (`SPARE_PART_NOT_YET_AVAILABLE`)
  in Python and Rust `check`. Catalog metadata fields (`voltage_level`,
  `parent_asset_id`, `coordinates`, `failure_modes`, `warehouse_location`) are
  reported in `unenforced_fields`.

- **fix**: `check` no longer republishes an imported `optimal` status; it
  recomputes feasibility and records the input label as `claimed_status` with
  `optimality_origin="imported_not_reproven"`.

- **docs**: refreshed `P6`, `P7`, and `P11` in `docs/CLAIMS_REGISTRY.md` for
  the Energotechhub intake window (7 September – 2 October 2026 inclusive).

- **bench**: FIFO-W places a ready job inside a shift and an approved outage
  window, after travel, and not before its predecessor finishes. On synthetic
  `res_severny` the crew calendars are empty, so the shift rule is idle there;
  that same instance then has 0 hard violations (section E). Heuristic, not
  a CP-SAT optimum.

- **test**: the pinned engine occupies an auxiliary resource for setup-matrix
  minutes before processing, on every assignment after the first on that
  crew. Asset exclusivity and pair bans stay domain post-checks
  (`docs/LIMITS.md`).

- **docs**: GitHub README lists the 14-slide submission pack, Energotechhub
  window [P6], prize ceiling [P8], CP-SAT section D, and native travel
  boundary; Academy 10th stream is marked past its published close.

- **docs**: dropped `SynAPS_v8_Evidence.pptx`. Submission pack is
  `SynAPS_GridPlan.pptx`. CI diffs extracted text (`docs/DECK_TEXT.txt`);
  it does not rebuild a 12-slide pptx.

- **docs**: marathon pitch PDF left the repo root (sliced at 0.1.4 /
  `94b5048`). Path: `_SUBMIT_MIK_2026_08_18/SynAPS-GridPlan-marathon-0.1.4.pdf`.
  Dropped from the sdist include list. Not an Energotechhub packet.

- **docs**: extracted pitch text: `docs/DECK_TEXT.txt` (from
  `SynAPS_GridPlan.pptx`).

- **docs**: CI-gated claims table in `docs/CLAIMS_REGISTRY.md` (`claim_id`,
  artifact, reproduce command, status). `tests/test_claims_registry.py`
  fails when a tagged lab number in README lacks its id.

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
  accelerator, not Academy «10th stream». Submission deck
  ``SynAPS_GridPlan.pptx``. Retracted
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
