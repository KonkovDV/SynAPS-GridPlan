# SynAPS-GridPlan

<p align="center">
  <img src="docs/synaps-gridplan-logo.jpg" alt="SynAPS-GridPlan" width="720">
</p>

Воспроизводимое лабораторное ядро планирования работ **ТОиР**: генерация
графика отдельно, независимая проверка отдельно. Бригады, окна отключения,
ЗИП, заморозка согласованных заявок ПЛ и явные запреты «эти два аппарата
не должны быть отключены сразу». Поиск слотов —
[SynAPS](https://github.com/KonkovDV/SynAPS). Проверка правил — отдельный
fail-closed чекер на Python; Rust реализует **доменный** контур с тестами
паритета, но не весь чекер движка SynAPS.

[![CI main](https://github.com/KonkovDV/SynAPS-GridPlan/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/KonkovDV/SynAPS-GridPlan/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](https://www.python.org/)

Если питч, заявка или этот README расходятся с [docs/LIMITS.md](docs/LIMITS.md)
— верен LIMITS.

| | |
| --- | --- |
| Базовая версия | **0.1.8** [V1] |
| Базовая ветка | `main` |
| Пин SynAPS | [`6178c93`](https://github.com/KonkovDV/SynAPS/commit/6178c93b705ff58be21fa74a98651883a2da1169) [V2] |
| Зрелость | **TRL 4 по ISO 16290: лабораторные фикстуры, не пилот на предприятии** (`versions.py`) [V3]. Не сертификат, **не ГОСТ Р 58048 УГТ4/5**. |
| Счёт pytest | [`docs/TEST_COUNT.txt`](docs/TEST_COUNT.txt) (`python -m pytest --collect-only -q`) [T1] |
| Реестр утверждений | [docs/CLAIMS_REGISTRY.md](docs/CLAIMS_REGISTRY.md) — verified / assumption / target / withdrawn |
| Запрещённые формулировки | [`docs/BANNED_CLAIMS.txt`](docs/BANNED_CLAIMS.txt), CI: `python scripts/lint_claims.py` |
| Границы | [docs/LIMITS.md](docs/LIMITS.md) |
| Пакет подачи | [`SynAPS_GridPlan.pptx`](SynAPS_GridPlan.pptx) (извлечённый текст: [`docs/DECK_TEXT.txt`](docs/DECK_TEXT.txt)) |
| Энерготехнохаб [P6] | Приём **продлён до 2 октября 2026 включительно**; оценка и собеседования 3–11 октября; Демо-день 14–20 декабря [P7]. Сверка 01.10.2026: страница [etechhubspb.ru/accelerator](https://www.etechhubspb.ru/accelerator) и [новость МФТИ от 29.09](https://www.mipt.ru/news/iz-nauki-v-promyshlennost-mfti-i-energotekhnokhab-peterburg-zapuskayut-programmu-po-vnedreniyu-tekhn). Факт подачи GridPlan в git не зафиксирован. Записка: [docs/ETECHHUB_APPLICATION.md](docs/ETECHHUB_APPLICATION.md) (даты в ней от 18.09, устарели) |
| Приз программы | 1 500 000 ₽ — потолок *eligibility* в анонсе СПбПУ, не выплата GridPlan [P8] |
| Одна фраза заявки | [docs/APPLICATION_TOIR_SCENARIO.md](docs/APPLICATION_TOIR_SCENARIO.md) |
| Дек v7 (не отправлять) | [docs/PITCH_V7_FACTCHECK.md](docs/PITCH_V7_FACTCHECK.md) |
| Академия инноваторов, 10-й поток | опубликованный приём до **14.09.2026**; на сверке 18.09 срок прошёл. Не путать со сроком Энерготехнохаба. Записка: [ACADEMY_APPLICATION.md](ACADEMY_APPLICATION.md) |
| Исторический пакет другой программы | [APPLICATION.md](APPLICATION.md): марафон «Энергия будущего». PDF 0.1.4: [`_SUBMIT_MIK_2026_08_18/SynAPS-GridPlan-marathon-0.1.4.pdf`](_SUBMIT_MIK_2026_08_18/SynAPS-GridPlan-marathon-0.1.4.pdf) — не пакет подачи |
| Практика | [PRACTICE.md](PRACTICE.md) |
| Аудит | [AUDIT.md](AUDIT.md) |
| УГТ / IP / пилот | [ГОСТ Р 58048](docs/UGT_GOST_R_58048.md), [IP и open-core](docs/IP_AND_OPEN_CORE.md), [one-pager пилота](docs/PILOT_ONEPAGER.md) |
| Автор в git | один: Коньков Д.В. ([CITATION.cff](CITATION.cff)). Предметный эксперт ТОиР в репозитории не назван |

English: crew- and window-constrained maintenance scheduling on SynAPS, with an
independent domain checker. Lab fixtures only. Not N-1, not SAIDI, not a plant
pilot. TRL 4 per ISO 16290: lab fixtures, not a plant pilot. Not GOST R 58048
certification. 187-FZ (KII) compliance is not claimed. ПАО «Россети» is not a
documented GridPlan customer.

## Что открывать на GitHub

| Файл | Зачем |
| --- | --- |
| [`SynAPS_GridPlan.pptx`](SynAPS_GridPlan.pptx) | пакет подачи (14 слайдов) |
| [`benchmark/results/jury_report.md`](benchmark/results/jury_report.md) | FIFO 107 / GREED 0 / CPSAT-30 на одном синтетическом JSON [B1] [B2] [B3] |
| [`docs/LIMITS.md`](docs/LIMITS.md) | границы; приоритет над питчем |
| [`docs/CLAIMS_REGISTRY.md`](docs/CLAIMS_REGISTRY.md) | единственный реестр цифр |
| [`docs/DECK_TEXT.txt`](docs/DECK_TEXT.txt) | текст дека, который диффит CI |
| [`docs/AI_WORK_PLAN_2026_10_01.md`](docs/AI_WORK_PLAN_2026_10_01.md) | триаж, Red Team, Murder Board и план работ после сверки 01.10.2026 |

Не пакет подачи: отозванный v7 ([факт-чек](docs/PITCH_V7_FACTCHECK.md)),
архивный PDF марафона в `_SUBMIT_MIK_2026_08_18/`, нумерованный каталог
`docs/00`–`docs/29` (исторические записки, не источник цифр).

CI на `main`: Python 3.12 и 3.13, Rust, lockfile. Гейты: pytest, `lint_claims.py`,
снимок [`docs/TEST_COUNT.txt`](docs/TEST_COUNT.txt) [T1], текст дека,
`jury_report.md` (включая раздел D / CP-SAT), паритет native на `res_severny`.

## Состояние на 1 октября 2026

Перепроверка `main` на `f56e693` локально (Windows, Python 3.12.10, OR-Tools 9.15):
весь набор pytest из [T1] прошёл, включая `slow` CP-SAT; `cargo test --locked`,
clippy и rustfmt зелёные; ruff и mypy по `src tests scripts`, `lint_claims.py`
и `extract_deck_text.py --check` проходят. Это прогон одной машины, не CI.

Что требует внимания:

- Открытые PR Dependabot ([#42](https://github.com/KonkovDV/SynAPS-GridPlan/pull/42),
  [#43](https://github.com/KonkovDV/SynAPS-GridPlan/pull/43)) красные: CI сверяет
  `sbom/cyclonedx-native.json` с `Cargo.lock`, а Dependabot инвентарь не пересобирает.
- Апстрим SynAPS ушёл на три коммита вперёд от пина `6178c93` [V2]; пин не обновлялся.

Пробелы контура, подтверждённые пробами Red Team 01.10.2026 (поведение 0.1.8,
исправления не выпущены):

- **Солвер не видит смены бригад.** Адаптер не передаёт `Crew.shift_calendar` в
  `WorkCenter.calendar` пиннутого SynAPS. Чекер смены проверяет, поэтому план со
  сменами честно отклоняется, но GREED и CP-SAT его не строят. Во всех фикстурах,
  включая РЭС «Северный», бригады доступны круглосуточно.
- **Часть жёстких правил есть только в постпроверке.** Взаимоисключение отключений
  одного актива, запреты пар отключений и остаток ЗИП не закодированы в модели
  солвера. Отказ GREED на `--seed 42` (`ASSET_OVERLAP`) показывает именно это.
- **`check` перепроверяет допустимость и не подтверждает оптимальность.**
  Импортированный `optimal` понижается до `feasible`; исходный ярлык пишется
  в `claimed_status` (`optimality_origin=imported_not_reproven`). Native `check`
  статус из файла не копирует.
- **Часть полей каталога не влияет на вердикт.** `voltage_level`,
  `parent_asset_id`, `coordinates`, `failure_modes`, `warehouse_location`
  попадают в `unenforced_fields`. `lead_time_min` запрещает старт только при
  нулевом остатке и без даты пополнения; остаток он не создаёт. Граница:
  [docs/LIMITS.md](docs/LIMITS.md).
- **Граф предшествования — только линейная цепочка.** Цикл, join и fan-out
  отвергаются при загрузке и в Python, и в native. Случайно допустимый порядок
  больше не выглядит проверенным планом.
- **Базовая линия слабая.** Календарный FIFO не знает окон отключения и переездов.
  Разрыв FIFO/GREED — отрыв от нижней планки, не выигрыш у диспетчера.
- **Чекер независим не полностью.** `constraints.py` берёт вывод legacy-заморозок
  из `adapter.py`; общая ошибка там затронет и компиляцию, и проверку.

План устранения и вопросы для защиты: [`docs/AI_WORK_PLAN_2026_10_01.md`](docs/AI_WORK_PLAN_2026_10_01.md).

## Что делает и чего не делает

**Делает.** Назначает бригады на работы при квалификациях, согласованных окнах
отключения, одной единице ЗИП на перечисленную позицию, линейных цепочках
предшественников, замороженных строках ПЛ и явных запретах пары активов.
Второй контур проверки, независимый от поиска, отклоняет план с жёстким
нарушением. В Python принимать результат следует по `outcome.ok`: допустимый
статус, `verified_feasible=true` и ноль жёстких нарушений одновременно.
Поле `schedule.status` само по себе недостаточно.

**Не делает.** Нет модуля трудового права, нет СНиП, нет норм непрерывного
отдыха. Нет SCADA, EMS, GIS, прогноза отказов, N-1 / потокораспределения,
оптимизации SAIDI, ЗИП как BOM-количества, графов предшественников с join /
fan-out, замены ЕАМ / 1С:ТОИР. `Crew.shift_calendar` — окна доступности, не
ростер смен. Оценка риска в отчёте — справочный прокси невыполненных работ,
не измеренное снижение вероятности аварии. Ночные 5k-прогоны ядра SynAPS —
другой домен.

```mermaid
flowchart LR
  A[JSON постановка] --> B[SynAPS: GREED / FIFO / CP-SAT]
  B --> C[Чекер движка + доменные правила Python]
  C --> E{статус и все проверки пройдены?}
  E -->|да| F[verified_feasible]
  E -->|нет| G[отказ в подтверждении]
  A --> D[Rust: FIFO + доменные правила]
  D --> H[отдельный ограниченный контур]
```

Мировая практика (Hydro-Québec TMS: формализуемые правила отдельно от
power-flow; публичный кейс Hexaly/PosAm/ČEZ — field workforce, другой класс
продукта): [PRACTICE.md](PRACTICE.md). Явный запрет двух отключений не
сертифицирует Tier III. Электрическая безопасность **вне скоупа**. Ни одна
из названных систем не является клиентом, партнёром или внедрением GridPlan.

## Пять минут для жюри

```bash
python -m pip install -e ".[dev]" --force-reinstall
python -m synaps_gridplan version
python benchmark/jury_benchmark.py --cpsat
python scripts/lint_claims.py
python scripts/extract_deck_text.py --check
python scripts/evidence_bundle.py --skip-pytest
```

`version` должен напечатать `0.1.8` и пин `6178c93…`. `jury_benchmark.py --cpsat`
пишет разделы A–D в `benchmark/results/jury_report.md` на **том же**
синтетическом РЭС «Северный». `evidence_bundle.py` без `--skip-pytest`
прогоняет pytest, jury и CP-SAT. JSON пишется в `benchmark/results/`
(gitignore). Не складывать этот прогон с аварийными сутками или scale-фидером.
Время стены в отчёте — машина прогона, не SLA [B7].

| Что увидеть | Команда / файл |
| --- | --- |
| GREED на синтетическом РЭС «Северный» проходит проверку, календарный FIFO — нет | `benchmark/results/jury_report.md` |
| CPSAT-30 на том же JSON: `optimal`, 0 жёстких, dual bound = makespan | тот же отчёт, раздел D; `python benchmark/jury_benchmark.py --cpsat` |
| Fail-closed: GREED на `small --seed 42` пишет план и выходит **2** (`ASSET_OVERLAP`) | блок ниже |
| Тот же маленький фидер, но проверенный | `--seed 12`, exit **0** |
| Текст дека совпадает с git | `python scripts/extract_deck_text.py --check` |
| Мировая практика, без претензии на пилот | `python -m synaps_gridplan practice` |

Демо теперь выходит с кодом 2, если положительные утверждения о GREED,
перепланировании, сохранении заморозки или детерминизме не подтверждены.
Успешное создание Markdown не считается успешным экспериментом.

Если `source` указывает в `site-packages`, а не в `<репо>/src/synaps_gridplan`:

```bash
python -m pip install -e ".[dev]" --force-reinstall --no-deps
```

## Доказательства (синтетика)

| Результат | Где |
| --- | --- |
| [B1] [B2] РЭС «Северный» (55 работ, 7 бригад, 39 активов): FIFO **107** жёстких нарушений, GREED **0** | `tests/test_res_severny.py`, `benchmark/results/jury_report.md` |
| [B3] CP-SAT (`CPSAT-30`) на том же JSON: `optimal`, 0 жёстких, dual bound = makespan. GREED makespan совпал в пределах 1 мин; оптимальность эвристики не утверждается | `test_res_cpsat_proves_optimal_makespan` (маркер `slow`), раздел D `jury_report.md` |
| Перепланирование не двигает замороженные строки ПЛ | Scenario B, те же тесты |
| Native Rust `check` на `res_severny`: доменный паритет kind с Python; `verified_feasible` у native остаётся false, потому что `travel_minutes` непуста | `tests/test_native_parity.py` |
| Блок ГРЭС (синтетика, не станция): GREED чист, FIFO нет | `tests/test_gres_block.py` |
| Два ввода в зал (не М9): GREED чист; оба ввода сразу — `SIMULTANEOUS_OUTAGE_BAN` | `tests/test_dual_feed_hall.py` |
| [B4] Аварийные сутки (23 работы): FIFO 27 / GREED 0 | `tests/test_emergency_day.py`, `benchmark/results/emergency_day_report.md` |
| [B5] Фидер 200 / 600 работ: GREED проверен, FIFO ломает окна | `tests/test_scale_feeder.py`, `benchmark/results/scale_report.md` |
| Чекер ловит overlap, ЗИП, квалификации, короткую длительность | `tests/test_adversarial_*.py` |
| Аудит заморозки, мутаций модели, ID-map, импорта, CSV и UTC | `tests/test_audit_regressions.py`, `tests/test_import_export_audit.py`, `tests/test_time_contract.py`, `tests/test_final_audit_guards.py` |

РЭС «Северный» копирует **типы** оборудования и открытые нормы. Это не
именованный участок Россети и не промышленные данные. Сохранённые отчёты —
снимки прежних запусков, не доказательство результата произвольного commit.

GREED и FIFO — эвристики (`heuristic_feasible`). Доказательство CP-SAT относится
к его модели и целевой функции. Адаптер выбирает одно окно из нескольких;
это не полный поиск по объединению окон и не доказательство глобальной
невыполнимости исходной многовариантной задачи. Все задержки отдельных работ
также нельзя отождествлять с агрегированной tardiness цепочки в SynAPS.

Если жюри спросит, подтверждает ли Rust «ноль» GREED на `res_severny`: доменную
часть — да, слой движка считает Python, `engine_checked=false`. Обе границы
закреплены тестами.

0.1.8 закрывает Red Team 0.1.8–0.1.9: `deque` в `_job_chains`, FIFO
``latest_finish``, заметка об усечении нарушений, overflow в `_cross_refs`.
[Аудит fail-closed вошёл в 0.1.5](https://github.com/KonkovDV/SynAPS-GridPlan/pull/14).
Badge относится к `main`. Доказательства аудита привязаны к commit в `AUDIT.md`,
а не к номеру версии или картинке из дека.

## Установка

Python ≥ 3.12. SynAPS закреплён **коммитом**, не веткой.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python -m synaps_gridplan version
python -m synaps_gridplan practice
python -m pytest -q -m "not slow"
```

## Контракт входа (0.1.8)

- ISO-даты передавайте с `Z` или явным смещением, например
  `2026-09-01T09:00:00+03:00`. Unix-время, boolean и naive datetime без зоны
  отвергаются, в том числе в календарях бригад. Aware-моменты нормализуются в UTC.
- Неизвестные поля верхнего и вложенного GridPlan-документа отвергаются,
  включая native catalogs и лишние ключи календаря бригад. Расширения — только
  в `domain_attributes`. JSON Schema в `schemas/` — конверт верхнего уровня плюс
  вложенный Pydantic-инвентарь; jsonschema проверяет синтетические дампы.
  Это не полная Draft 2020-12-норма произвольного будущего v2 и не байтовый
  round trip.
- ID внутри каталогов уникальны; ссылки должны существовать. Мутации
  `model_copy(update=...)` повторно проверяются на границе компилятора и чекера.
- `immutable:false` не закрепляет слот. Неизменяемую ПЛ нельзя отменить пустым
  списком ожидаемых заморозок или сменой строки в сохранённом плане.
- Пустая `travel_minutes` означает явное допущение нулевого переезда. В непустой
  матрице реальный маршрут A→B не заменяется маршрутом «база→B». Начальные/
  конечные поездки и индивидуальные маршруты при `max_parallel>1` требуют
  отдельного согласования модели; полноценный VRP здесь не заявлен.
- Плотная setup-матрица проверяется до построения по upstream-лимиту
  2 000 000 элементов. Дополнительно действуют лабораторные квоты JSON и
  каталогов (`synaps_gridplan.limits`). Это не SLA CPU/памяти процесса.
- `approved=true`, происхождение данных и TRL — не подпись, не независимая
  проверка источника и не регуляторный допуск.

## Команды

Проверенный демо-стенд жюри (РЭС «Северный», включая CP-SAT):

```bash
python benchmark/jury_benchmark.py --cpsat
```

Маленький фидер, GREED проходит проверку (exit 0):

```bash
python -m synaps_gridplan synthesize --mode small --seed 12 -o feeder.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
python -m synaps_gridplan check feeder.json result.json
python -m synaps_gridplan report result.json --format markdown
```

`report` **не перепроверяет** сохранённый план. Импорт помечается
`imported_snapshot_not_rechecked`. Повторная проверка — `check PROBLEM RESULT`
(`verification_origin=independent_recheck`); сохранённый `verified_feasible`
игнорируется. CSV экранирует формулоподобный текст; JSON не добавляет этих
CSV-префиксов. Интерполяция Markdown сплющивает перевод строки, backticks и
угловые скобки; это не общий HTML-sanitizer. Типизированный рендеринг не
обещает побайтовый JSON round trip. Это не подпись файла.

Fail-closed на том же контуре (`--seed 42` → exit **2**, `ASSET_OVERLAP`):

```bash
python -m synaps_gridplan synthesize --mode small --seed 42 -o feeder.json
python -m synaps_gridplan solve feeder.json --solver GREED -o result.json
```

Это штатная работа продукта, не сломанный install. Native FIFO на том же
seed тоже выходит **2**.

Коды Python CLI:

| Код | Смысл |
| --- | --- |
| **0** | Команда выполнена. Для `solve`/`disrupt`/`check` это также означает подтверждённый план. |
| **2** | План не прошёл проверку либо обработана ошибка аргументов/ввода/вывода. При ошибке входа файл плана может не появиться. |
| **1** | Неперехваченная ошибка или проблема окружения. |

Остальные постановки:

```bash
python benchmark/emergency_day_benchmark.py
python benchmark/scale_benchmark.py
python -m synaps_gridplan synthesize --mode gres-block --seed 42 -o gres.json
python -m synaps_gridplan synthesize --mode dual-feed-hall --seed 42 -o hall.json
```

`gres-block` и `dual-feed-hall` собирает только Python. Native `synthesize`
этих режимов намеренно завершается ошибкой.

Rust: FIFO и доменные проверки, без реализации всего SynAPS engine checker:

```bash
cd native/synaps-gridplan-rs
cargo test --locked
```

Границы и отдельные коды native CLI — в [native README](native/synaps-gridplan-rs/README.md).
Для непустой задачи любая непустая `travel_minutes` блокирует native-подтверждение,
даже если матрица заполнена нулями. Доменный verdict выдаётся отдельно;
`engine_checked=false`. Неподдерживаемое ограничение — не доказанное нарушение
и не сертификат невыполнимости. Не удаляйте реальные переезды ради зелёного флага.
Native `check` не заменяет проверку всех ограничений движка Python.

## Дерево

```
src/synaps_gridplan/        Python-пакет
native/synaps-gridplan-rs/  Rust: FIFO и доменные проверки
schemas/                    JSON Schema (не замена семантической валидации)
benchmark/                  РЭС / jury / аварийные сутки / масштаб
tests/
docs/LIMITS.md              границы продукта
docs/CLAIMS_REGISTRY.md     реестр утверждений
docs/DECK_TEXT.txt          извлечённый текст пакета подачи
docs/TEST_COUNT.txt         снимок pytest --collect-only
docs/AI_WORK_PLAN_2026_10_01.md  триаж и план работ после сверки 01.10.2026
SynAPS_GridPlan.pptx        пакет подачи (14 слайдов)
scripts/                    lint_claims, extract_deck_text, evidence_bundle
AUDIT.md                    доказательства аудита и оставшиеся gate
ACADEMY_APPLICATION.md      подготовка к 10-му потоку Академии (срок приёма прошёл)
APPLICATION.md              исторический пакет энергетического марафона
_SUBMIT_MIK_2026_08_18/     архив подачи 18.08.2026; PDF 0.1.4 — не пакет Энерготехнохаба
PRACTICE.md                 мировая практика и границы
CITATION.cff                автор в git
sbom/                       CycloneDX-инвентарь lockfile, не сканер уязвимостей
requirements-lock.txt       Linux-пин Python + SHA SynAPS
```

## Лицензия

MIT — [LICENSE](LICENSE).
