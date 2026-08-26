"""Emergency-day guard: узел «Восточный» must stay GREED-clean,
FIFO-broken, and the pre-agreed frozen ПЛ window must survive replan.

Protects the emergency-restoration demo (synthetic, regulatory chain)
from regressions in adapter/planner semantics: emergency outage windows,
inspection→repair chains, ДГУ jobs without interruption, frozen ПЛ rows.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))

from emergency_day_benchmark import (  # noqa: E402
    DISRUPTED_REFS,
    build_emergency_problem,
    render_md,
    run,
)

from synaps_gridplan.baselines import plan_with_config  # noqa: E402
from synaps_gridplan.planner import replan_after_disruption  # noqa: E402


@pytest.fixture(scope="module")
def problem():
    return build_emergency_problem()


def test_emergency_instance_shape(problem) -> None:
    assert len(problem.assets) == 10
    assert len(problem.jobs) == 23
    assert len(problem.crews) == 8
    assert len(problem.outage_windows) == 5
    assert len(problem.spare_parts) == 4
    assert len(problem.frozen_assignments) == 1
    fr = problem.frozen_assignments[0]
    assert fr.immutable and fr.source == "pl_window"
    assert (fr.end - fr.start) == timedelta(hours=4)
    emergency = [j for j in problem.jobs if j.kind == "emergency"]
    # локализация + 3 ввода 110 кВ + ввод Ф-3 + 3 ремонта 110 кВ + ремонт и
    # расчистка Ф-3 + 2 ДГУ + перевод ТП + ответвление 0,4 кВ = 14
    assert len(emergency) == 14
    assert problem.domain_attributes["data_provenance"] == "synthetic"
    switching = [j for j in problem.jobs if "switch_110" in j.required_qualifications]
    assert len(switching) == 4  # локализация + 3 ввода в работу 110 кВ
    # Прецедентный граф обязан оставаться линеен: адаптер компилирует только
    # цепочки (join/fan-out silently drop edges).
    succ_count: dict[str, int] = {}
    for j in problem.jobs:
        assert len(j.predecessor_job_ids) <= 1
        for p in j.predecessor_job_ids:
            succ_count[str(p)] = succ_count.get(str(p), 0) + 1
    assert all(v == 1 for v in succ_count.values())


def test_emergency_greed_verified_clean(problem) -> None:
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    assert outcome.verified_feasible
    assert outcome.metadata.get("gridplan_violations", []) == []
    assert (outcome.metadata.get("engine_violations") or []) == []
    assert outcome.hard_violation_count == 0
    assert len(outcome.schedule.assignments) == len(problem.jobs)


def test_emergency_frozen_pl_row_pinned(problem) -> None:
    """ТО Т-2 (Городская) — заявка ПЛ 13:00–17:00, согласованная накануне:
    GREED обязан поставить её ровно в замороженный слот и на ОВБ-2."""
    outcome = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    assert outcome.verified_feasible
    fr = problem.frozen_assignments[0]
    op_id = outcome.id_map[f"job:{fr.job_id}"]
    wc_id = outcome.id_map[f"crew:{fr.crew_id}"]
    asn = next(a for a in outcome.schedule.assignments if a.operation_id == op_id)
    assert asn.work_center_id == wc_id
    assert asn.start_time == fr.start and asn.end_time == fr.end


def test_emergency_fifo_breaks_hard_rules(problem) -> None:
    outcome = plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    violations = outcome.metadata.get("gridplan_violations", [])
    engine = outcome.metadata.get("engine_violations") or []
    assert not outcome.verified_feasible
    assert outcome.hard_violation_count >= 4  # аварийные окна FIFO игнорирует
    assert outcome.hard_violation_count == len(violations) + len(engine)


def test_emergency_replan_preserves_frozen_pl(problem) -> None:
    """Уточнение объёма по ВЛ-110: цепочка уходит на repair; замороженная
    ПЛ-0901-14 и остальной день обязаны остаться неподвижными."""
    base = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    ref_to_job = {j.external_ref: j for j in problem.jobs}
    disrupted = [ref_to_job[r] for r in DISRUPTED_REFS]
    assert len(disrupted) == 3
    repaired = replan_after_disruption(
        problem, base_outcome=base, disrupted_job_ids=[j.id for j in disrupted]
    )
    assert repaired.status == "feasible"
    assert repaired.verified_feasible
    assert repaired.metadata.get("gridplan_violations", []) == []
    assert (repaired.metadata.get("engine_violations") or []) == []
    fr = problem.frozen_assignments[0]
    op_id = repaired.id_map[f"job:{fr.job_id}"]
    asn = next(a for a in repaired.schedule.assignments if a.operation_id == op_id)
    assert asn.start_time == fr.start and asn.end_time == fr.end


def test_emergency_determinism(problem) -> None:
    a = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    b = plan_with_config(problem, solver_config="GREED", apply_frozen=True)
    assert [x.model_dump(mode="json") for x in a.schedule.assignments] == [
        x.model_dump(mode="json") for x in b.schedule.assignments
    ]


def test_emergency_report_renders_verified() -> None:
    """A dirty GREED plan must not be labelled verified in the rendered report."""
    results = run()
    md = render_md(results)
    assert results["scenario_a"]["greed"]["verified_feasible"]
    assert "Восточный" in md
    assert "СТО 17330282" in md
    assert "ДГУ-200" in md
    assert "ПЛ-0901-14" in md
    assert "Локализация повреждённого участка" in md
    assert "Мособлэнерго" not in md
    assert "до атаки" not in md
    assert "Реальный день" not in md
    fp = results["scenario_c"]["plan_fingerprint"]
    assert isinstance(fp, str) and len(fp) == 64 and fp[:16] in md


def test_benchmark_console_prints_encode_as_cp1251() -> None:
    """Windows jury demos use cp1251; a single arrow must not abort a green run."""
    import ast

    root = Path(__file__).resolve().parents[1] / "benchmark"
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Name) or func.id != "print":
                continue
            for arg in node.args:
                parts: list[str] = []
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    parts.append(arg.value)
                elif isinstance(arg, ast.JoinedStr):
                    parts.extend(
                        v.value
                        for v in arg.values
                        if isinstance(v, ast.Constant) and isinstance(v.value, str)
                    )
                for part in parts:
                    part.encode("cp1251")
