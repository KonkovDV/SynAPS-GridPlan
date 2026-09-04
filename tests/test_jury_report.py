"""Published jury markdown must match the checker and add up."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.report import ru_violation_counts
from synaps_gridplan.synthetic import synthesize_feeder
from synaps_gridplan.versions import GRIDPLAN_VERSION, SYNAPS_COMMIT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))

from jury_benchmark import _ok, render_md  # noqa: E402


def _payload(*, greed_verified: bool, greed_viol: int, repair_verified: bool) -> dict:
    return {
        "gridplan_version": "0.0.0-test",
        "synaps_commit": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "iso16290_trl": 4,
        "instance": {"jobs": 10, "crews": 2, "assets": 3, "outage_windows": 4},
        "scenario_a": {
            "fifo": {
                "assigned": 10,
                "hard_violation_count": 5,
                "verified_feasible": False,
                "violations_ru": {"работа вне окна отключения": 5},
                "wall_time_s": 0.01,
                "status": "error",
            },
            "greed": {
                "assigned": 10,
                "hard_violation_count": greed_viol,
                "verified_feasible": greed_verified,
                "violations_ru": (
                    {"два отключения на одном аппарате": greed_viol} if greed_viol else {}
                ),
                "wall_time_s": 0.2,
                "status": "feasible" if greed_verified else "error",
            },
        },
        "scenario_b": {
            "frozen_windows": 2,
            "disrupted_jobs": ["J1"],
            "repaired": {
                "status": "feasible" if repair_verified else "error",
                "hard_violation_count": 0 if repair_verified else 3,
                "verified_feasible": repair_verified,
                "wall_time_s": 0.05,
            },
            "frozen_windows_moved": 0,
            "churn": {"moved": 0, "added": 0, "removed": 0},
        },
        "scenario_c": {
            "two_runs_identical": True,
            "plan_fingerprint": "abcd" * 16,
        },
    }


def test_render_does_not_pass_a_dirty_greed_plan() -> None:
    text = render_md(_payload(greed_verified=False, greed_viol=4, repair_verified=False))
    assert "| Проверка | нет | нет |" in text
    assert "нельзя показывать" in text
    assert "график без жёстких нарушений" not in text
    assert "✅" not in text


def test_render_passes_only_when_checker_is_clean() -> None:
    text = render_md(_payload(greed_verified=True, greed_viol=0, repair_verified=True))
    assert "| Проверка | нет | да |" in text
    assert "Оптимальность GREED не утверждается" in text
    assert _ok({"verified_feasible": True, "hard_violation_count": 0}) is True
    assert _ok({"verified_feasible": True, "hard_violation_count": 4}) is False


def _section_count_sum(section: str) -> int:
    return sum(int(n) for n in re.findall(r"\| [^|\n]+ \| (\d+) \|", section))


def test_committed_jury_report_matches_pin() -> None:
    report = ROOT / "benchmark" / "results" / "jury_report.md"
    text = report.read_text(encoding="utf-8")
    assert "| Проверка | нет | да |" in text
    assert GRIDPLAN_VERSION in text
    assert SYNAPS_COMMIT[:12] in text
    assert "ПАО «Россети»" in text
    assert "0.1.16" not in text
    assert "gridplan 0.1.10" not in text
    assert "6fd339367a36" not in text
    assert "✅" not in text
    assert "res_severny_benchmark.py" in text
    assert "rosseti_res_benchmark" not in text
    assert "Карпинск" not in text
    assert "Лопатино" not in text
    header = re.search(
        r"\| Жёстких нарушений \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|",
        text,
    )
    assert header is not None
    fifo_n, greed_n = int(header.group(1)), int(header.group(2))
    fifo_sec = text.split("FIFO, расшифровка:")[1].split("GREED, расшифровка:")[0]
    greed_sec = text.split("GREED, расшифровка:")[1].split("\n## ")[0]
    assert _section_count_sum(fifo_sec) == fifo_n
    assert _section_count_sum(greed_sec) == greed_n


def test_fifo_serialized_layers_match_hard_count() -> None:
    problem = synthesize_feeder(mode="small", seed=21)
    outcome = plan_with_config(problem, solver_config="FIFO", apply_frozen=False)
    engine = outcome.metadata.get("engine_violations") or []
    domain = outcome.metadata.get("gridplan_violations") or []
    assert outcome.hard_violation_count == len(engine) + len(domain)
    assert sum(ru_violation_counts(outcome).values()) == outcome.hard_violation_count
