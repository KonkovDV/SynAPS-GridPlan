"""Fail-closed JSON intake. Prose is refused; a plan counts only after check.

This module does not call a language model. ``format_measure`` reports the
labeled sample only.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from synaps_gridplan.model import GridPlanProblem
from synaps_gridplan.planner import plan_maintenance

_PROSE_KEYS = frozenset({"text", "prompt", "narrative", "request"})


@dataclass(frozen=True)
class ExtractionResult:
    """A problem JSON, or a refusal that must not be solved."""

    emitted: bool
    reason: str | None = None
    problem: GridPlanProblem | None = None


@dataclass(frozen=True)
class SampleRow:
    sample_id: str
    emitted: bool
    checked_ok: bool


@dataclass(frozen=True)
class ExtractionMeasure:
    n_emitted: int
    n_checked_ok: int


def extract_problem(payload: str | Mapping[str, Any]) -> ExtractionResult:
    """Parse a problem document. Free text and a blank spare quantity are refusals."""

    if isinstance(payload, str):
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            return ExtractionResult(emitted=False, reason="invalid_json")
    elif isinstance(payload, Mapping):
        loaded = dict(payload)
    else:
        return ExtractionResult(emitted=False, reason="not_an_object")
    if not isinstance(loaded, dict):
        return ExtractionResult(emitted=False, reason="not_an_object")
    if any(key in loaded for key in _PROSE_KEYS):
        return ExtractionResult(emitted=False, reason="prose")
    if "problem" in loaded:
        if set(loaded) != {"problem"} or not isinstance(loaded["problem"], dict):
            return ExtractionResult(emitted=False, reason="envelope")
        body = loaded["problem"]
    else:
        body = loaded
    spares = body.get("spare_parts")
    if isinstance(spares, list):
        for spare in spares:
            if (
                isinstance(spare, dict)
                and "available_quantity" not in spare
                and "stock_qty" not in spare
            ):
                return ExtractionResult(emitted=False, reason="blank_quantity")
    try:
        problem = GridPlanProblem.model_validate(body)
    except ValidationError:
        return ExtractionResult(emitted=False, reason="invalid_problem")
    return ExtractionResult(emitted=True, problem=problem)


def measure_emitted(
    items: list[tuple[str, str | Mapping[str, Any]]],
    *,
    solver_config: str = "GREED",
) -> tuple[ExtractionMeasure, list[SampleRow]]:
    """Solve only emitted JSON. ``checked_ok`` follows ``PlanOutcome.ok``."""

    rows: list[SampleRow] = []
    for sample_id, payload in items:
        extracted = extract_problem(payload)
        checked_ok = False
        if extracted.emitted and extracted.problem is not None:
            checked_ok = plan_maintenance(
                extracted.problem,
                solver_config=solver_config,
            ).ok
        rows.append(
            SampleRow(
                sample_id=sample_id,
                emitted=extracted.emitted,
                checked_ok=checked_ok,
            )
        )
    emitted = sum(row.emitted for row in rows)
    checked = sum(row.checked_ok for row in rows)
    return ExtractionMeasure(n_emitted=emitted, n_checked_ok=checked), rows


def format_measure(measure: ExtractionMeasure) -> str:
    """State the labeled-sample fraction without turning it into an accuracy claim."""

    fraction = "0/0" if measure.n_emitted == 0 else f"{measure.n_checked_ok}/{measure.n_emitted}"
    return (
        "Доля JSON, прошедших check, на этой размеченной выборке: "
        f"{fraction}. Это не точность извлечения текста заявки ТОиР."
    )
