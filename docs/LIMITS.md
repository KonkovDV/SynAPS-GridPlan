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
- **Не заявлены:** N-1, SAIDI, живой EL5, INFIMUM, партнёрство с ПАО «Россети»,
  внедрение на объекте, «первые в нише».
- **Архивный PDF марафона не пакет подачи.** Срез 0.1.4 (`94b5048`) лежит в
  `_SUBMIT_MIK_2026_08_18/SynAPS-GridPlan-marathon-0.1.4.pdf`. В корне
  репозитория и в sdist этого файла нет. Не пересобирать его как дек 0.1.8.
- **lint_claims не сканирует исторический каталог.** Пропускаются
  `docs/[0-9]*`, `_SUBMIT_MIK_2026_08_18/`, `docs/rfc/` и суффиксы `.pdf`
  (и прочие бинарные). Это согласовано с `CLAIMS_REGISTRY.md`: тот каталог
  не источник цифр. Живой пакет — README, дек, `docs/` без нумерации.
