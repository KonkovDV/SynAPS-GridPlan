# 24 — Мастер-план работы для ИИ-программиста (2026-08-14)

> **АРХИВ. К анкете МИК не прилагать.** Кухня разработки 11–14.08 (волны, G1–G11,
> пути `C:\plans\*`, «Исполнитель — ИИ-программист»). Пины `02dacda` / `2e3af19`
> закрыты публичным **0.1.1** / `bd09d13`. Канон заявки: `docs/00`–`09`, `22`.

> Составлен по полному чату 11–14 августа 2026 (SynAPS, SynAPS-GridPlan, SynAPS-MobiRoute).
> Это план, а не код. Исполнитель — ИИ-программист в следующих сессиях.
> Каждая волна заканчивается: focused pytest → архитектурный ratchet → Red Team-дельта → CHANGELOG → коммит только по явной команде.

## 0. Жёсткие правила (действуют на все волны)

1. **Контракт FEASIBLE**: `status == FEASIBLE` ⇒ все операции расставлены, `proven_hard_violations(FeasibilityChecker.check(..., exhaustive=True)) == ∅`, `stabilize_temporal_consistency.converged == 1`, ничего за `planning_horizon_end`. `LANE_INFERENCE_UNPROVEN` — жёсткое нарушение.
2. **Зерно времени**: `max(1, ceil(base/speed))`. Без AVX-512 (i5-13600KF, только AVX2/FMA3 + PREFETCHT0 dist 8). Без rayon в главном цикле cover.
3. **Запрещённые заявления**: INFIMUM 39k/40 мин, +78M ₽, 27 дней, Zhu −9.8%, Prysmian −25%, 499770/145 с как кабельное доказательство, N-1, SAIDI, SOTA, «заменили INFIMUM», «repair на порядок быстрее», «Hamming 0 доказывает заморозку».
4. **Не смешивать миры**: 499770 оп / ~145 с = синтетический GREEDY_COVER; 39k/40 мин = маркетинг вендора; −9.8% makespan = Zhu et al. Processes 14(5):769.
5. **Ратчет длины функций** (`tests/test_architecture.py`): новые функции ≤ 80 строк; `cli.py::main` ≤ 130+10; `incremental_repair._solve_core` ≤ 253+10. Публичные функции в `synaps/` обязаны иметь production-вызывателя (тесты не считаются).
6. **Permanent deferrals, не переоткрывать без нового RFC + Red Team**: native ABI для `p_{o,m}` (skip-to-Python — контракт), dmorill FJSSP-SDST (GPL-3, запрет), KI-S3 sentinel (BHK-разрезы не монотонны), CP-SAT energy term (закрыт в Wave 10, вес 0 по умолчанию).
7. `benchmark/results/` и `benchmark/studies/` в .gitignore — измеренные числа писать в RFC/CHANGELOG, не в игнорируемые JSON.
8. Железное правило ML: нейросети только советуют (L-RHO/Graph-RHO — advisory), никогда не движок завода. Без GPU-GA, без DRL-политики.

## Текущее состояние (проверено 2026-08-14)

| Репо | HEAD | Состояние |
|------|------|-----------|
| `C:\plans\SynAPS` | `4708443` | 500k GREEDY_COVER (499770 оп / ~145 с / 2.3 GB), кабельный домен C0–C4, нервный месяц 20316 оп FEASIBLE на 16 станках/передел |
| `C:\plans\SynAPS-GridPlan` | `02dacda` | Пин SynAPS `2e3af19` (отстал на 2 коммита), untracked `benchmark/results/rosseti_res_run_2026_08_12.log`, дедлайн заявки Марафона **20 августа** |
| `C:\plans\SynAPS-MobiRoute` | `0114e4e` | stress_200 pipeline ~8.1 с (было 95 с), rolling-horizon day-ahead добавлен |

---

## Приоритет 0 — GridPlan: дедлайн Марафона 20.08 (самое срочное)

