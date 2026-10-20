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

CP-SAT `OPTIMAL` is the compiled model and its makespan. Asset exclusivity,
pair bans, and spare stock stay in the post-check. `PlanOutcome.ok` needs an
acceptable status, `verified_feasible`, and zero hard violations together.

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
