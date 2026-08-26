"""Guard: declared SynAPS pin must match the installed synaps package metadata.

The Marathon / jury surface claims a specific upstream SHA in
``synaps_gridplan.versions.SYNAPS_COMMIT``. A stale editable install or a
forgotten pin bump must fail CI rather than silently demo the wrong engine.
"""

from __future__ import annotations

import contextlib
import importlib.metadata
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
import synaps

from synaps_gridplan.cli import main
from synaps_gridplan.versions import GRIDPLAN_VERSION, SYNAPS_COMMIT, SYNAPS_REPO

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_VERSIONS = REPO_ROOT / "src" / "synaps_gridplan" / "versions.py"


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


def test_requirements_lock_pins_same_synaps_commit() -> None:
    lock = Path(__file__).resolve().parents[1] / "requirements-lock.txt"
    text = lock.read_text(encoding="utf-8")
    assert f"@{SYNAPS_COMMIT}" in text
    assert "tzdata==" not in text


def _path_from_file_url(url: str) -> Path:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    if path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return Path(path).resolve()


def test_imported_pin_matches_this_checkout() -> None:
    """Catch a leftover ``pip install -e`` from a retired tree."""
    text = REPO_VERSIONS.read_text(encoding="utf-8")
    assert f'SYNAPS_COMMIT = "{SYNAPS_COMMIT}"' in text
    assert f'GRIDPLAN_VERSION = "{GRIDPLAN_VERSION}"' in text


def test_editable_install_is_this_checkout() -> None:
    raw = importlib.metadata.distribution("synaps-gridplan").read_text("direct_url.json")
    if raw is None:
        pytest.skip("synaps-gridplan has no PEP 610 direct_url.json")
    info = json.loads(raw)
    if not (info.get("dir_info") or {}).get("editable"):
        pytest.skip("synaps-gridplan is not an editable install")
    assert _path_from_file_url(info["url"]) == REPO_ROOT.resolve()


def test_cli_version_prints_pin(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    out = capsys.readouterr().out
    assert f"synaps-gridplan {GRIDPLAN_VERSION}" in out
    assert SYNAPS_COMMIT in out
    assert "iso16290_trl 4" in out
    assert "source " in out


def test_installed_synaps_git_commit_matches_pin() -> None:
    raw = importlib.metadata.distribution("synaps").read_text("direct_url.json")
    if raw is None:
        pytest.skip("synaps has no PEP 610 direct_url.json")
    vcs = json.loads(raw).get("vcs_info") or {}
    commit_id = vcs.get("commit_id")
    if not commit_id:
        pytest.skip("synaps is not a git install")
    assert commit_id == SYNAPS_COMMIT


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
