# Benchmark results

Synthetic fixtures only. The published demos are `jury_report.md` (месячный
ТОиР-план, РЭС «Северный») and `emergency_day_report.md` (аварийный день
18.08.2026, узел «Восточный») — version pins inside the files. JSON dumps are
gitignored.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python benchmark/jury_benchmark.py
python benchmark/emergency_day_benchmark.py
python -m pytest -q -m "not slow"
```
