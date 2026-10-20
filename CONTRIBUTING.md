# Contributing

SynAPS-GridPlan is the public repository of an energy ТОиР scheduling
contour on SynAPS. Its maturity is an ISO 16290 TRL 4 self-assessment on
synthetic fixtures: not GOST R 58048 certification, not 187-FZ / KII
attestation. A plan counts when `outcome.ok` is true, that is an acceptable
status, `verified_feasible`, and zero hard violations together. Quantitative
statements belong in `docs/CLAIMS_REGISTRY.md` (`verified` / `assumption` /
`target` / `withdrawn`). Do not name a partner or customer without a document.

## Setup

Python ≥ 3.12. SynAPS is pinned by full SHA in `pyproject.toml`.
`--force-reinstall` puts the pin over an editable SynAPS checkout;
`tests/test_version_pins.py` fails while another commit is installed.

```bash
python -m pip install -e ".[dev]" --force-reinstall
python -m synaps_gridplan version
```

## Before a pull request

These are the gates in `.github/workflows/ci.yml`:

```bash
python -m ruff check src tests scripts benchmark
python -m ruff format --check src tests scripts
python -m mypy src/synaps_gridplan
python -m pytest -q
python scripts/lint_claims.py
python scripts/scan_secrets.py
python scripts/extract_deck_text.py --check
python scripts/export_test_count.py
python scripts/export_pydantic_schema.py
python scripts/export_sbom.py
```

The last three rewrite `docs/TEST_COUNT.txt`, `schemas/`, and `sbom/`.
Commit what they change. `python -m pytest -q -m "not slow"` skips the
CP-SAT guards for a quick loop; CI runs them. `python scripts/evidence_bundle.py`
writes a one-command lab snapshot.

Benchmark scripts rewrite the committed reports in `benchmark/results/`.
Regenerate the jury report with `python benchmark/jury_benchmark.py --cpsat`:
without the flag section D disappears, and the tests require it. Wall-time
cells change on every run.

Dependabot cargo and Actions bumps do not edit `sbom/`. The `dependabot-sbom`
workflow regenerates that inventory from the base commit's generator and pushes
the result. Any other pull request still fails CI when `sbom/` disagrees with
the lockfiles.

Native contour:

```bash
cd native/synaps-gridplan-rs
cargo fmt --check
cargo test --locked
cargo clippy --locked -- -D warnings
```

## Pull requests

`main` takes changes through pull requests. Checks must be green on a branch
that is up to date with `main`. Commit titles follow Conventional Commits
(`feat`, `fix`, `docs`, `test`, `bench`, `chore`, `refactor`).

Do not float the SynAPS pin on a branch tip. Do not mark GREED/FIFO as
`optimal`. Do not add live grid dumps.

## Living and historical docs

If a slide, the README, or an application disagrees with `docs/LIMITS.md`,
`LIMITS.md` is right. Numbered `docs/[0-9]*` files, `docs/rfc/`, and
`_SUBMIT_MIK_2026_08_18/` are the August 2026 application and red-team
archive: `scripts/lint_claims.py` skips them, and they are not a source of
numbers. Unnumbered files in `docs/` are living. Current claims live in
`README.md`, `AUDIT.md`, `CHANGELOG.md`, `docs/CLAIMS_REGISTRY.md`, and
`src/synaps_gridplan/versions.py`.
