"""Labeled JSON must pass the checker before it counts. Prose is not emitted."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from synaps_gridplan.extract import extract_problem, format_measure, measure_emitted
from synaps_gridplan.model import Asset, Crew, GridPlanProblem, MaintenanceJob
from synaps_gridplan.synthetic import synthesize_feeder


def _tiny_payload() -> dict:
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
    return problem.model_dump(mode="json")


def test_prose_and_blank_quantity_are_refused() -> None:
    prose = extract_problem({"text": "почини трансформатор завтра"})
    assert prose.emitted is False
    assert prose.reason == "prose"
    payload = _tiny_payload()
    payload["spare_parts"] = [{"code": "BOLT"}]
    blank = extract_problem(payload)
    assert blank.emitted is False
    assert blank.reason == "blank_quantity"


def test_labeled_sample_counts_only_json_that_passes_check() -> None:
    dirty = synthesize_feeder(mode="small", seed=42).model_dump(mode="json")
    measure, rows = measure_emitted(
        [
            ("tiny", _tiny_payload()),
            ("small-42", dirty),
            ("prose", {"text": "заявка без полей"}),
        ]
    )
    by_id = {row.sample_id: row for row in rows}
    assert by_id["tiny"].emitted is True
    assert by_id["tiny"].checked_ok is True
    assert by_id["small-42"].emitted is True
    assert by_id["small-42"].checked_ok is False
    assert by_id["prose"].emitted is False
    assert measure.n_emitted == 2
    assert measure.n_checked_ok == 1
    text = format_measure(measure)
    assert text == (
        "Доля JSON, прошедших check, на этой размеченной выборке: 1/2. "
        "Это не точность извлечения текста заявки ТОиР."
    )
    assert "100%" not in text
