# 04 — Пакет доказательств (Evidence Pack)

> Дата среза продукта: **16.08.2026**. Публичный контур **GridPlan 0.1.1**,
> пин SynAPS `bd09d13561b3bd690845d07546def59b4521b16c`.
>
> **Как читать.** В анкету идут **§0 и §8**. §1–2 и §3 — зрелость **движка**
> SynAPS (другой репозиторий, в т.ч. кабельный домен). Это не доказательство
> пилота Россетей и не инстанс 10K работ ТОиР.

## 0. Что показываем жюри по продукту (сходится с APPLICATION.md)

| Утверждение | Артефакт | Число |
|---|---|---|
| Версия пакета | `src/synaps_gridplan/versions.py`, `pyproject.toml` | **0.1.1** |
| Пин движка | тот же файл + `test_version_pins.py` | `bd09d13` = 40 hex |
| Автотесты продукта | `pytest -q` (18.08.2026, py 3.13) | **96 passed** (в т.ч. 1 `slow` CP-SAT, 3 паритета с `cargo`, 7 аварийного дня, 5 масштаба фидера), **~22 с** |
| Синтетический РЭС «Северный» | `benchmark/results/jury_report.md` | 55 работ, 7 бригад, 39 активов, 85 окон |
| FIFO vs GREED | тот же отчёт | жёстких нарушений **107** / **0**; GREED «да» только при `verified_feasible` и нуле нарушений; отпечаток GREED `e2095325f0210065` |
| Расшифровка 107 | таблица отчёта | 5+5+48+16+1+32 = 107 (два слоя: GridPlan + SynAPS) |
| CP-SAT оптимум makespan | `test_res_cpsat_proves_optimal_makespan` (`slow`), живой прогон 16.08 | **30600** мин = dual bound, gap 0%, `verified_feasible` |
| Freeze ПЛ | Scenario B в том же контуре | frozen не двигаются |
| Аварийные сутки (синтетика, регламент СТО) | `benchmark/results/emergency_day_report.md`, `tests/test_emergency_day.py` | 23 работы, 8 бригад, цепочка локализация→ремонт→опробование→ввод + ДГУ + замороженная ПЛ; FIFO 27 / GREED 0; не реконструкция живого филиала |
| Генератор 200/600 | `benchmark/results/scale_report.md` | GREED 0 нарушений, FIFO ломает окна; 50k движка — другой домен |
| Фикстура генерации | `tests/test_gres_block.py` | тираж, не живая ЭЛ5 |
| TRL | `APPLICATION.md`, `versions.py` | ISO 16290 **TRL 4** |
| Fail-closed CLI | `tests/test_cli_baselines.py`, README | `small --seed 42` GREED → exit 2 / `ASSET_OVERLAP` |
| Lockfile Python | `requirements-lock.txt` + CI job `lockfile` | тот же SHA `bd09d13`, без win32 `tzdata` |

РЭС «Северный» — типы оборудования и открытые нормы. **Не** выгрузка ПАО «Россети».

---

## 1. Техническая зрелость движка SynAPS (не продукт GridPlan)

Срез ниже — про upstream. Для заявки достаточно знать: GridPlan стоит на этом движке и **пин закрыт**. Не копировать в анкету «25 конфигов / 129 модулей» как возможности РЭС-планировщика.

| Свидетельство | Где (репо SynAPS) | Статус |
|---|---|---|
| Именованные конфигурации солверов | `synaps/solvers/registry.py` | в master пина |
| Strict-детерминизм CP-SAT | ADR + тесты upstream | в пине |
| FeasibilityChecker | `synaps/solvers/feasibility_checker.py` | fail-closed, используется GridPlan |
| Бенчмарки Brandimarte / cover-масштаб | `benchmark/` upstream | **другой домен**, см. старый §8 |

Пути `docs/adr/…` живут в **SynAPS**, не в публичном дереве GridPlan.

## 2. Adversarial-аудит движка (архивная рамка)

Исторические «волны» закрыты регрессиями в upstream. В заявку МИК **не** выносить жаргон RT/G11 и не обещать «14 волн за день» как критерий зрелости продукта. Для жюри: `tests/test_adversarial_*.py` в GridPlan ловят подделку графика (перекрытие, ЗИП, квалификации, неизвестные id).

## 3. Научная валидация архитектуры (рамка, не измерение пилота)

| Тезис | Подтверждение 2025–2026 |
|---|---|
| LBBD для энергокритериев в scheduling | Juvigny et al., arXiv:2601.06542 |
| Антимиопийный RHC | arXiv:2510.02502 |
| ML только solver-preserving | arXiv:2604.21891 |
| Joint crew scheduling | IEEE TPWRS 2025 |

