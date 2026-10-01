# Границы продукта (LIMITS)

Если питч, README или заявка противоречат этому файлу — верен этот файл.
Инженерные детали: [docs/limitations.md](limitations.md).

- **Данные синтетические.** Инстанс `res_severny` собирается в
  `benchmark/res_severny_benchmark.py` (`data_provenance=synthetic`). Это не
  живая выгрузка ДЗО и не цифровой двойник сети.
- **TRL 4 лабораторный.** `ISO16290_TRL = 4` в `src/synaps_gridplan/versions.py`:
  лабораторные фикстуры, не пилот на предприятии. Не сертификат ГОСТ Р 58048.
  Не аттестация 187-ФЗ / КИИ.
- **Нет модуля трудового права.** В `src/synaps_gridplan/` нет сменных норм
  Минтруда, СНиП или непрерывного отдыха как отдельного контура. Поле
  `Crew.shift_calendar` — окна доступности; пустой календарь не ограничивает.
- **Rust-чекер — доменный слой, не движок SynAPS.** Паритет kind с Python
  гейтится в `tests/test_native_parity.py` на `--mode small` (seeds 26/42/12)
  и на GREED/FIFO планах синтетического `res_severny`.
  `verification_scope = gridplan_domain`, `engine_checked = false`.
- **Travel-матрица на `res_severny` непуста.** Native `check` тогда пишет
  `unsupported_constraints = ["travel_minutes"]` и держит `verified_feasible =
  false` даже при чистом домене (GREED: домен 0, Python `verified_feasible`
  true). Слой движка (у FIFO — часть из 107 жёстких нарушений) считает только
  Python/SynAPS.
- **Декоративные поля каталога.** `Asset.voltage_level`, `parent_asset_id`,
  `coordinates`, `failure_modes` и `SparePart.warehouse_location` принимаются
  и попадают в `metadata.unenforced_fields` (kind `UNENFORCED_FIELD`). На
  вердикт не влияют. `lead_time_min` — жёсткое правило только при нулевом
  usable-остатке и без `replenishment_date`: старт раньше
  `planning_horizon_start + lead_time_min` даёт `SPARE_PART_NOT_YET_AVAILABLE`.
  Задержка не увеличивает остаток: после этого момента нулевой остаток
  по-прежнему `SPARE_PART_SHORTAGE`. Ненулевой остаток или заданная
  `replenishment_date` оставляют `lead_time_min` предупреждением. То же
  жёсткое правило считает native `check`.
- **Предшествование — линейные цепочки.** Цикл, две входящие или две исходящие
  дуги отвергаются при загрузке. Компилятор не строит DAG с join или fan-out.
- **Взаимоисключение по активу — постпроверка.** Закреплённый SynAPS
  (`6178c93`) для каждой работы бригады, кроме первой, занимает
  вспомогательный ресурс на окне `[start - минуты матрицы переналадки, end)`.
  Переезд из этой матрицы поэтому выглядит как занятие актива.
  `AuxiliaryResource` с `pool_size=1` на актив не компилируется. Запрет пары
  тем же ресурсом получил бы то же окно, поэтому тоже остаётся в доменной
  проверке. Тест:
  `tests/test_synaps_pin_regression.py::test_matrix_setup_occupies_aux_before_the_asset_job_starts`.
- **Не заявлены:** N-1, SAIDI, живой EL5, INFIMUM, партнёрство с ПАО «Россети»,
  внедрение на объекте, «первые в нише».
- **Архивный PDF марафона не пакет подачи.** Срез 0.1.4 (`94b5048`) лежит в
  `_SUBMIT_MIK_2026_08_18/SynAPS-GridPlan-marathon-0.1.4.pdf`. В корне
  репозитория и в sdist этого файла нет. Не пересобирать его как дек 0.1.8.
- **lint_claims не сканирует исторический каталог.** Пропускаются
  `docs/[0-9]*`, `_SUBMIT_MIK_2026_08_18/`, `docs/rfc/` и суффиксы `.pdf`
  (и прочие бинарные). Это согласовано с `CLAIMS_REGISTRY.md`: тот каталог
  не источник цифр. Живой пакет — README, дек, `docs/` без нумерации.
