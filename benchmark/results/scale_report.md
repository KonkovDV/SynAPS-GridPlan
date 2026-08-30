# Масштаб генератора (синтетический фидер)

Не именованный РЭС. Режимы `medium` (200) и `stress` (600) собраны как кампания:
одна линейная цепочка на актив, одно отключение в выделенном окне, склад не меньше
спроса, бригада закреплена. GREED проходит независимую проверку. Календарный FIFO
окна не соблюдает.

Именованный макет района — `jury_report.md` (55 работ, РЭС «Северный»).
Fail-closed демо на маленьком фидере — `small --seed 42` (ASSET_OVERLAP).

Версия GridPlan 0.1.2, SynAPS `6178c93b705f`.
Время стены — локальный прогон, не SLA.

| Режим | Работ | GREED назн. | GREED наруш. | GREED | GREED, с | FIFO наруш. |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| `medium` seed=12 | 200 | 200 | **0** | да | 0.295 | **40** |
| `stress` seed=12 | 600 | 600 | **0** | да | 2.92 | **80** |

Прогоны 50k/500k в README движка SynAPS — другой домен (не постановка ТОиР).
`feasibility_rate` оттуда на GridPlan не переносится.

```bash
python -m synaps_gridplan synthesize --mode medium --seed 12 -o medium.json
python -m synaps_gridplan solve medium.json --solver GREED -o medium-plan.json
# exit 0 — проверка пройдена
python -m synaps_gridplan synthesize --mode stress --seed 12 -o stress.json
python -m synaps_gridplan solve stress.json --solver GREED -o stress-plan.json
```
