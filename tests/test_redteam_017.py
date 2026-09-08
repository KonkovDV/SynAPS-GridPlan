"""Red Team 0.1.7: complete the 0.1.6 laboratory closures without widening claims."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from synaps_gridplan.baselines import plan_fifo
from synaps_gridplan.model import (
    Asset,
    Crew,
    FailureMode,
    FrozenAssignment,
    GridPlanProblem,
    MaintenanceJob,
    OutageWindow,
    RiskProfile,
    SimultaneousOutageBan,
    SparePart,
)
from synaps_gridplan.report import render_report
from synaps_gridplan.sanitize import display_text
from synaps_gridplan.synthetic import synthesize_feeder

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "schemas" / "gridplan.pydantic.problem.json").read_text(encoding="utf-8")
)


def _load_scan_secrets():
    spec = spec_from_file_location("gridplan_scan_secrets", ROOT / "scripts" / "scan_secrets.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_small_synthetic_does_not_mark_windows_frozen() -> None:
    problem = synthesize_feeder(mode="small", seed=12)
    assert problem.outage_windows
    assert all(not window.frozen for window in problem.outage_windows)


def test_display_text_flattens_newlines_html_and_backticks() -> None:
    assert display_text("line1\nline2") == "line1 line2"
    assert display_text("a`b") == "a'b"
    assert display_text("<script>x</script>") == "&lt;script&gt;x&lt;/script&gt;"
    assert "\n" not in display_text("cr\rlf\n")


def test_markdown_report_neutralizes_html_in_interpolated_fields() -> None:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    asset = Asset(code="A", location_code="L")
    crew = Crew(code="C", home_location_code="L")
    problem = GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[MaintenanceJob(external_ref="J", asset_id=asset.id, duration_min=60)],
        planning_horizon_start=start,
        planning_horizon_end=start + timedelta(days=1),
    )
    outcome = plan_fifo(problem)
    meta = dict(outcome.metadata)
    meta["gridplan_violations"] = [{"kind": "PROBE", "message": "see <img src=x> and `code`\nnext"}]
    text = render_report(replace(outcome, metadata=meta), fmt="markdown")
    assert "<img src=x>" not in text
    assert "&lt;img src=x&gt;" in text
    assert "`code`" not in text
    assert "\nnext" not in text.split("see ", 1)[-1]


@pytest.mark.parametrize(
    "patch",
    [
        {"unexpected": True},
        {"assets": [{"code": "A", "unexpected": True}]},
        {"crews": [{"code": "C", "unexpected": True}]},
        {
            "jobs": [
                {
                    "external_ref": "J",
                    "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "duration_min": 60,
                    "unexpected": True,
                }
            ]
        },
    ],
)
def test_unknown_nested_fields_are_rejected(patch: dict[str, Any]) -> None:
    start = "2026-09-01T06:00:00Z"
    payload: dict[str, Any] = {
        "assets": [{"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "code": "A"}],
        "crews": [{"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "code": "C"}],
        "jobs": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "external_ref": "J",
                "asset_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "duration_min": 60,
            }
        ],
        "planning_horizon_start": start,
        "planning_horizon_end": "2026-09-02T06:00:00Z",
    }
    payload.update(patch)
    with pytest.raises(ValueError, match="extra"):
        GridPlanProblem.model_validate(payload)


def test_unknown_fields_on_catalog_models_are_rejected() -> None:
    start = datetime(2026, 9, 1, 6, tzinfo=UTC)
    asset = Asset(code="A")
    with pytest.raises(ValueError, match="extra"):
        RiskProfile.model_validate({"unexpected": True})
    with pytest.raises(ValueError, match="extra"):
        FailureMode.model_validate({"code": "FM", "unexpected": True})
    with pytest.raises(ValueError, match="extra"):
        SparePart.model_validate({"code": "S", "unexpected": True})
    with pytest.raises(ValueError, match="extra"):
        OutageWindow.model_validate(
            {
                "asset_id": asset.id,
                "start": start,
                "end": start + timedelta(hours=1),
                "unexpected": True,
            }
        )
    with pytest.raises(ValueError, match="extra"):
        FrozenAssignment.model_validate(
            {
                "job_id": "11111111-1111-1111-1111-111111111111",
                "crew_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "start": start,
                "end": start + timedelta(hours=1),
                "unexpected": True,
            }
        )
    with pytest.raises(ValueError, match="extra"):
        SimultaneousOutageBan.model_validate(
            {
                "asset_id_a": asset.id,
                "asset_id_b": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "unexpected": True,
            }
        )


def test_pydantic_inventory_lists_nested_models_with_additional_properties_false() -> None:
    defs = SCHEMA["$defs"]
    for name in (
        "Asset",
        "Crew",
        "CrewCalendarWindow",
        "FailureMode",
        "FrozenAssignment",
        "MaintenanceJob",
        "OutageWindow",
        "RiskProfile",
        "SimultaneousOutageBan",
        "SparePart",
    ):
        assert name in defs, name
        assert defs[name].get("additionalProperties") is False, name


def test_synthesized_problems_validate_against_committed_pydantic_schema() -> None:
    validator = jsonschema.Draft202012Validator(
        SCHEMA, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    for mode, seed in (("small", 12), ("small", 42), ("frozen-conflict", 9)):
        data = json.loads(synthesize_feeder(mode=mode, seed=seed).model_dump_json())
        validator.validate(data)


def test_secret_scan_matches_constructed_shapes_not_repo_files() -> None:
    scan = _load_scan_secrets()
    aws = "AKIA" + ("A" * 16)
    github = "ghp_" + ("x" * 36)
    slack = "xoxb-" + ("0" * 12)
    stripe = "sk_live_" + ("a" * 24)
    google = "AIza" + ("a" * 35)
    pem = "BEGIN " + "OPENSSH PRIVATE KEY"
    assert scan.find_hits(aws) == ["aws-access-key-id"]
    assert "github-pat" in scan.find_hits(github)
    assert scan.find_hits(slack) == ["slack-token"]
    assert scan.find_hits(stripe) == ["stripe-live-secret"]
    assert scan.find_hits(google) == ["google-api-key"]
    assert "private-key" in scan.find_hits(pem)
    assert scan.find_hits("ordinary lab fixture text") == []
