# Changelog

## Unreleased audit — 2026-09-07/08

Reviewable changes in [PR #12](https://github.com/KonkovDV/SynAPS-GridPlan/pull/12),
including the native audit from PR #13. No merge into `main`, version bump or new
release tag was performed. Evidence and remaining release gates: [AUDIT.md](AUDIT.md).

### Stricter contracts and fixes

- Validate catalog identity, references and version labels at use boundaries;
  malformed/incomplete/non-injective ID maps must not erase work from checking.
- Intersect clearance windows with release/latest bounds. Preserve all immutable
  problem commitments through plan import, checking, disruption and diffing;
  advisory freezes are not hard locks.
- Recompile the current problem for repair, keep the base unmodified and disclose
  the actual `INCREMENTAL_REPAIR` engine. Unsupported custom repair labels fail.
- Reject naive domain datetimes and normalize aware instants to UTC. Pydantic
  coercions still exist; this is not a complete strict JSON Schema contract.
- Require actual site-to-site travel in nonempty matrices; reject oversized dense
  setup matrices before constructing them using the pinned upstream limit.
- Native FIFO/check now distinguish domain feasibility from verification scope.
  Any nonempty travel matrix prevents native verification for a nonempty workload,
  including all-zero matrices. Empty travel is an explicit zero-travel assumption.
- Harden native ranges, temporal arithmetic, frozen/setup parsing and UUID maps.
- Reject contradictory positive saved-result flags; label imported reports as
  snapshots, not new checks. Quote CSV cells and mitigate formula-like prefixes,
  including metadata/preamble fields. JSON does not add CSV safety prefixes.
- Gate positive jury-demo claims on actual results; document limited compiled-model
  optimality, synthetic data, self-assessed TRL and absent industrial validation.

Historical entries below describe earlier release claims, not fresh evidence for
an arbitrary revision. Current applicability corrections are in README/AUDIT;
ISO 16290 TRL is self-assessed and the existing PDF was not reviewed or regenerated
by this audit.

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

