# Контракт данных v2

Обратно совместим с JSON `gridplan.v1`: новые поля необязательны. Модели — `src/synaps_gridplan/model.py`. Схемы:

- `schemas/gridplan.v2.problem.schema.json`
- `schemas/gridplan.v2.result.schema.json`
- `schemas/gridplan.v2.diff.schema.json`

У опубликованного результата есть `data_provenance` из набора `synthetic | open_data | customer_data | experiment | production_verified` и явный `claim_level`. Отпечатки `input_hash` и `config_hash` — SHA-256 канонического JSON (`synaps_gridplan.fingerprint`).

Поля, которые вердикт не меняют, перечисляются в `unenforced_fields`:

- `Asset.voltage_level`
- `Asset.parent_asset_id`
- `Asset.coordinates`
- `Asset.failure_modes`
- `SparePart.warehouse_location`
- `SparePart.lead_time_min` — жёсткое правило только при нулевом `usable_quantity` и пустом `replenishment_date`: старт раньше `planning_horizon_start + lead_time_min` даёт `SPARE_PART_NOT_YET_AVAILABLE`. Задержка остаток не создаёт. Ненулевой остаток или заданная дата поставки оставляют поле предупреждением.

На входе отвергаются неизвестные ключи (`extra="forbid"`, в Rust — `deny_unknown_fields`), метки времени без смещения и нелинейный граф `predecessor_job_ids`: цикл, больше одного предшественника, больше одного последователя.

## Табличный обмен

Чтеца CSV и XLSX в пакете нет. Этот раздел — словарь для будущего чтеца. Чтец собирает `GridPlanProblem` и отдаёт его валидации. Неизвестная колонка в модель не входит.

Пустая ячейка количества не пишется как ноль и не становится остатком. `SparePart.available_quantity` — остаток, `reserved_quantity` — уже занятая часть, usable — их разность. `stock_qty` — прежнее имя `available_quantity`. `pool_size` движка — одновременная ёмкость, не склад. `lead_time_min` остаток не создаёт.

Календари бригады. Пустые вместе `shift_calendar` и `availability` означают круглосуточно. Один непустой список и есть календарь. Оба непусты — пересечение. Пустое пересечение не круглосуточно: в солвер уходит минута до начала горизонта, чтобы внутри горизонта не нашлось ни одного слота.

Принимаются и не меняют вердикт: `Asset.voltage_level`, `Asset.parent_asset_id`, `Asset.coordinates`, `Asset.failure_modes`, `SparePart.warehouse_location`. `SparePart.lead_time_min` жёсткий только при нулевом usable и без `replenishment_date`.

`travel_minutes`: ключ `{from_location}|{to_location}`, минуты подготовки. Непустая матрица держит native `verified_feasible` ложным. Число ячеек матрицы в солвере — бригады × (коды площадок)², с базами бригад и точкой `idle`. Выше `MAX_SCHEDULE_SETUP_ENTRIES` пина (2 000 000) компилятор отказывает до выделения списка.

`safety_constraints` и `service_area` в солвер не компилируются. Непустой список допусков должен целиком входить в объединение `qualifications` бригады и строковых элементов `domain_attributes.safety_clearances`, иначе `SAFETY_CONSTRAINT_MISMATCH`. Пустой список ничего не требует: это не группа по электробезопасности. `SERVICE_AREA_MISMATCH` — только если зона актива и зона бригады обе заданы и не совпали. Для строк native `check` совпадает. Нестроковый элемент `safety_clearances` Python приводит через `str`, Rust пропускает.

`required_qualifications` компилятор собирает в пул `skill:{квалификация}`. `pool_size` — сумма `max(1, max_parallel)` по бригадам с этой строкой. Первая часть работы берёт одну единицу. На пине для каждой работы бригады, кроме первой на этом рабочем центре, окно начинается в `start` минус минуты переезда. Это одновременная ёмкость, не допуск по наряду.

Конкретный профиль CIM (IEC 61970 / 61968) для пакета не фиксировался. Отображение опирается на JSON-схему пакета, не на номер профиля.