### G1. Поднять пин SynAPS `2e3af19` → `4708443`
- Файл: `pyproject.toml:36` (`synaps @ git+...@2e3af198...`).
- После поднятия: `pip install -e .`, полный `pytest` GridPlan, прогон `benchmark/jury_benchmark.py` и `benchmark/rosseti_res_benchmark.py`, сверить, что fail-closed нотариус (G11, travel, shift_calendar) остался зелёным на новом upstream.
- Риск: в upstream появились `RHC-GREEDY-COVER` авто-роутинг ≥10k и кабельный домен — проверить, что роутинг GridPlan-инстансов не сменился молча.
- Приёмка: все тесты GridPlan зелёные, jury/rosseti отчёты перегенерированы, числа в `docs/04_EVIDENCE_PACK.md` совпадают с свежими прогонами.

### G2. Гигиена репо
- `benchmark/results/rosseti_res_run_2026_08_12.log` — либо закоммитить (если evidence для жюри), либо удалить/игнорировать. Не оставлять untracked.

### G3. Остатки из чата (сообщение «Оставлено честно»)
- `shift_calendar` / `safety_constraints` / `service_area` — сейчас только в нотариусе; решить: задействовать в солверах или явно задокументировать «notary-only» в `docs/limitations.md`.
- G11 last-window-wins — проверить на новом upstream (в SynAPS закрыто через `immutable_op_ids`, A15-P1-6).
- A15-P0-2/3 (ALNS frozen precedence / setup vs frozen) — в SynAPS закрыты (WAVE15_REDTEAM_DELTA); в GridPlan проверить регрессионными тестами на новом пине.

### G4. Обновить evidence pack для жюри
- `docs/04_EVIDENCE_PACK.md`: добавить свежие числа upstream (50k FEASIBLE за ~6.7 с, 500k cover, кабельный месяц 20316 оп / 9.36 с) — строго с оговорками «синтетика, не Россети».
- Проверить `docs/02_APPLICATION_DRAFT.md` и `docs/22_PILOT_DATA_REQUEST_ROSSETI.md` на актуальность перед подачей.

---

## Приоритет 1 — SynAPS: ускорение кабельного месяца (A1–A6)

Источник: `docs/rfc/CABLE_NERVOUS_MONTH_ACCEL_2026_08.md`. Измеренные узкие места: 1600@8 → coverage 0.50 (error), 800@8 → 0.92 (error); 1600@16 → FEASIBLE 9.36 с, но 2.75e6 мин переналадок (~⅔ календаря); Python GREED ATCS повис >120 с уже на 400 заказах/8 станках.

### S1 (A1). ATCS-ключ готовности в native COVER — главная волна
- Цель: **1600@8 FEASIBLE** (сейчас overflow). Нативная куча `ReadyKey(floor, seq, uuid_rank)` не смотрит на переналадку.
- Файлы: `native/synaps_native/src/list_schedule.rs` (ReadyKey, `place_append_only`, `place_with_aux_delay`), `synaps/solvers/rhc/_cover.py` (Python-паритет), `synaps/solvers/greedy_dispatch.py` (существующий ATCS: `compute_atcs_log_scores_batch`, `local_setup_scale_by_wc`, гард `is_setup_matrix_metric`), `synaps/accelerators.py` (`list_schedule_cover_native` ABI).
- Делать: флаг `cover_ready_rule=("fifo"|"atcs")`, ATCS log-score среди ready-операций (существующая формула GREED), затем earliest-end машина. Сохранить детерминизм (tie-break по uuid_rank). Метричность SDST-матрицы — гардом, как в GREED.
- Приёмка: 1600@8 FEASIBLE с пустым нотариусом и converged=1; setup-минуты на 1600@16 заметно ниже 2.75e6; регрессии 50k/100k/500k cover отсутствуют (пересчитать); Python-путь и native дают одинаковый статус на малых фикстурах; ratchet зелёный.
- Red Team обязателен до мержа: атаковать tie-break, неметричную SDST, aux-задержку, latest_finish cap.

