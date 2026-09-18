# Data contract v2

Backward compatible with `gridplan.v1` JSON: new fields are optional.

## Entities

See Pydantic models in `src/synaps_gridplan/model.py` and JSON Schema:

- `schemas/gridplan.v2.problem.schema.json`
- `schemas/gridplan.v2.result.schema.json`
- `schemas/gridplan.v2.diff.schema.json`

## Provenance

Every published result must carry `data_provenance` in:

`synthetic | open_data | customer_data | experiment | production_verified`

and an explicit `claim_level`.

## Fingerprints

`input_hash` / `config_hash` are SHA-256 of canonical JSON
(`synaps_gridplan.fingerprint`).
