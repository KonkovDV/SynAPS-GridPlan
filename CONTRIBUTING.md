# Contributing

This tree is the public contest packet (ISO 16290 TRL 4 self-assessment on
synthetic fixtures; not GOST R 58048 certification). Claims are narrow: a
plan is `verified_feasible` only when both check layers report zero hard
violations. Quantitative statements belong in `docs/CLAIMS_REGISTRY.md`
(`verified` / `assumption` / `target` / `withdrawn`). Do not name a partner
or customer without a document. 187-FZ / KII compliance is not claimed.

One-command lab snapshot:

```bash
python scripts/evidence_bundle.py
```

## Setup

Python ≥ 3.12. SynAPS is pinned by full SHA in `pyproject.toml`.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python -m pytest -q -m "not slow"
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy src/synaps_gridplan
python scripts/export_pydantic_schema.py
python scripts/export_sbom.py
python scripts/scan_secrets.py
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

`docs/` and `_SUBMIT_MIK_2026_08_18/` are a **historical** application/red-team
archive (August 2026). Current claims live in `README.md`, `AUDIT.md`,
`CHANGELOG.md`, `docs/CLAIMS_REGISTRY.md` and `src/synaps_gridplan/versions.py`.
