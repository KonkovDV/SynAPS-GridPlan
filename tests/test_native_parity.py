"""Python CLI JSON → native ``check``: domain kinds match; coverage is explicit."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )
    assert proc.returncode in {0, 2}, proc.stderr
    text = (proc.stdout or "").strip()
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
    problem = json.loads(feeder.read_text(encoding="utf-8"))
    requires_travel = bool(problem["jobs"] and problem["travel_minutes"])
    assert payload["verification_scope"] == "gridplan_domain"
    assert payload["engine_checked"] is False
    assert payload["unsupported_constraints"] == (["travel_minutes"] if requires_travel else [])
    assert payload["hard_violation_count"] == len(rust_kinds)
    assert payload["domain_verified_feasible"] is (len(rust_kinds) == 0)
    assert payload["verified_feasible"] is (len(rust_kinds) == 0 and not requires_travel)


@pytest.mark.skipif(CARGO is None, reason="cargo not on PATH")
@pytest.mark.parametrize("solver", ["FIFO", "GREED"])
def test_native_check_res_severny_domain_matches_python(tmp_path: Path, solver: str) -> None:
    """Rust `check` on synthetic res_severny: domain kinds match Python.

    Engine-layer kinds stay in Python. Nonempty ``travel_minutes`` keeps
    native ``verified_feasible`` false even when the domain layer is clean.
    """
    sys.path.insert(0, str(ROOT / "benchmark"))
    from res_severny_benchmark import build_res_problem  # noqa: E402

    problem = build_res_problem()
    assert problem.jobs
    assert problem.travel_minutes
    feeder = tmp_path / "problem.json"
    result = tmp_path / "result.json"
    feeder.write_text(problem.model_dump_json(indent=2), encoding="utf-8")
    code = main(["solve", str(feeder), "--solver", solver, "-o", str(result)])
    assert code in {0, 2}
    raw = json.loads(result.read_text(encoding="utf-8"))
    py_domain = [row["kind"] for row in raw["outcome"]["metadata"].get("gridplan_violations") or []]
    py_engine = [row["kind"] for row in raw["outcome"]["metadata"].get("engine_violations") or []]
    payload = _native_check(feeder, result)
    rust_kinds = [canonicalize_rust_kind(row["kind"]) for row in payload.get("violations") or []]
    assert kind_multiset(rust_kinds) == kind_multiset(py_domain)
    assert payload["verification_scope"] == "gridplan_domain"
    assert payload["engine_checked"] is False
    assert payload["unsupported_constraints"] == ["travel_minutes"]
    assert payload["hard_violation_count"] == len(rust_kinds)
    domain_clean = len(rust_kinds) == 0
    assert payload["domain_verified_feasible"] is domain_clean
    assert payload["verified_feasible"] is False
    if solver == "GREED":
        assert domain_clean
        assert not py_engine
        assert raw["outcome"]["verified_feasible"] is True
    else:
        assert not domain_clean
        assert py_engine
        assert raw["outcome"]["hard_violation_count"] == len(py_domain) + len(py_engine)
