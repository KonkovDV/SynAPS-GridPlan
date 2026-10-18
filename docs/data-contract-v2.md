# Контракт данных v2 и табличный обмен

В пакете проверяются инварианты из `models.py` и `checker.py` (Python) и из
`native/synaps-gridplan-rs`. Поля за пределами этого набора складываются в
список `unenforced_fields` итогового отчёта (`PlanOutcome.unenforced_fields` и
вывод Rust `check`) и не меняют вердикт допустимости:

- `Asset.voltage_level`
- `Asset.parent_asset_id`
- `Asset.coordinates`
- `Asset.failure_modes`
- `SparePart.warehouse_location`
- `SparePart.lead_time_min` — при `quantity_on_hand == 0` и пустом
  `replenishment_date` запрещает старт работы раньше
  `planning_horizon_start + lead_time_min` (`SPARE_PART_NOT_YET_AVAILABLE`);
  при ненулевом остатке на складе или явно заданной дате поставки поле не
  меняет вердикт и перечисляется в `unenforced_fields`.

Отвергаются на входе (`ValidationError` в Python, ошибка десериализации в
Rust):

- неизвестные ключи в корне документа и во вложенных каталогах (`extra="forbid"`,
  `deny_unknown_fields`);
- метки времени без часового пояса (`Z` или `+03:00`);
- нелинейный граф предшествования работ (`predecessor_job_ids`): цикл,
  схождение (`> 1` предшественника у работы) или ветвление (`> 1` прямого
  последователя у работы). Компилятор строит только линейные цепочки.

## Табличный обмен

Чтеца CSV и XLSX в пакете нет. Будущий импорт из плоских выгрузок АСУ ТОиР
приводит строки таблиц к JSON-модели `GridPlanProblem` по следующим правилам:

| Лист выгрузки | Сущность JSON | Ключевые поля | Правило валидации на границе |
| --- | --- | --- | --- |
| `assets` | `Asset` | `id`, `name`, `asset_type`, `substation_id`, `location_id`, `voltage_level`, `parent_asset_id` | Уникальный `id`; `voltage_level` и `parent_asset_id` попадают в `unenforced_fields` |
| `crews` | `Crew` | `id`, `name`, `skills`, `max_parallel`, `home_location_id`, `shift_calendar`, `availability` | Только интервалы с явным смещением часового пояса (`Z` или `+03:00`) |
| `outage_windows` | `OutageWindow` | `id`, `asset_id`, `start`, `end`, `approved`, `frozen` | `asset_id` обязан существовать в `assets`; `end > start` |
| `spare_parts` | `SparePart` | `id`, `name`, `quantity_on_hand`, `replenishment_date`, `lead_time_min`, `warehouse_location` | Целые неотрицательные остатки; `lead_time_min >= 0` |
| `jobs` | `MaintenanceJob` | `id`, `name`, `asset_id`, `duration_min`, `required_skills`, `requires_outage`, `allowed_window_ids`, `predecessor_job_ids`, `required_spare_part_ids`, `earliest_start`, `latest_finish` | Ссылки на существующие `assets`, `outage_windows`, `spare_parts`; только линейные цепочки предшествования (`Asset.coordinates` и `Asset.failure_modes` из карточки актива перечисляются в `unenforced_fields`) |
| `frozen_assignments` | `FrozenAssignment` | `job_id`, `crew_id`, `start`, `end`, `outage_window_id`, `immutable` | Фиксация согласованного слота ПЛ при перепланировании |
| `simultaneous_outage_bans` | `SimultaneousOutageBan` | `id`, `asset_a_id`, `asset_b_id`, `reason` | Явный табличный запрет одновременного вывода двух активов |

Поля `Asset.voltage_level`, `Asset.parent_asset_id`, `Asset.coordinates`,
`Asset.failure_modes`, `SparePart.warehouse_location` и `SparePart.lead_time_min`
(при ненулевом остатке на складе или заданной дате поставки) при импорте из
таблиц сохраняются в JSON-модели и отражаются в `unenforced_fields`.
Конкретный профиль CIM (IEC 61970 / 61968) для пакета не фиксировался.
Отображение опирается на внутреннюю JSON-схему `schemas/gridplan.pydantic.problem.json`.

### Граница компиляции в ядро `SynAPS`

- **Вспомогательные ресурсы (`AuxiliaryResource`).** На закреплённом пине
  `SynAPS` (`6178c93`) параметр `pool_size` задаёт параллельную ёмкость
  ресурса (`>= 1`), это не склад и не расходуемый остаток ЗИП. Кроме того,
  интервал занятости `AuxiliaryResource` начинается в `start - setup_minutes`,
  то есть захватывает время бригады в пути. Поэтому расходуемый складской ЗИП,
  эксклюзивность актива на время ремонта и попарные запреты отключений
  проверяются независимым доменным чекером после построения расписания.
- **Календарь бригады (`WorkCenter.calendar`).** Компилятор передаёт в `SynAPS`
  пересечение `shift_calendar` и `availability`. Круглосуточный режим (`None`)
  допускается только тогда, когда оба списка в карточке бригады пусты. Пустое пересечение не круглосуточно: если смены и окна доступности заданы, но не
  пересекаются ни на одной минуте горизонта, бригада получает закрытый
  календарь без доступных интервалов.
