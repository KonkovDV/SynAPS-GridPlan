# Benchmark results

Synthetic fixtures only. Published markdown:

| File | What it is |
| --- | --- |
| `jury_report.md` | checked campaign-shaped demo, РЭС «Северный» (55 jobs) |
| `emergency_day_report.md` | synthetic restoration day, узел «Восточный» |
| `scale_report.md` | generic 200/600-job feeder: search time, checker still rejects |

Version pins live inside the files. JSON dumps are gitignored.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python benchmark/jury_benchmark.py
python benchmark/emergency_day_benchmark.py
python -m pytest -q -m "not slow"
```