Полная библиография — локальный архив; **не прилагать** к анкете как «наш результат на сети».

## 4. Соответствие доменной модели

GridPlan добавляет поверх движка: окна ПЛ, ЗИП как расход, frozen-строки, simultaneous-outage bans, отчёт жюри. Режим N-1 и SAIDI **отсутствуют** (`docs/limitations.md`).

## 5. Демо-артефакты (продукт)

```bash
python -m pytest -q
python benchmark/jury_benchmark.py
# small/seed 42 + GREED → exit 2 (ASSET_OVERLAP), это fail-closed, не «зелёное» демо
python -m synaps_gridplan synthesize --mode small --seed 12 -o feeder.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
```

Сценарии: `07_DEMO_SCENARIOS.md`. Не использовать `python -m synaps solve tiny_3x3.json` как демо заявки.

## 6. Городская значимость

Пилот МИК интересен городу, если контур связан с электроснабжением Москвы (группа «Россети», в т.ч. Московский регион) и проходит на городской/корпоративной площадке программы. Цифры «1 млн светильников / 3000 электробусов» — контекст ДЖКХ, **не** KPI GridPlan.

## 7. Честные ограничения

1. Живого внедрения нет → измеримый пилот, не «уже в ДЗО».
2. Именованный ТОиР-инстанс — 55 работ (РЭС «Северный»). Генератор 200/600: GREED проходит проверку, FIFO — нет. 50k/500k движка — другой домен.
3. Proof logging VeriPB — не в runtime. Сегодня: чекер + dual bound CP-SAT на малой постановке.
4. Shifts/calendars/safety/service area — notary-hard, если непусты; в поиске GREED/CP-SAT не участвуют (`limitations.md` п.6).

## 8. Свежие числа (18.08.2026) — заменяют срез 16.08

Писать в заявку только с оговоркой «синтетика».

### 8.1. Продукт GridPlan 0.1.1

| Прогон | Результат | Чего это не доказывает |
|---|---|---|
| `pytest -q` | **96 passed** / ~22 с | Не пилот ДЗО |
| `benchmark/jury_benchmark.py` (РЭС «Северный») | FIFO **107** / GREED **0**; отпечаток плана GREED **`e2095325f0210065`** (закоммиченный `jury_report.md`) | Не живой РЭС Россетей |
| `benchmark/emergency_day_benchmark.py` (узел «Восточный») | FIFO **27** / GREED **0**; ДГУ; замороженная ПЛ-0901-14 не сдвинута repair'ом; 2 прогона идентичны | Не данные сетевой; не реконструкция живого филиала |
| `benchmark/results/scale_report.md` (фидер 200/600) | GREED **0** / FIFO ломает окна; сборка 600 ~3 с | Не выгрузка ДЗО |
| CP-SAT `slow` (живой 16.08) | OPTIMAL makespan **30600** = bound, gap 0% | Не оптимум по недоотпуску / SAIDI |
| `gres-block` | GREED чистый, FIFO нет | Не Конаковская ГРЭС, не ЭЛ5 |
| CLI `small --seed 42` GREED | exit **2**, `ASSET_OVERLAP` | Не сломанный install; fail-closed |

Пин: `bd09d13`. Публичная история GitHub: `eeb1acc` (пакет 0.1.1), `b72484d` (fail-closed CLI / паритет checker), `c83c849` (пин `af72943`), `736251d` (пин `bd09d13`), `0a798e3` (APPLICATION: Россети / команда / TAM, Linux lockfile). Внутренние 0.1.2–0.1.16 — локальная ветка `archive/local-history`, к заявке не прилагать.

Архивный срез **не использовать** (14.08 и ранее): пин `6dd92ea`, «55 passed / 11.3 с», «FIFO 61», HEAD `23d9d08` / `02dacda`. Заменён таблицей выше.

### 8.2. Движок SynAPS (синтетика другого домена)

Оставляем как ответ на вопрос «тянет ли ядро масштаб», с жёсткой оговоркой.

| Прогон | Что измерено | Чего это не доказывает |
|---|---|---|
| 50k GREEDY_COVER | порядка секунд, FEASIBLE | Не N-1, не SAIDI, не ТОиР сети |
| 500k GREEDY_COVER | ~5·10⁵ оп, сотни секунд, гигабайты RSS | Не кабельный цех заказчика и не график РЭС |
| Кабельный нервный месяц | ~20k оп, cover | Не Москвакабельмет; не аргумент пилота Россетей |

Поля `shift_calendar` / `safety_constraints` / `service_area` — notary-hard, если непустые; в поиске не участвуют.
