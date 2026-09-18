"""Evidence bundle renderer must not invent a partnership or mix datasets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evidence_bundle import bundle_ok, render_md  # noqa: E402


def _bundle(**overrides):
    base = {
        "environment": {
            "recorded_at_utc": "2026-09-18T00:00:00+00:00",
            "gridplan_version": "0.1.8",
            "iso16290_trl": 4,
            "synaps_commit": "6178c93b705ff58be21fa74a98651883a2da1169",
            "git_commit": "abc",
            "git_dirty": False,
            "python": "3.12.0",
            "platform": "test",
        },
        "pytest": {"returncode": 0, "wall_time_s": 1.0, "cmd": ["pytest", "-q"]},
        "jury": {
            "instance": {"jobs": 55, "crews": 7, "assets": 39, "outage_windows": 85},
            "scenario_a": {
                "fifo": {
                    "status": "error",
                    "verified_feasible": False,
                    "hard_violation_count": 107,
                    "wall_time_s": 0.02,
                },
                "greed": {
                    "status": "feasible",
                    "verified_feasible": True,
                    "hard_violation_count": 0,
                    "wall_time_s": 0.2,
                },
            },
        },
        "cpsat_res_severny": {
            "status": "optimal",
            "verified_feasible": True,
            "hard_violation_count": 0,
            "wall_time_s": 8.0,
            "best_objective_bound": 100,
            "objective_bound_units": "makespan_minutes",
            "makespan_minutes": 100,
        },
    }
    base.update(overrides)
    return base


def test_render_names_one_instance_and_no_partner() -> None:
    text = render_md(_bundle())
    assert "РЭС «Северный»" in text
    assert "scale-фидер сюда не входят" in text
    assert "Россети" not in text
    assert "партнёр" not in text.lower() or "Партнёрств" in text
    assert "0.1.8" in text


def test_bundle_ok_requires_clean_greed_and_optimal_cpsat() -> None:
    assert bundle_ok(_bundle())
    dirty = _bundle()
    dirty["jury"]["scenario_a"]["greed"]["hard_violation_count"] = 3
    assert not bundle_ok(dirty)
    timeout = _bundle()
    timeout["cpsat_res_severny"]["status"] = "feasible"
    assert not bundle_ok(timeout)
