"""JSON Schema drift: synthesized problems must match committed schemas."""

from __future__ import annotations

import json
from pathlib import Path

from synaps_gridplan.model import SCHEMA_VERSION_V2, GridPlanProblem
from synaps_gridplan.synthetic import synthesize_feeder

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_v1_and_v2_problem_schemas_list_frozen_assignments() -> None:
    v1 = _schema("gridplan-problem.schema.json")
    v2 = _schema("gridplan.v2.problem.schema.json")
    assert "frozen_assignments" in v1["properties"]
    assert "frozen_assignments" in v2["properties"]
    assert "simultaneous_outage_bans" in v1["properties"]
    assert "simultaneous_outage_bans" in v2["properties"]


def test_pydantic_model_exposes_frozen_assignments() -> None:
    props = GridPlanProblem.model_json_schema()["properties"]
    assert "frozen_assignments" in props
    assert "simultaneous_outage_bans" in props


def test_synthesize_small_satisfies_v1_required_keys() -> None:
    problem = synthesize_feeder(mode="small", seed=12)
    data = json.loads(problem.model_dump_json())
    required = _schema("gridplan-problem.schema.json")["required"]
    for key in required:
        assert key in data
    assert "frozen_assignments" in data
    dumped_v2 = json.loads(
        problem.model_copy(update={"schema_version": SCHEMA_VERSION_V2}).model_dump_json()
    )
    for key in _schema("gridplan.v2.problem.schema.json")["required"]:
        assert key in dumped_v2
