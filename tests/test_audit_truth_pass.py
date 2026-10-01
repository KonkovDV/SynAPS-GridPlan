"""October truth pass: benchmark lint is in CI, and AUDIT records the 01.10 check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_ci_ruff_checks_benchmark_sources() -> None:
    ci = (_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "ruff check src tests scripts benchmark" in ci
    assert "ruff format --check src tests scripts\n" in ci


def test_benchmark_sources_pass_ruff() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "benchmark"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_audit_records_the_october_truth_pass() -> None:
    audit = (_ROOT / "AUDIT.md").read_text(encoding="utf-8")
    assert "## 9. Truth pass 01.10.2026" in audit
    assert "6dde1ce" in audit
    assert "58 функций `#[test]`" in audit
    assert "2 октября 2026" in audit
