"""Emit Pydantic JSON Schema for GridPlanProblem.

This is the nested schema generated from the live Pydantic models, including
``additionalProperties: false`` from ``extra=forbid``. It is not a promise of
byte-for-byte JSON round-trip or of Draft 2020-12 validation of arbitrary
future ``gridplan.v2`` documents.
"""

from __future__ import annotations

import json
from pathlib import Path

from synaps_gridplan.model import GridPlanProblem

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "gridplan.pydantic.problem.json"


def main() -> int:
    schema = GridPlanProblem.model_json_schema()
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
