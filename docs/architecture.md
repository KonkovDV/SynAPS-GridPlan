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

## Upstream pin

Validated SynAPS commit is declared in `synaps_gridplan.versions.SYNAPS_COMMIT`
and `pyproject.toml`.
