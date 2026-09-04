"""Synthetic GRES-block ТОиР. Not a named-station dump.

Dual-GTU ban is combinatorial (not N-1). Blade ЗИП is consumable. FIFO is
dirty on the stock instance; GREED is not. Ban occupancy is the hull of a
precedence-connected interruption chain (Goel & Meisel, EJOR 2013).
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
from synaps_gridplan.synthetic_gres import synthesize_gres_block


def _job(problem, ref: str):
    return next(job for job in problem.jobs if job.external_ref == ref)


def _asset(problem, code: str):
    return next(asset for asset in problem.assets if asset.code == code)


def _crew(problem, code: str):
    return next(crew for crew in problem.crews if crew.code == code)


def _span(outcome, problem, ref: str) -> tuple:
    job = _job(problem, ref)
    op_id = outcome.id_map[f"job:{job.id}"]
    asn = next(a for a in outcome.schedule.assignments if a.operation_id == op_id)
    return asn.start_time, asn.end_time


def test_gres_block_is_synthetic_and_deterministic() -> None:
    a = synthesize_gres_block(seed=42)
    b = synthesize_gres_block(seed=42)
    assert a.domain_attributes["data_provenance"] == "synthetic"
    assert a.domain_attributes["not_live_el5"] is True
    assert a.model_dump(mode="json") == b.model_dump(mode="json")
    assert synthesize_gres_block(seed=1).model_dump(mode="json") != a.model_dump(mode="json")


def test_gres_seed_salts_ids_not_topology() -> None:
    """Seed is UUID salt. Days, quals, ban pair, job refs do not reshape."""

    a = synthesize_gres_block(seed=1)
    b = synthesize_gres_block(seed=2)
    assert [job.external_ref for job in a.jobs] == [job.external_ref for job in b.jobs]
    assert {job.id for job in a.jobs} != {job.id for job in b.jobs}
    assert [w.external_ref for w in a.outage_windows] == [w.external_ref for w in b.outage_windows]


def test_gres_block_has_gtu_chains_and_explicit_ban() -> None:
    problem = synthesize_gres_block(seed=7)
    codes = {asset.code for asset in problem.assets}
    assert {"GTU-1", "GTU-2", "BOP-FWP", "SWYD-110"} <= codes
    refs = {job.external_ref for job in problem.jobs}
    assert "Изоляция GTU-1" in refs
    assert "Ремонт GTU-1" in refs
    assert "Испытания GTU-1" in refs
    assert "Срочная дефектация ПЭН" in refs
    assert len(problem.simultaneous_outage_bans) == 1
    ban = problem.simultaneous_outage_bans[0]
    assert "not N-1" in ban.reason
    gtu_ids = {asset.id for asset in problem.assets if asset.code.startswith("GTU-")}
    assert {ban.asset_id_a, ban.asset_id_b} == gtu_ids


def test_gres_block_greed_verifies() -> None:
    problem = synthesize_gres_block(seed=42)
    outcome = plan_with_config(problem, solver_config="GREED")
    kinds = outcome.metadata.get("gridplan_violation_kinds", [])
    assert outcome.ok, (outcome.status, kinds, outcome.hard_violation_count)
    assert outcome.verified_feasible
    assert outcome.hard_violation_count == 0
    assert len(outcome.schedule.assignments) == len(problem.jobs)
    assert outcome.status != "optimal"
    assert outcome.metadata.get("claim_status") == "heuristic_feasible"
    assert "SIMULTANEOUS_OUTAGE_BAN" not in kinds
    assert "OUTAGE_WINDOW_VIOLATION" not in kinds


def test_gres_gtu_chain_serializes_inside_clearance() -> None:
    """Chained isolate→repair→test touch-serialize inside one ПЛ window."""

    problem = synthesize_gres_block(seed=42)
    outcome = plan_with_config(problem, solver_config="GREED")
    assert outcome.verified_feasible
    window = next(w for w in problem.outage_windows if w.asset_id == _asset(problem, "GTU-1").id)
    iso_s, iso_e = _span(outcome, problem, "Изоляция GTU-1")
    rep_s, rep_e = _span(outcome, problem, "Ремонт GTU-1")
    tst_s, tst_e = _span(outcome, problem, "Испытания GTU-1")
    assert iso_e <= rep_s <= rep_e <= tst_s
    assert iso_s >= window.start and tst_e <= window.end


def test_gres_fifo_does_not_verify() -> None:
    """Same class as РЭС Scenario A: calendar FIFO is not a GRES solver claim."""

    problem = synthesize_gres_block(seed=42)
    outcome = plan_with_config(problem, solver_config="FIFO")
    assert outcome.verified_feasible is False
    kinds = set(outcome.metadata.get("gridplan_violation_kinds", []))
    assert kinds & {
        "OUTAGE_WINDOW_VIOLATION",
        "SIMULTANEOUS_OUTAGE_BAN",
        "ASSET_OVERLAP",
        "PRECEDENCE_VIOLATION",
    }


def test_gres_dual_gtu_overlap_is_ban_not_n1() -> None:
    """Align both ПЛ windows, overlap isolations — BAN fires without a window miss."""

    problem = synthesize_gres_block(seed=42)
    gtu1, gtu2 = _asset(problem, "GTU-1"), _asset(problem, "GTU-2")
    w1 = next(w for w in problem.outage_windows if w.asset_id == gtu1.id)
    aligned = [
        w.model_copy(update={"start": w1.start, "end": w1.end})
        if w.asset_id in {gtu1.id, gtu2.id}
        else w
        for w in problem.outage_windows
    ]
    problem = problem.model_copy(update={"outage_windows": aligned})
    iso1, iso2 = _job(problem, "Изоляция GTU-1"), _job(problem, "Изоляция GTU-2")
    eto1, eto2 = _crew(problem, "ЭТО-1"), _crew(problem, "ЭТО-2")
    schedule_problem, id_map = to_schedule_problem(problem)
    forged = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{iso1.id}"],
                    work_center_id=id_map[f"crew:{eto1.id}"],
                    start_time=w1.start,
                    end_time=w1.start + timedelta(minutes=iso1.duration_min),
                ),
                Assignment(
                    operation_id=id_map[f"job:{iso2.id}"],
                    work_center_id=id_map[f"crew:{eto2.id}"],
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
    assert "not N-1" in problem.simultaneous_outage_bans[0].reason


def test_gres_ban_skips_online_bop() -> None:
    """Ban is interruption-only. Online ПЭН during a GTU outage is not N-1."""

    problem = synthesize_gres_block(seed=42)
    iso = _job(problem, "Изоляция GTU-1")
    bop = _job(problem, "Срочная дефектация ПЭН")
    window = next(w for w in problem.outage_windows if w.asset_id == iso.asset_id)
    eto, mech = _crew(problem, "ЭТО-1"), _crew(problem, "МЕХ-1")
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
                    operation_id=id_map[f"job:{bop.id}"],
                    work_center_id=id_map[f"crew:{mech.id}"],
                    start_time=window.start,
                    end_time=window.start + timedelta(minutes=bop.duration_min),
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


def test_gres_blade_stock_is_consumable_not_concurrent() -> None:
    """Two staggered GTU repairs still consume two blades. qty=1 must not verify."""

    problem = synthesize_gres_block(seed=42)
    spare = problem.spare_parts[0].model_copy(update={"available_quantity": 1, "stock_qty": 1})
    problem = problem.model_copy(update={"spare_parts": [spare]})
    outcome = plan_with_config(problem, solver_config="GREED")
    assert outcome.verified_feasible is False
    assert "SPARE_PART_SHORTAGE" in outcome.metadata.get("gridplan_violation_kinds", [])


def test_cli_synthesize_gres_block(tmp_path: Path) -> None:
    out = tmp_path / "gres.json"
    assert main(["synthesize", "--mode", "gres-block", "--seed", "3", "-o", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["domain_attributes"]["generator"] == "synthesize_gres_block"
    assert payload["domain_attributes"]["not_live_el5"] is True


def test_cli_gres_block_rejects_feeder_sizing(tmp_path: Path) -> None:
    out = tmp_path / "gres.json"
    assert main(["synthesize", "--mode", "gres-block", "--assets", "99", "-o", str(out)]) == 2
    assert not out.exists()


def test_gres_chain_hull_occupies_the_gap_for_the_ban() -> None:
    """Goel EJOR 2013: unit downtime is first isolate → last test, not task union.

    Align ПЛ windows. Place GTU-1 isolate and tests with a midday gap, GTU-2
    isolate inside that gap. Pairwise job intervals miss; chain hull must BAN.
    """

    problem = synthesize_gres_block(seed=42)
    gtu1, gtu2 = _asset(problem, "GTU-1"), _asset(problem, "GTU-2")
    w1 = next(w for w in problem.outage_windows if w.asset_id == gtu1.id)
    aligned = [
        w.model_copy(update={"start": w1.start, "end": w1.end})
        if w.asset_id in {gtu1.id, gtu2.id}
        else w
        for w in problem.outage_windows
    ]
    problem = problem.model_copy(update={"outage_windows": aligned})
    iso1 = _job(problem, "Изоляция GTU-1")
    tst1 = _job(problem, "Испытания GTU-1")
    iso2 = _job(problem, "Изоляция GTU-2")
    eto1, eto2 = _crew(problem, "ЭТО-1"), _crew(problem, "ЭТО-2")
    kip = _crew(problem, "КИПиА-1")
    schedule_problem, id_map = to_schedule_problem(problem)
    forged = type(
        "R",
        (),
        {
            "assignments": [
                Assignment(
                    operation_id=id_map[f"job:{iso1.id}"],
                    work_center_id=id_map[f"crew:{eto1.id}"],
                    start_time=w1.start,
                    end_time=w1.start + timedelta(minutes=iso1.duration_min),
                ),
                Assignment(
                    operation_id=id_map[f"job:{tst1.id}"],
                    work_center_id=id_map[f"crew:{kip.id}"],
                    start_time=w1.start + timedelta(hours=10),
                    end_time=w1.start + timedelta(hours=13),
                ),
                Assignment(
                    operation_id=id_map[f"job:{iso2.id}"],
                    work_center_id=id_map[f"crew:{eto2.id}"],
                    start_time=w1.start + timedelta(hours=4),
                    end_time=w1.start + timedelta(hours=6),
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
