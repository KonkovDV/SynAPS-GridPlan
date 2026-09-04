"""Python CLI JSON → native ``check``: GridPlan-layer kind multisets match."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from synaps_gridplan.cli import main
from synaps_gridplan.kind_map import canonicalize_rust_kind, kind_multiset

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "native" / "synaps-gridplan-rs" / "Cargo.toml"
CARGO = shutil.which("cargo")


def test_rust_kind_aliases_are_documented() -> None:
    from synaps_gridplan.kind_map import RUST_TO_PYTHON_KIND

    assert RUST_TO_PYTHON_KIND["UNKNOWN_JOB"] == "UNKNOWN_OPERATION"
    assert RUST_TO_PYTHON_KIND["DUPLICATE_JOB_ASSIGNMENT"] == "DUPLICATE_ASSIGNMENT"
    assert canonicalize_rust_kind("ASSET_OVERLAP") == "ASSET_OVERLAP"


def _native_check(problem: Path, plan: Path) -> dict:
    assert CARGO is not None
    env = os.environ.copy()
    env["CARGO_TERM_COLOR"] = "never"
    proc = subprocess.run(
        [
            CARGO,
            "run",
            "--quiet",
            "--locked",
            "--manifest-path",
            str(MANIFEST),
            "--",
            "check",
            str(problem),
            str(plan),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
    )
    assert proc.returncode in {0, 2}, proc.stderr
    text = proc.stdout.strip()
    brace = text.find("{")
    assert brace >= 0, proc.stdout + proc.stderr
    return json.loads(text[brace:])


@pytest.mark.skipif(CARGO is None, reason="cargo not on PATH")
@pytest.mark.parametrize(("seed", "solver"), [(26, "FIFO"), (42, "GREED"), (12, "GREED")])
def test_native_check_kind_multiset_matches_python(tmp_path: Path, seed: int, solver: str) -> None:
    feeder = tmp_path / "problem.json"
    result = tmp_path / "result.json"
    assert main(["synthesize", "--mode", "small", "--seed", str(seed), "-o", str(feeder)]) == 0
    code = main(["solve", str(feeder), "--solver", solver, "-o", str(result)])
    assert code in {0, 2}
    raw = json.loads(result.read_text(encoding="utf-8"))
    py_kinds = [row["kind"] for row in raw["outcome"]["metadata"].get("gridplan_violations") or []]
    payload = _native_check(feeder, result)
    rust_kinds = [canonicalize_rust_kind(row["kind"]) for row in payload.get("violations") or []]
    assert kind_multiset(rust_kinds) == kind_multiset(py_kinds)
    assert payload["verified_feasible"] is (len(rust_kinds) == 0)