### S2 (A2). Выделенные линии по семействам (encode-first, без ядра)
- Файл: `synaps/domains/cable/instance.py` — `eligible_wc_ids` ограничить по семейству (PVC-линии ≠ XLPE-линии) в `generate_cable_instance`/`generate_nervous_month` (параметр, по умолчанию выкл.).
- Приёмка: на 1600@8 с S1 — падение cross-family 400-минутных переналадок; честная таблица «с/без» в RFC.

### S3 (A3). Инкрементальный календарь в IncrementalRepair
- Сейчас ремонт окрестности 20–28 оп сканирует ~20k frozen-назначений: 5.1–6.0 с против 9.25 с полного cover (всего 1.77×).
- Файлы: `synaps/solvers/incremental_repair.py` (`_solve_core`), `synaps/solvers/_dispatch_support.py` (`MachineIndex`).
- Делать: строить `MachineIndex`/aux-окна только по затронутым машинам и временному окну окрестности; frozen вне окна — как compact blocking-интервалы.
- Приёмка: repair < 1 с на 20k при том же результате нотариуса; Hamming не растёт; волна 0 нервного месяца ≥ 5× против full re-cover.

### S4 (A4). Дельта-нотариус
- Сейчас IncrementalRepair честно гоняет exhaustive-нотариус по всем 20k — это доминирует wall time ремонта.
- Делать: дельта-проверка окрестности ∪ затронутых машин + флаг `full_notary=True` по умолчанию для cover-заявлений. Пропуск frozen-операции — P0, поэтому сначала Red Team-доказательство, что дельта не слепая к frozen.
- Приёмка: дельта и полный нотариус дают одинаковый вердикт на всём наборе волн; cover-путь всегда полный.

### S5 (A5). Кампания по цвету / заморозка как L-RHO-аналог
- Цветной календарь (per-family фаза слотов) в `synaps/domains/cable/campaign.py` ИЛИ задокументировать заморозку как policy-аналог variable-fixing (L-RHO arXiv:2502.15791, Graph-RHO arXiv:2604.10073). GNN — только advisory-sidecar, не в этой волне.

### S6 (A6 = C5a). Hold-until-successor для барабанов — строго gated
- Открывать только после чисел S1+S2 и отдельного RFC + Red Team. `peak_wip_drums=265` против пула 96 — разрыв качества, не скорости. Не открывать C5a «для ускорения месяца».

---

## Приоритет 2 — Кабельные остатки Red Team (N-R*, C-R*)

Источники: `docs/rfc/CABLE_NERVOUS_MONTH_REDTEAM_2026_08_14.md`, `docs/rfc/CABLE_DOMAIN_REDTEAM_2026_08_14.md`.

| ID | Задача | Приёмка |
|----|--------|---------|
| N-R3/N-R4 | Честный бенчмарк «срочная вставка»: добавлять **новые** родительские заказы mid-month (не перестановку существующих), сравнить repair vs full re-solve на мутированном инстансе; Hamming R=0 волны 1 объяснить в RFC как no-move | RFC с таблицей; без заявления «на порядок быстрее» |
| N-R6 | Мультисид: seeds 1..5 для нервного месяца, mean/min/max по solve_s, coverage, Dmax | Таблица в ACCEL RFC; без доверительных интервалов |
| N-R8 | `temporal_stabilization_converged` — RHC-only метадата; на GREED-пути либо выставлять честно, либо писать «n/a (GREED)» | Тест на tiny CLI-прогоне |
| C-R1 | `CABLE_PVC_WEIGHTS` в поиск: прокинуть `objective_weights` в CP-SAT/ALNS на кабельном профиле (не трогать GREEDY-дефолт) | Тест: CP-SAT с весами снижает material_loss против makespan-only на малой фикстуре |
| C-R3 | Заморозка на первом решении: опциональный policy-флаг в `solve_schedule` (сейчас freeze только в repair) | Тест: rush не ворует слот выданного плана на first solve |
| C-R5 | SMED-калибровка: документ, что 240/360/400 мин — параметрические, порядок MAPRE, не заводской секундомер | Раздел в `docs/domains/cable.md` |
| C-R7 | `allow_freeze_break` — булево, не ACL: задокументировать | Строка в limitations |
| C-R8 | Blocking/no-wait/AMR/RFID — вне ядра, ссылка на PyJobShop | Уже задокументировано; не закрывать кодом |

