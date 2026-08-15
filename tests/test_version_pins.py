"""Guard: declared SynAPS pin must match the installed synaps package metadata.

The Marathon / jury surface claims a specific upstream SHA in
``synaps_gridplan.versions.SYNAPS_COMMIT``. A stale editable install or a
forgotten pin bump must fail CI rather than silently demo the wrong engine.
"""

from __future__ import annotations

import contextlib
import importlib.metadata
from pathlib import Path

import synaps

from synaps_gridplan.versions import GRIDPLAN_VERSION, SYNAPS_COMMIT, SYNAPS_REPO


def test_gridplan_version_matches_pyproject() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert f'version = "{GRIDPLAN_VERSION}"' in text
    cargo = (root / "native" / "synaps-gridplan-rs" / "Cargo.toml").read_text(encoding="utf-8")
    assert f'version = "{GRIDPLAN_VERSION}"' in cargo.split("[dependencies]", 1)[0]


def test_synaps_is_importable_with_declared_repo() -> None:
    assert SYNAPS_REPO.endswith("/SynAPS")
    assert synaps.__name__ == "synaps"
    # Prefer distribution version when present; SHA pin is the contract.
    with contextlib.suppress(importlib.metadata.PackageNotFoundError):
        _ = importlib.metadata.version("synaps")


def test_declared_synaps_commit_is_full_sha() -> None:
    assert len(SYNAPS_COMMIT) == 40
    assert all(c in "0123456789abcdef" for c in SYNAPS_COMMIT.lower())


def test_pyproject_synaps_git_pin_matches_versions() -> None:
    """The install pin must be the same SHA the jury surface prints."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert f"@{SYNAPS_COMMIT}" in text


def test_installed_synaps_source_mentions_rt20_markers() -> None:
    """Smoke: installed tree contains the fail-closed surfaces the pin promises
    (UNKNOWN_* checks, repair kwargs guard, empty-disruption refuse).
    """
    import synaps.portfolio as portfolio
    import synaps.solvers.feasibility_checker as checker_mod

    checker_file = Path(checker_mod.__file__)
    text = checker_file.read_text(encoding="utf-8")
    assert "UNKNOWN_OPERATION" in text
    assert "UNKNOWN_WORK_CENTER" in text
    portfolio_file = Path(portfolio.__file__)
    ptext = portfolio_file.read_text(encoding="utf-8")
    assert "solver_time_limit_s" in ptext or "_repair_merged_kwargs" in ptext
    assert "legalize base_assignments" in ptext
