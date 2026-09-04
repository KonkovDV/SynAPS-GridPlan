"""Synthetic dual-feed hall. Not MMTS-9 / MSK-IX / a named cloud campus.

Mutex is concurrent-maintainability analogue (Uptime Tier III class): do not
occupy both declared utility paths at once. Not N-1, not an IX cascade.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from synaps.model import Assignment

from synaps_gridplan.adapter import to_schedule_problem
from synaps_gridplan.baselines import plan_with_config
from synaps_gridplan.cli import main
from synaps_gridplan.constraints import check_gridplan_constraints
from synaps_gridplan.synthetic_hall import synthesize_dual_feed_hall


def _job(problem, ref: str):
    return next(job for job in problem.jobs if job.external_ref == ref)


def _asset(problem, code: str):
    return next(asset for asset in problem.assets if asset.code == code)


def _crew(problem, code: str):
    return next(crew for crew in problem.crews if crew.code == code)


def test_hall_is_synthetic_and_not_a_live_ix() -> None:
    a = synthesize_dual_feed_hall(seed=42)
    b = synthesize_dual_feed_hall(seed=42)
    assert a.domain_attributes["data_provenance"] == "synthetic"
    assert a.domain_attributes["not_live_m9"] is True
    assert a.domain_attributes["not_live_el5"] is True
    assert a.model_dump(mode="json") == b.model_dump(mode="json")
    blob = json.dumps(a.model_dump(mode="json"), ensure_ascii=False).lower()
    assert "ммтс-9" not in blob
    assert "м9" not in blob
    assert "яндекс" not in blob
    assert "butlerova" not in blob


def test_hall_seed_salts_ids() -> None:
    a = synthesize_dual_feed_hall(seed=1)
    b = synthesize_dual_feed_hall(seed=2)
    assert [job.external_ref for job in a.jobs] == [job.external_ref for job in b.jobs]
    assert {job.id for job in a.jobs} != {job.id for job in b.jobs}


def test_hall_has_two_feeds_and_explicit_ban() -> None:
    problem = synthesize_dual_feed_hall(seed=7)
    codes = {asset.code for asset in problem.assets}
    assert {"FEED-A", "FEED-B", "HALL-UPS", "BUS-10"} <= codes
    refs = {job.external_ref for job in problem.jobs}
    assert "Изоляция FEED-A" in refs
    assert "Включение FEED-B" in refs
    assert "Прогон ДГУ (без отключения вводов)" in refs
    assert len(problem.simultaneous_outage_bans) == 1
    ban = problem.simultaneous_outage_bans[0]
    assert "not N-1" in ban.reason
    assert "not M9" in ban.reason
    feed_ids = {asset.id for asset in problem.assets if asset.code.startswith("FEED-")}
    assert {ban.asset_id_a, ban.asset_id_b} == feed_ids


def test_hall_greed_verifies() -> None:
    problem = synthesize_dual_feed_hall(seed=42)
    outcome = plan_with_config(problem, solver_config="GREED")
    kinds = outcome.metadata.get("gridplan_violation_kinds", [])
    assert outcome.ok, (outcome.status, kinds, outcome.hard_violation_count)
    assert outcome.verified_feasible
    assert outcome.hard_violation_count == 0
    assert len(outcome.schedule.assignments) == len(problem.jobs)
    assert "SIMULTANEOUS_OUTAGE_BAN" not in kinds


def test_hall_fifo_does_not_verify() -> None:
    problem = synthesize_dual_feed_hall(seed=42)
    outcome = plan_with_config(problem, solver_config="FIFO")
    assert outcome.verified_feasible is False
    kinds = set(outcome.metadata.get("gridplan_violation_kinds", []))
    assert kinds & {
        "OUTAGE_WINDOW_VIOLATION",
        "SIMULTANEOUS_OUTAGE_BAN",
        "ASSET_OVERLAP",
        "PRECEDENCE_VIOLATION",
    }


def test_hall_overlap_is_ban_not_n1() -> None:
    problem = synthesize_dual_feed_hall(seed=42)
    fa, fb = _asset(problem, "FEED-A"), _asset(problem, "FEED-B")
    w1 = next(w for w in problem.outage_windows if w.asset_id == fa.id)
    aligned = [
        w.model_copy(update={"start": w1.start, "end": w1.end})
        if w.asset_id in {fa.id, fb.id}
        else w
        for w in problem.outage_windows
    ]
    problem = problem.model_copy(update={"outage_windows": aligned})
    iso1, iso2 = _job(problem, "Изоляция FEED-A"), _job(problem, "Изоляция FEED-B")
    eto_a, eto_b = _crew(problem, "ЭТО-A"), _crew(problem, "ЭТО-B")
    schedule_problem, id_map = to_schedule_problem(problem)
    forged = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{iso1.id}"],
                    work_center_id=id_map[f"crew:{eto_a.id}"],
                    start_time=w1.start,
                    end_time=w1.start + timedelta(minutes=iso1.duration_min),
                ),
                Assignment(
                    operation_id=id_map[f"job:{iso2.id}"],
                    work_center_id=id_map[f"crew:{eto_b.id}"],
                    start_time=w1.start + timedelta(minutes=10),
                    end_time=w1.start + timedelta(minutes=10 + iso2.duration_min),
                ),
            ]
        },
    )()
    kinds = {
        v.kind
        for v in check_gridplan_constraints(
            problem, schedule_problem=schedule_problem, result=forged, id_map=id_map
        )
    }
    assert "SIMULTANEOUS_OUTAGE_BAN" in kinds
    assert "OUTAGE_WINDOW_VIOLATION" not in kinds


def test_hall_dgu_online_is_not_a_feed_ban() -> None:
    problem = synthesize_dual_feed_hall(seed=42)
    iso = _job(problem, "Изоляция FEED-A")
    dgu = _job(problem, "Прогон ДГУ (без отключения вводов)")
    window = next(w for w in problem.outage_windows if w.asset_id == iso.asset_id)
    eto, diesel = _crew(problem, "ЭТО-A"), _crew(problem, "ДГУ-1")
    schedule_problem, id_map = to_schedule_problem(problem)
    forged = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{iso.id}"],
                    work_center_id=id_map[f"crew:{eto.id}"],
                    start_time=window.start,
                    end_time=window.start + timedelta(minutes=iso.duration_min),
                ),
                Assignment(
                    operation_id=id_map[f"job:{dgu.id}"],
                    work_center_id=id_map[f"crew:{diesel.id}"],
                    start_time=window.start,
                    end_time=window.start + timedelta(minutes=dgu.duration_min),
                ),
            ]
        },
    )()
    kinds = {
        v.kind
        for v in check_gridplan_constraints(
            problem, schedule_problem=schedule_problem, result=forged, id_map=id_map
        )
    }
    assert "SIMULTANEOUS_OUTAGE_BAN" not in kinds


def test_cli_synthesize_dual_feed_hall(tmp_path: Path) -> None:
    out = tmp_path / "hall.json"
    assert main(["synthesize", "--mode", "dual-feed-hall", "--seed", "3", "-o", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["domain_attributes"]["generator"] == "synthesize_dual_feed_hall"
    assert payload["domain_attributes"]["not_live_m9"] is True


def test_cli_dual_feed_hall_rejects_feeder_sizing(tmp_path: Path) -> None:
    out = tmp_path / "hall.json"
    assert main(["synthesize", "--mode", "dual-feed-hall", "--assets", "99", "-o", str(out)]) == 2
    assert not out.exists()
