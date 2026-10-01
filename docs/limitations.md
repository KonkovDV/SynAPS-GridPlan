# Limitations (honest)

1. **Risk** is an advisory proxy (priority + post-plan exposure), not CVaR / RUL /
   certified PoF.
2. **Outage windows** are checked hard in GridPlan post-check for
   `interruption_required` jobs; if the solver proposes an illegal interval the
   status becomes `error`.
3. **ЗИП:** SynAPS `AuxiliaryResource.pool_size` models concurrent capacity.
   Consumable stock / replenishment are GridPlan post-checks
   (`SPARE_PART_SHORTAGE`).
4. **Frozen:** explicit `FrozenAssignment` is authoritative; legacy frozen
   windows still invent first-eligible crew (partial).
5. **Travel** is setup-matrix minutes, not full crew routing (VRP).
6. **Shifts** are compiled into `WorkCenter.calendar`: the intersection of
   `shift_calendar` and `availability`. Both empty means 24/7. Occupancy
   `[start - setup, end]` must sit in one interval, the same formula as the
   pinned engine. A job longer than every open interval becomes a chain of
   day parts on the same asset; the outage is the hull from the first start
   to the last end. Spare stock and skills are required once, on the first
   part. An immutable freeze stays one placement. **Safety and service
   area** stay post-check only. This is not a labour-law roster.
7. **No customer EAM / SCADA / GIS** integration.
8. Heuristic solvers (`GREED`, `BEAM`, `ALNS`, `RHC`) map to
   `heuristic_feasible` and must not be called optimal without proof.
9. Synthetic generator modes are fixtures, not network digital twins.
   `gres-block` is generation-shaped (GTU / BOP / SWYD) and labelled
   `not_live_el5` — not a named-station dump, not unit-commitment, not N-1.
10. Benchmark metrics are `synthetic_experiment` / `fixture_only`.
11. Native `synaps-gridplan-rs synthesize` does not implement `gres-block`
    (Python CLI only). Native FIFO/check still apply to a Python-emitted JSON
    and fail-close on the stock GRES instance (windows / ban / overlap) —
    that is notary evidence, not a native GRES synthesizer.
12. GRES `SimultaneousOutageBan` is interruption-only. Online BOP (ПЭН)
    during a GTU outage does not fire the ban. Do not read this as N-1 or
    unit-commitment security.
13. GRES `seed` salts UUID5 identifiers; job refs, window days, and the
    dual-GTU ban pair do not reshape. Feeder `--assets/--jobs/--crews` are
    rejected on `--mode gres-block`.
14. GRES blade ЗИП is consumable stock (two repairs ⇒ qty ≥ 2), not a
    concurrent pool that would allow qty=1 when outages are staggered.
15. **Ban occupancy** is the hull of a precedence-connected interruption
    chain, not the union of task intervals. Independent jobs (no predecessor
    on that asset) are not hulled. This is still not N-1.
16. **ISO 16290 TRL 4** (laboratory). Not TRL 5 relevant environment, not
    TRL 6 pilot, not ISO 55000 certification, not ГОСТ-certified ТОиР.
17. **Simultaneous-outage ban occupancy** is the hull of a precedence-connected
    interruption chain (conservative over-approximation). A plan that is
    electrically fine can still be rejected. Fail-closed by design; not N-1.
18. **`shift_calendar`:** each assignment must sit inside **one** calendar
    row. A night shift split across midnight as two adjacent rows is read as
    `OUTSIDE` / `SHIFT_CALENDAR_VIOLATION`. Merge those rows before ingest.
    Rows are not auto-stitched.
19. **ЗИП:** one stock unit per job. There is no quantity field on the job.
    Two repairs of the same spare need `qty ≥ 2`.
20. **Datetimes** on one problem must be all-naive or all-aware. Mixing
    raises loudly (not a silent skip).
21. GREED does not model asset exclusivity. `ASSET_OVERLAP` is a checker
    finding. Default `synthesize --mode small --seed 42` + GREED exits **2**.
    That is fail-closed. Verified small seed on this pin: **12**. Contest
    instance: `benchmark/jury_benchmark.py`. An asset `AuxiliaryResource` is
    not a substitute: on this pin the engine charges that resource for
    setup-matrix minutes before processing starts, so crew travel would
    count as an outage. Pair bans stay in the same post-check.
22. `FIFO-W` reads shift, availability, approved outage windows, travel, and
    predecessor finish. Empty crew calendars stay round-the-clock. It does
    not model asset exclusivity except by sitting inside those windows.
    Synthetic `res_severny` has empty crew calendars; section E of
    `benchmark/results/jury_report.md` is that instance. The 08:00–17:00
    slice is section F, not a labour roster.

