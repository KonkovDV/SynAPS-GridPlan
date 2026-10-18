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

## Табличный обмен

Чтеца CSV и XLSX в пакете нет. Этот раздел — словарь колонок для будущего
чтеца. Чтец собирает `GridPlanProblem` и отдаёт его валидации (`extra=forbid`).
Неизвестная колонка в модель не входит.

Номер профиля CIM в этом проходе не проверялся. Подставлять номер нельзя.

Пустая ячейка количества не пишется как ноль и не становится остатком.
`SparePart.available_quantity` — остаток, `reserved_quantity` — уже занятая
часть, usable — их разность. `stock_qty` — прежнее имя `available_quantity`.
`pool_size` движка — одновременная ёмкость, не склад. `lead_time_min` остаток
не создаёт.

Календари бригады. Пустые вместе `shift_calendar` и `availability` означают
круглосуточно. Один непустой список и есть календарь. Оба непусты —
пересечение. Пустое пересечение не круглосуточно.

Принимаются и не меняют вердикт: `Asset.voltage_level`,
`Asset.parent_asset_id`, `Asset.coordinates`, `Asset.failure_modes`,
`SparePart.warehouse_location`. `SparePart.lead_time_min` жёсткий только при
нулевом usable и без `replenishment_date`.

`travel_minutes`: ключ `{from_location}|{to_location}`, минуты подготовки.
Непустая матрица держит native `verified_feasible` ложным.
