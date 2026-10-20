# SynAPS-GridPlan Architecture

**Product boundary:** deterministic computational core for building and checking
maintenance / repair / emergency replan schedules for energy assets.

**Not:** SCADA, EAM, OMS, GIS, diagnostics, failure prediction, power-flow EMS,
or a corporate ТОиР system replacement.

## Layers

```
GridPlanProblem (domain)
    → adapter.to_schedule_problem (compile)
    → SynAPS solve_schedule / repair_schedule
    → SynAPS FeasibilityChecker
    → GridPlan constraints post-check (outage, frozen, ЗИП consumable, …)
    → PlanOutcome + report (+ optional diff)
```

## Authority for claims

| Layer | Proves |
| --- | --- |
| SynAPS FeasibilityChecker | Engine hard constraints on compiled problem |
| GridPlan constraints | Domain semantics SynAPS does not fully encode |
| Benchmark | Synthetic relative behaviour only |
| Customer evidence | Required for any pilot / savings claim — absent |

## What the compile includes

Crew calendars are compiled. `shift_calendar` and `availability` intersect
into `WorkCenter.calendar`. Both empty means the crew is available around the
clock. A disjoint pair leaves the crew closed for that period.

Each qualification becomes an `AuxiliaryResource` coded `skill:{name}`.
`pool_size` is the sum of `max(1, max_parallel)` over crews that list it.
The first day-part of a job takes one unit. On the pin, every assignment
after the first on that work center holds the resource from
`start - setup_minutes`. The pool is concurrent capacity.

The setup matrix is `len(crews) × (location codes)²`, including asset sites,
crew bases, and the sentinel `idle`. Above `MAX_SCHEDULE_SETUP_ENTRIES` on
the pinned SynAPS (`2 000 000` at `6178c93`) compilation raises `ValueError`
before the list is allocated.

CP-SAT `OPTIMAL` is the compiled model and its makespan. Asset exclusivity,
pair bans, spare stock, `safety_constraints`, and `service_area` stay in the
post-check. A non-empty safety list must be covered by the crew's
qualifications or `domain_attributes.safety_clearances`
(`SAFETY_CONSTRAINT_MISMATCH`). Service areas are compared only when both
are set (`SERVICE_AREA_MISMATCH`). `PlanOutcome.ok` needs an
acceptable status, `verified_feasible`, and zero hard violations together.

`synthesize --mode` is `small`, `medium`, `stress`, `scale-2k`, `scale-5k`,
`disruption`, `infeasible`, `frozen-conflict`, `gres-block`, `dual-feed-hall`.
The named РЭС «Северный» instance and the emergency-day instance are
`benchmark/jury_benchmark.py` and `benchmark/emergency_day_benchmark.py`.

`extract_problem` accepts a JSON object and does not call a language model.
A refusal is one of `invalid_json`, `not_an_object`, `prose` (a root key
`text`, `prompt`, `narrative`, or `request`), `envelope` (a `problem` key
that is not the whole document), `blank_quantity` (a spare with neither
`available_quantity` nor `stock_qty`), or `invalid_problem` (the object
fails `GridPlanProblem`). A blank quantity does not become zero stock.

## Upstream pin

The validated SynAPS commit is `synaps_gridplan.versions.SYNAPS_COMMIT`,
the same SHA as `pyproject.toml`. A newer upstream `main` does not move the
pin by itself.
