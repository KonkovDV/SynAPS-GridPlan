# План работ для ИИ-агента: триаж, Red Team, Murder Board (сверка 01.10.2026)

Рабочий документ для исполнителя, не публичный материал и не заявка.
Ревизия: `main` @ `f56e693`, продукт **0.1.8**, пин SynAPS `6178c93`.
Числа ниже — наблюдения локальных проб 01.10.2026. В README, дек или заявку их
переносить только через строку [`CLAIMS_REGISTRY.md`](CLAIMS_REGISTRY.md).

## 0. Правила для исполнителя

1. Прочитать `AGENTS.md`, [`LIMITS.md`](LIMITS.md), [`CLAIMS_REGISTRY.md`](CLAIMS_REGISTRY.md).
   При конфликте верен `LIMITS.md`.
2. Не заявлять N-1, SAIDI, живой EL5, INFIMUM, партнёрство с ПАО «Россети»,
   соответствие 187-ФЗ, сертификат ГОСТ Р 58048. ISO 16290 TRL 4 — самооценка.
3. Одна задача — одна ветка — один PR. Сначала падающий тест, потом исправление.
   Не ослаблять assert ради зелёного CI.
4. Перед PR прогнать все гейты (раздел 8). Новые числа в README — только с `claim_id`.
5. После изменения публичного поведения: `CHANGELOG.md`, `AUDIT.md` (новый раздел
   с commit), при необходимости `LIMITS.md` и реестр.

## 1. Снимок состояния 01.10.2026

