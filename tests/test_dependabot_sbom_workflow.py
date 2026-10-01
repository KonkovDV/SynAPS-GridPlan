"""Dependabot lockfile bumps must refresh the SBOM without widening CI write access."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"


def _text(name: str) -> str:
    return (_WORKFLOWS / name).read_text(encoding="utf-8")


def test_only_the_dependabot_job_may_write_repository_contents() -> None:
    writers = sorted(
        path.name
        for path in _WORKFLOWS.glob("*.yml")
        if "contents: write" in path.read_text(encoding="utf-8")
    )
    assert writers == ["dependabot-sbom.yml"]
    job = _text("dependabot-sbom.yml")
    assert "pull_request_target" in job
    assert "github.actor == 'dependabot[bot]'" in job
    assert "github.event.pull_request.head.repo.full_name == github.repository" in job
    assert "github.event.pull_request.base.sha" in job
    assert "export_sbom.py" in job
    assert "pip install -e" not in job
    assert "contents: write" in job
    assert "actions: write" in job
    assert "permissions: {}" in job
    ci = _text("ci.yml")
    assert "workflow_dispatch" in ci
    assert "git diff --exit-code -- schemas/gridplan.pydantic.problem.json sbom/" in ci
    assert "contents: write" not in ci