---

## Приоритет 3 — Ядро SynAPS: старые остатки

### K1. Полный прогон pytest до конца
- В чате полный прогон вис ~15 мин на ~37% (W16-C11: `while True` в `_reanchor_against_frozen` — исправлено bounded-циклом). Доказательства полного зелёного прогона после фикса нет.
- Делать: `pytest -x --timeout=300` (или per-test timeout), довести до 100%, имена упавших — в Red Team-дельту. Никаких «точечных наборов» как замены полного прогона в финале волны.

### K2. KI-F16 / verification-остатки из чата
- ALNS native ranking на `base/speed` до snap — проверить текущее состояние, закрыть или задокументировать.
- Полный SDST pack в native — оценить трудозатраты; не путать с permanent deferral `p_{o,m}` ABI.
- MAB destroy-only arms — сверить с `docs/rfc/DESIGN_ALNS_MAB_OPERATOR_SELECTION.md`; если дизайн подтверждён — закрыть ссылкой, нет — задача.

### K3. A15-P2 wall-clock детерминизм
- Уже закрыто штампами `wall_clock_path_dependent` / `determinism_violated`. Решить: нужен ли strict-режим (ошибка вместо штампа) для CI-гейтов.

### Не переоткрывать (permanent)
- Native ABI `p_{o,m}`, dmorill GPL-3, KI-S3 sentinel, CP-SAT energy term. См. `docs/rfc/WAVE10_DEFERRED_DECISIONS.md`, `KNOWN_ISSUES.md`.

---

## Приоритет 4 — MobiRoute (отдельный репо, после P0–P1)

Источник: `docs/redteam-algebra-2026-08-12.md` (residuals), `docs/native-acceleration.md`.

| ID | Задача | Детали |
|----|--------|--------|
| M1 | stress_200: 8.1 с → 2–3 с | День-ahead ~4 с — sequential lex inserts (3000×200); traffic +8 держит короткий feasible-хвост; leftovers уходят в re-greedy. Профилировать хвост, не трогать lockstep native/Python |
| M2 | LBBD / RHC — `NotImplementedError` | Решить: реализовать или явно «out of scope» в limitations |
| M3 | Третья остановка, квоты часов, живой граф, ALNS | RT-20 residual; `ops_via`/`ops_quota` существуют; ALNS никогда не OPTIMAL |
| M4 | Native rebuild после смены ABI; CI-линия native | Сейчас CI по умолчанию на Python SoA; добавить native lane |
| M5 | GPU — закрыт вопрос | 13×13 зон, hot path sequential/branchy; зафиксировать отказ в docs |

---

## Порядок исполнения и зависимости

```
G1–G4 (дедлайн 20.08)  →  S1 (ATCS в COVER)  →  S2 (линии)  →  S3+S4 (repair/нотариус)
                              ↓                        ↓
                        N-R6 (мультисид) ←── S5, затем gate → S6 (C5a, только по числам)
K1 (полный pytest) — параллельно с G1, обязателен до любого «всё зелёно».
K2, K3, C-R*, N-R* — после S1. M1–M5 — последними.
```

## Definition of Done на каждую волну

1. Числа из реальных прогонов на этой машине, seed указан, миры не смешаны.
2. FEASIBLE только с пустым exhaustive-нотариусом и converged=1.
3. `pytest tests/test_architecture.py` зелёный (ratchet, dead-public).
4. Red Team-дельта в `docs/rfc/` со списком «что не закрыто».
5. CHANGELOG. Коммит и пуш — только по явной команде пользователя.