| Проверка | Результат |
| --- | --- |
| `pytest -m "not slow"` | 256 passed, 1 deselected |
| `pytest -m slow` (CP-SAT на `res_severny`) | 1 passed |
| `cargo test --locked`, clippy `-D warnings`, `cargo fmt --check` | зелёные (58 Rust-тестов) |
| ruff/mypy по `src tests scripts`, `lint_claims.py`, `extract_deck_text.py --check` | зелёные |
| `ruff check .` (весь репозиторий) | 5 × E501 в `benchmark/` — CI `benchmark/` не линтует |
| GitHub CI `main` | зелёный (последний push-прогон 19.09) |
| Открытые PR | [#42](https://github.com/KonkovDV/SynAPS-GridPlan/pull/42), [#43](https://github.com/KonkovDV/SynAPS-GridPlan/pull/43) (Dependabot cargo) — красные |
| Апстрим SynAPS | `main` на 3 коммита впереди пина (`f80449f`, `07f11eb`, `cf10ca3`) |
| Энерготехнохаб | приём продлён до **02.10.2026 включительно** (P6/P7 обновлены в реестре) |

## 2. Триаж

P0 — ложное подтверждение или срыв ближайшего дедлайна. P1 — продукт не решает
реалистичную постановку или вводит в заблуждение. P2 — качество, долг, гигиена.
Это инженерный триаж, не CVSS.

| ID | P | Проблема | Доказательство | Что сделать | Приёмка |
| --- | --- | --- | --- | --- | --- |
| T-01 | P0 | Срок Энерготехнохаба продлён до 02.10; живые документы говорят «до 25.09» | страница программы и новость МФТИ 29.09 | См. волну 0 | grep по живым документам не находит «7–25» как текущий срок |
| T-02 | P1 | Солвер не видит смены бригад: `WorkCenter.calendar` не заполняется | проба H1: смены 08–17 → GREED `ok=False`, 20 × `SHIFT_CALENDAR_VIOLATION`; `res_severny` → 21; длины `WorkCenter.calendar` = 0 | R-01 | фикстура со сменами, GREED и CP-SAT `ok=True` |
| T-03 | P1 | `check` переносит `status: optimal` из входного файла | проба H2: подделка `solver_config=CPSAT-30`, `status=optimal` → `check` exit 0, `status=optimal`, `claim_status=optimal`, `verification_origin=independent_recheck` | R-02 | тест: после `check` статус не выше `feasible`, исходный статус в `claimed_status` |
| T-04 | P1 | Взаимоисключение по активу, запреты пар и остаток ЗИП — только постпроверка | `small --seed 42` GREED → `ASSET_OVERLAP`; CP-SAT на `small` со сменами → `ASSET_OVERLAP` | R-03 | GREED/CP-SAT на seed 42 дают `ok=True` либо честный `infeasible` от модели |
| T-05 | P1 | Базовая линия — соломенное чучело: FIFO не знает окон и переездов | `baselines.plan_fifo` | R-04 | в `jury_report.md` второй baseline с учётом окон; разрыв показан честно |
| T-06 | P1 | Поля принимаются, но не действуют: `lead_time_min`, `parent_asset_id`, `voltage_level`, `coordinates`, `failure_modes`, `warehouse_location` | проба H3: `lead_time_min=10**6` → план `ok=True` | R-05 | либо поле проверяется, либо ненулевое значение даёт явное предупреждение `UNENFORCED_FIELD` в metadata и строку в LIMITS |
| T-07 | P2 | Циклы и join в `predecessor_job_ids` проходят загрузку | проба H4: цикл A↔B принят, ловится только постпроверкой; H5: у C с двумя предшественниками компилируется одно ребро | R-06 | цикл → `ValueError` при загрузке; join/fan-out → явная ошибка или поддержка в компиляторе |
| T-08 | P2 | Dependabot PR не могут пройти CI: SBOM не пересобирается | лог прогона 36536396234: diff `sbom/cyclonedx-native.json` | R-07 | PR #42/#43 зелёные или закрыты с причиной |
| T-09 | P2 | Чекер зависит от компилятора: `constraints.py` импортирует `legacy_window_frozen_assignments` из `adapter.py` | импорт в `constraints.py:16` | R-08 | чекер не импортирует `adapter`; перекрёстный тест равенства выводов |
| T-10 | P2 | Пин SynAPS отстаёт на 3 коммита; в апстриме записан «GridPlan 0.1.2» | `gh api compare` | R-09 | ревью диффа, решение bump/не bump записано в `AUDIT.md` |
| T-11 | P2 | Устаревшие документы (даты, «Red team 23–24.09 не проведена», счёт Rust-тестов 48 vs 58) | grep | R-10 | раздел 9 в `AUDIT.md`, даты сверены |
| T-12 | P2 | Предметный эксперт не назван; Red Team с экспертами не проведена | `CITATION.cff`, `REDTEAM_DEFENSE_BRIEF.md` | человек, не ИИ | протокол сессии в git |

## 3. Red Team: пробы и как превратить их в тесты

Пробы запускались вне репозитория. Их нужно перенести в `tests/test_redteam_020.py`
как падающие тесты до исправления.

### H1. Смены бригад (T-02)

```python
from datetime import timedelta
from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.model import CrewCalendarWindow, GridPlanProblem
from synaps_gridplan.synthetic import synthesize_feeder

def day_shifts(p, a=8, b=17):
    rows, day = [], p.planning_horizon_start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day < p.planning_horizon_end:
        rows.append(CrewCalendarWindow(start=day + timedelta(hours=a), end=day + timedelta(hours=b)))
        day += timedelta(days=1)
    return rows

base = synthesize_feeder(n_assets=12, n_jobs=30, n_crews=4, seed=12, mode="small")
crews = [c.model_copy(update={"shift_calendar": day_shifts(base)}) for c in base.crews]
p = GridPlanProblem.model_validate(base.model_copy(update={"crews": crews}).model_dump(mode="python"))
oc = plan_with_config(p, solver_config="GREED")
assert all(wc.calendar for wc in oc.schedule_problem.work_centers)  # сейчас падает
```

Дополнительное наблюдение: если вручную подставить календарь в `WorkCenter.calendar`,
CP-SAT на `small` соблюдает смены (остаётся только `ASSET_OVERLAP`, см. T-04), а GREED
отказывается ставить работы (`UNSCHEDULED_JOB`). Причина: работы до 540 минут
плюс переезд не помещаются в 9-часовую смену, а апстрим проверяет
`[start - setup, end]` внутри одного интервала. Это вопрос модели, не только кода.

### H2. Оптимальность из файла (T-03)

Сценарий: `synthesize --mode small --seed 12` → `solve --solver GREED` → в JSON
результата выставить `outcome.solver_config="CPSAT-30"`, `outcome.status="optimal"`,
`schedule.status="optimal"` → `check` возвращает exit 0 и `status: optimal`.
Допустимость при этом перепроверена честно; ложным остаётся только ярлык оптимальности.

### H3–H5

- `lead_time_min=10**6` у всех ЗИП → план всё равно `ok=True`.
- Цикл `A.predecessor=[B]`, `B.predecessor=[A]` принимается моделью;
  `ok=False` с `PRECEDENCE_VIOLATION` и `ASSET_OVERLAP` — fail-closed, но без понятной ошибки.
- Join `C.predecessor=[A, B]`: в компиляции у C одно ребро; постпроверка прошла,
  потому что GREED случайно поставил B раньше C.

## 4. Murder Board: вопросы, которые убивают проект

Формат: вопрос → честный ответ сегодня → артефакт, который закрывает вопрос.

1. **«Где заказчик?»** Нет договора, письма, владельца площадки, данных.
   → Письмо о намерениях или протокол встречи с ДЗО/службой ТОиР; заполненный `PILOT_ONEPAGER.md`.
2. **«Ваши бригады работают круглосуточно?»** Да, во всех фикстурах. Солвер смены не видит (T-02).
   → R-01 + фикстура со сменами в `jury_report.md`.
3. **«FIFO 107 против GREED 0 — вы сравниваетесь с алгоритмом, который не знает окон?»** Да (T-05).
   → R-04: baseline с учётом окон, ручной план эксперта на том же JSON, CP-SAT как верхняя планка.
4. **«Чем вы лучше того, что уже работает?»** У СО ЕЭС — ПК «Заявки/Ремонты/Перечень» на CIM;
   у «Россети Кубань» — график вывода в ремонт в СУПА на 1С:Энергетика с интеграцией АСУРЭО;
   у «Россети Центр» — СОУР в реестре российского ПО. GridPlan их не заменяет.
   → Позиционирование «модуль проверки и оптимизации рядом с учётной системой»;
   импорт выгрузки СУПА/АСУРЭО-подобного формата (R-12). Что у этих систем нет
   независимой проверки и оптимизации — **гипотеза**, не проверена.
5. **«Как это ложится на регламент?»** ПП РФ № 86 (ред. 07.02.2026): сводный годовой
   график ремонта СО утверждает не позднее 31 августа (п. 15), месячный — не позднее
   24-го числа предыдущего месяца (п. 21). Это объекты диспетчеризации; распределительный
   ТОиР ДЗО живёт по своим СТО. → Режимы «годовой» и «месячный» с заморозкой утверждённого (R-13).
6. **«Чекер независим?»** Частично: общий Pydantic-контур, импорт из `adapter.py` (T-09).
   Rust-контур независим, но только доменный и не проверяет переезды.
   → R-08 + расширение native на travel или явный отказ в отчёте жюри.
7. **«Optimal у CP-SAT — оптимум чего?»** Оптимум скомпилированной модели: одно окно
   на работу, без взаимоисключения по активу и остатка ЗИП. Совпадение с полной
   задачей на `res_severny` получено, потому что постпроверка прошла.
   → R-03 и строгая формулировка B3 в реестре.
8. **«Масштаб?»** 55 работ для CP-SAT, 600 для GREED на синтетике. У РЭС за год — тысячи.
   → R-11: прогон 2–5 тыс. работ с бюджетом времени, ограничения памяти.
9. **«Bus factor?»** Один автор, эксперт ТОиР не назван. → Человек: назвать эксперта, `CITATION.cff`.
10. **«MIT — что вы продаёте?»** `IP_AND_OPEN_CORE.md`: услуги, внедрение, лицензия на
    данные/адаптеры. → Решение по лицензии адаптеров заказчика до пилота (человек).
11. **«КИИ и закупка?»** 187-ФЗ не заявляется. Реестр российского ПО — не исследован.
    → R-14: выписать требования реестра и ПП к закупкам ПО, без заявлений о соответствии.
12. **«LLM в направлении 02 — где он?»** В коде нет. → R-15 только после R-01…R-06.

## 5. OSINT (сверка 01.10.2026)

| Факт | Источник | Вывод |
| --- | --- | --- |
| Приём в акселератор продлён до 02.10 включительно; оценка 3–11.10; онлайн 15.10–11.11; очная сессия 11–13.11 (МФТИ); Демо-день 14–20.12 | https://www.etechhubspb.ru/accelerator ; https://www.mipt.ru/news/iz-nauki-v-promyshlennost-mfti-i-energotekhnokhab-peterburg-zapuskayut-programmu-po-vnedreniyu-tekhn | P6/P7 обновлены. Решение о подаче — за человеком, срок завтра |
| Новые техноброкеры: Н. Рождественская, А. Кушнер | страница программы | P11 обновлён. Брокеры программы, не партнёры |
| Итоги отбора не опубликованы | поиск 01.10 | ничего не утверждать |
| Репозиторий: 0 звёзд, 0 форков, релизы v0.1.4–v0.1.8, 2 открытых PR Dependabot | GitHub API | внешней валидации нет |
| SynAPS: последний push 12.09; 3 коммита после пина, один в `synaps/solvers/rhc/_window.py` | GitHub API | R-09 |
| СО ЕЭС: ПК «Заявки/Ремонты/Перечень», синхронизация с единой информационной моделью CIM | https://www.so-ups.ru/news/press/press-release-view/news/10400/ ; https://www.asureo.ru/2024/10/blog-post.html | формат обмена — CIM; R-12 |
| «Россети Кубань»: график вывода в ремонт в СУПА на 1С:Энергетика + АСУРЭО | https://eawards.1c.ru/projects/avtomatizaciya-vedeniya-grafika-vyvoda-oborudovaniya-v-remont-v-ao-rosseti-kuban-na-baze-1s-energetika-310693/ | действующий конкурент/точка интеграции |
| «Россети Центр»: СОУР в реестре российского ПО (26.01.2026) | https://www.cnews.ru/news/line/2026-01-26_boris_ebzeev_rosseti_tsentr | то же; ориентир по реестру ПО |
| ПП РФ № 86, ред. 07.02.2026, пп. 15 и 21 | https://www.consultant.ru/document/cons_doc_LAW_375386/2726d992015af202eb34a08458e09416eacd2110/ | R-13 |

Перед переносом любой строки в публичные материалы — завести строку в реестре со
статусом и датой доступа.

## 6. SOTA 2026: что брать, что нет

| Направление | Источник | Применение в GridPlan |
| --- | --- | --- |
| CP для формализуемых правил + симулятор и constraint acquisition для потокораспределения | Popovic et al., CP 2022; Barral et al., CPAIOR 2024 (уже в `PRACTICE.md`) | сохранить двухслойную архитектуру; электрику не обещать |
| Годовое планирование отключений с еженедельным пересчётом (Elia OPSO) | https://www.n-side.com/en/insights/en-an-integrated-approach-for-the-scheduling-of-grid-activities-requiring-outages/ | режимы «год/месяц/неделя» с заморозкой (R-13) |
| Маршрутизация бригад + минимизация простоя линии (LNS + MIP) | Goel & Meisel, EJOR 2013 | hull цепочки уже есть; переезды и простой — в целевую функцию |
| CP-SAT для смен с переходом через полночь, перерывами | CP-WSP, arXiv 2607.05177 | модель смен для R-01; дробление многодневных работ |
| OR-Tools 9.15: работа над LRAT-доказательствами | https://github.com/google/or-tools/releases | исследовать проверяемый сертификат оптимальности для B3 (R-16) |
| LLM → модель CP: CP-Bench (до ~70% точности), CP-Agent (100% на исправленном CP-Bench с обратной связью исполнения) | arXiv 2506.06052; arXiv 2508.07468 | извлечение JSON из заявок только с чекером в контуре (R-15) |
| LLM без солвера: ConstraintBench — лучшая модель 65% допустимости; домен crew assignment — 0,8% | arXiv 2602.22465 | аргумент: нельзя доверять LLM-плану без независимой проверки |
| DRL/трансформеры для диспетчеризации бригад при авариях | arXiv 2509.04308 | не брать в 0.2.x; другой класс задачи |

## 7. План работ по волнам

### Волна 0 — до 02.10.2026 23:59 (дедлайн Энерготехнохаба)

Сделано 01.10.2026. Код солвера не менялся.

- [x] Даты в `docs/ETECHHUB_APPLICATION.md`, `APPLICATION.md`,
  `docs/APPLICATION_TOIR_SCENARIO.md`, `docs/PILOT_ONEPAGER.md`,
  `ACADEMY_APPLICATION.md`, `docs/PITCH_V7_FACTCHECK.md`. Строки
  `tests/test_claims_truth.py` сохранены. P4 в реестре уточнён: 25.09 больше
  не текущий дедлайн P6.
- [x] Дек не пересобирался: в `docs/DECK_TEXT.txt` старого срока нет.
- [x] Чек-лист подачи — раздел в `docs/ETECHHUB_APPLICATION.md`. Подавать или нет
  решает человек.

### Волна 1 — 0.1.9 «честность контура» (1–2 недели)

- [x] **R-02 (T-03).** `recheck_plan` понижает импортированный `optimal` до
  `feasible`, пишет `claimed_status` и `optimality_origin=imported_not_reproven`.
  Native `check` статус не копирует; регрессия в `cli_regressions.rs`.
  Версия пакета не бампилась: это один пункт волны, не релиз 0.1.9.
- [x] **R-05 (T-06).** `lead_time_min` жёсткий только при usable = 0 и без
  `replenishment_date` (старт раньше горизонта + задержка). Остаток не
  увеличивается. Ненулевой остаток, дата пополнения и декоративные поля
  (`voltage_level`, `parent_asset_id`, `coordinates`, `failure_modes`,
  `warehouse_location`) — `UNENFORCED_FIELD` в metadata, не в счётчике
  жёстких нарушений. Семантика в `docs/LIMITS.md`. Python и native.
- [x] **R-06 (T-07).** Выбор: явная ошибка, не компиляция DAG. Цикл, join и
  fan-out отвергаются в `GridPlanProblem` и в native `validate_refs`. Сообщение
  называет работы. Линейные цепочки фикстур не затронуты.
- **R-07 (T-08).** Workflow на `pull_request` от `dependabot[bot]`: пересобрать
  `sbom/` и закоммитить в ветку PR, либо исключить cargo-патчи из SBOM-диффа.
  Права `contents: write` только этому job.
- **R-08 (T-09).** Перенести вывод legacy-заморозок в модуль без зависимости от
  компилятора; тест равенства выводов компилятора и чекера.
- **R-10 (T-11).** `AUDIT.md` §9 «Truth pass 01.10.2026»; `CHANGELOG.md` Unreleased;
  `ruff check benchmark` — исправить 5 × E501 и включить `benchmark` в CI ruff.

### Волна 2 — 0.2.0 «модель солвера = правила чекера» (2–4 недели)

- **R-01 (T-02).** В адаптере: `WorkCenter.calendar` = пересечение `shift_calendar` и
  `availability` (пустой список = круглосуточно). Решить семантику переезда внутри
  смены и привести GridPlan-чекер к той же формуле `[start - setup, end]`.
  Работы длиннее смены: дробить на цепочку дневных операций на одном активе —
  hull цепочки уже даёт непрерывное отключение. Новая фикстура
  `res_severny_shifts` с реалистичными сменами (по МСК) в `jury_report.md` (новый раздел E).
- **R-03 (T-04).** Взаимоисключение по активу: `AuxiliaryResource` с `pool_size=1`
  на актив для работ с `interruption_required`. Проверить, что апстрим считает aux
  на окне `[start - setup, end)` — переезд бригады не должен блокировать актив;
  если блокирует — нужен апстрим-PR. Запреты пар: общий aux на пару; hull цепочки
  остаётся в постпроверке. Остаток ЗИП: расходуемый ресурс в CP-SAT
  (cumulative по времени потребления) или явный предварительный отбор.
- **R-04 (T-05).** Baseline `FIFO-W`: EDD с учётом окон, переездов и смен.
  В отчёте жюри: FIFO, FIFO-W, GREED, CP-SAT на одном JSON; не складывать датасеты.
- **R-11.** Масштаб: генератор 2 000 и 5 000 работ, бюджет времени, пиковая память;
  записать в реестр как новые строки только после воспроизводимого прогона в CI.

### Волна 3 — данные и регламент (параллельно с поиском заказчика)

- **R-12.** Импорт табличной выгрузки (CSV/XLSX) с явным словарём полей
  (`data-contract-v2.md`); исследовать CIM-профиль обмена графиками ремонтов
  (IEC 61968/61970 и национальные стандарты на его основе — номер проверить, не выдумывать).
- **R-13.** Режимы горизонта: годовой черновик, месячный с заморозкой утверждённых
  строк, недельный repair. Привязка к срокам п. 15 и п. 21 ПП № 86 — только для
  объектов диспетчеризации, с оговоркой.
- **R-14.** Выписать требования реестра российского ПО и закупок; в публичные
  материалы — только «не исследовано / требования такие-то», без заявлений о соответствии.

### Волна 4 — исследовательская (после волн 1–2)

- **R-15.** Извлекатель «текст заявки → GridPlan JSON» с LLM, где каждый кандидат
  проходит `check`. Метрика — доля проверенных JSON на размеченном наборе;
  сравнение по протоколу CP-Bench/ConstraintBench, без «победили GPT».
- **R-16.** Сертификат оптимальности CP-SAT (LRAT или повторный независимый
  солвер с тем же bound) для B3.
- **R-09.** Ревью трёх коммитов SynAPS; bump пина отдельным PR с полным прогоном
  и обновлением `versions.py`, `pyproject.toml`, `requirements-lock.txt`, SBOM.
  В апстриме обновить запись «GridPlan 0.1.2» отдельным PR в SynAPS.

### Не делать

- Не добавлять N-1, SAIDI, power-flow, «оптимизацию аварийности».
- Не называть ДЗО, СО ЕЭС, 1С или Энерготехнохаб партнёрами или заказчиками.
- Не обнулять `travel_minutes` ради зелёного native-вердикта.
- Не публиковать цифры проб из этого файла без строки реестра.

## 8. Гейты перед каждым PR

```bash
python -m pip install -e ".[dev]" --force-reinstall --no-deps
python -m ruff check src tests scripts && python -m ruff format --check src tests scripts
python -m mypy src/synaps_gridplan
python -m pytest -q
python scripts/lint_claims.py
python scripts/export_test_count.py && git diff --exit-code -- docs/TEST_COUNT.txt
python scripts/extract_deck_text.py --check
python scripts/export_pydantic_schema.py && python scripts/export_sbom.py
git diff --exit-code -- schemas/gridplan.pydantic.problem.json sbom/
python benchmark/jury_benchmark.py --cpsat
cd native/synaps-gridplan-rs && cargo fmt --check && cargo test --locked && cargo clippy --locked -- -D warnings
```

Новые тесты меняют `docs/TEST_COUNT.txt` — пересоздать снимок в том же PR.
