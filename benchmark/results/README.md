# Benchmark results

Synthetic fixtures only. The published demo is `jury_report.md` (version pin
inside the file). JSON dumps are gitignored.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python benchmark/jury_benchmark.py
python -m pytest -q -m "not slow"
```
