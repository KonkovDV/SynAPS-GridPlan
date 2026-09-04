# Contributing

This tree is the public contest packet (ISO 16290 TRL 4). Claims are
narrow: a plan is `verified_feasible` only when both check layers report
zero hard violations.

## Setup

Python ≥ 3.12. SynAPS is pinned by full SHA in `pyproject.toml`.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python -m pytest -q -m "not slow"
python -m ruff check src tests
python -m ruff format --check src tests
```

Native contour:

```bash
cd native/synaps-gridplan-rs
cargo fmt --check
cargo test --locked
cargo clippy --locked -- -D warnings
```

Do not float the SynAPS pin on a branch tip. Do not mark GREED/FIFO as
`optimal`. Do not add live grid dumps.
