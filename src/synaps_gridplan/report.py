"""Export planning outcomes to JSON / CSV / Markdown (human-readable)."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from typing import Any, Literal

from synaps_gridplan.planner import PlanOutcome
from synaps_gridplan.practice import PRACTICE_LAYER, applicability_limits
from synaps_gridplan.versions import GRIDPLAN_VERSION, ISO16290_TRL, SYNAPS_COMMIT

# Shared labels for demo reports. Unknown kinds are printed as-is.
VIOLATION_KIND_RU: dict[str, str] = {
    "OUTAGE_WINDOW_VIOLATION": "работа вне окна отключения",
    "OUTAGE_WINDOW_MISSING": "нет согласованного окна отключения",
    "FORBIDDEN_OUTAGE_WINDOW": "попадание в запрещённое окно",
    "PRECEDENCE_VIOLATION": "нарушена техпоследовательность",
    "SPARE_PART_SHORTAGE": "не хватает ЗИП",
    "SPARE_PART_NOT_YET_AVAILABLE": "ЗИП ещё не пополнен",
    "QUALIFICATION_MISMATCH": "бригада без нужной квалификации",
    "FROZEN_ASSIGNMENT_CONFLICT": "сдвинуто замороженное окно",
    "HORIZON_VIOLATION": "выход за горизонт планирования",
    "HORIZON_BOUND_VIOLATION": "выход за горизонт (движок)",
    "UNSCHEDULED_JOB": "работа не попала в график",
    "DUPLICATE_ASSIGNMENT": "работа назначена дважды",
    "ASSET_OVERLAP": "два отключения на одном аппарате",
    "CREW_OVERLAP": "бригада назначена дважды на один интервал",
    "MACHINE_OVERLAP": "пересечение слотов на одном рабочем центре",
    "MISSING_ASSIGNMENT": "нет назначения в движке",
    "SETUP_GAP_VIOLATION": "нарушен зазор на переезд",
    "AUX_RESOURCE_CAPACITY_VIOLATION": "нехватка вспомогательного ресурса",
    "DURATION_MISMATCH": "длительность слота не совпадает с нормой",
    "DURATION_BELOW_GRAIN": "слот короче кванта времени",
    "LATEST_FINISH_VIOLATION": "окончание позже latest_finish",
    "SIMULTANEOUS_OUTAGE_BAN": "совпали отключения из явного запрета пары",
    "SHORT_DURATION": "слот короче длительности работы",
    "RELEASE_DATE_VIOLATION": "старт раньше даты выпуска",
    "ELIGIBLE_CREW_MISMATCH": "назначена бригада вне списка допущенных",
    "UNKNOWN_OPERATION": "назначение на неизвестную операцию",
    "UNKNOWN_WORK_CENTER": "назначение на неизвестный рабочий центр",
    "UNKNOWN_CREW": "назначение на неизвестную бригаду",
    "INVALID_ASSIGNMENT_TIME": "назначение без часового пояса",
    "INVALID_ID_MAP": "карта идентификаторов неполна или неоднозначна",
    "INVALID_PROBLEM": "некорректная постановка задачи",
}


def ru_violation_counts(outcome: PlanOutcome) -> dict[str, int]:
    """Counts from both check layers. Sum equals ``hard_violation_count``."""

    raw: Counter[str] = Counter()
    for key in ("gridplan_violations", "engine_violations"):
        for item in outcome.metadata.get(key) or []:
            raw[str(item["kind"])] += 1
    return {VIOLATION_KIND_RU.get(kind, kind): n for kind, n in sorted(raw.items())}


ReportFormat = Literal["json", "csv", "markdown"]


def render_report(outcome: PlanOutcome, *, fmt: ReportFormat = "json") -> str:
    if fmt == "json":
        return json.dumps(_as_dict(outcome), indent=2, default=str)
    if fmt == "csv":
        return _as_csv(outcome)
    if fmt == "markdown":
        return _as_markdown(outcome)
    raise ValueError(f"unsupported format: {fmt}")


def _as_dict(outcome: PlanOutcome) -> dict[str, Any]:
    obj = outcome.schedule.objective
    meta = outcome.metadata or {}
    return {
        "schema_version": outcome.schema_version,
        "plan_id": meta.get("plan_id"),
        "solver_config": outcome.solver_config,
        "status": outcome.status,
        "claim_status": meta.get("claim_status", outcome.status),
        "verified_feasible": outcome.verified_feasible,
        "verification_origin": meta.get("verification_origin", "in_memory_result"),
        "hard_violation_count": outcome.hard_violation_count,
        "claim_level": meta.get("claim_level", "experiment"),
        "iso16290_trl": meta.get("iso16290_trl", ISO16290_TRL),
        "data_provenance": meta.get("data_provenance", "experiment"),
        "input_hash": meta.get("input_hash"),
        "config_hash": meta.get("config_hash"),
        "gridplan_version": meta.get("gridplan_version", GRIDPLAN_VERSION),
        "synaps_commit": meta.get("synaps_commit", SYNAPS_COMMIT),
        "objective": {
            "makespan_minutes": obj.makespan_minutes,
            "total_setup_minutes": obj.total_setup_minutes,
            "total_tardiness_minutes": obj.total_tardiness_minutes,
            "total_energy_kwh": obj.total_energy_kwh,
            "coverage": obj.coverage,
            "unscheduled_operations": obj.unscheduled_operations,
            "weighted_sum": obj.weighted_sum,
        },
        "risk_proxy": meta.get("risk_proxy"),
        "gridplan_violations": meta.get("gridplan_violations", []),
        "engine_violations": meta.get("engine_violations", []),
        "optimality_note": meta.get("optimality_note"),
        "assignments": [
            {
                "operation_id": str(a.operation_id),
                "work_center_id": str(a.work_center_id),
                "start_time": a.start_time.isoformat(),
                "end_time": a.end_time.isoformat(),
                "setup_minutes": a.setup_minutes,
            }
            for a in outcome.schedule.assignments
        ],
        "frozen_assignment_count": sum(fr.immutable for fr in outcome.frozen_assignments),
        "metadata": meta,
        "id_map_size": len(outcome.id_map),
        "practice": meta.get("practice"),
        "applicability_limits": applicability_limits(),
    }


def _csv_cell(value: Any) -> Any:
    """Keep formula-like text inert on common spreadsheet imports.

    CSV quoting handles separators/newlines, but does not stop formulas. Raw
    machine-readable values remain available in JSON; CSV is a display export.
    """
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip(" \t\r\n\ufeff").startswith(("=", "+", "-", "@"))
    ):
        return "'" + value
    return value


def _as_csv(outcome: PlanOutcome) -> str:
    buf = io.StringIO()
    meta = outcome.metadata or {}
    # Use the CSV encoder for preamble rows too: metadata can contain newlines.
    preamble = {
        "claim_level": meta.get("claim_level", "experiment"),
        "iso16290_trl": meta.get("iso16290_trl", ISO16290_TRL),
        "data_provenance": meta.get("data_provenance", "experiment"),
        "input_hash": meta.get("input_hash", ""),
        "config_hash": meta.get("config_hash", ""),
        "gridplan_version": meta.get("gridplan_version", GRIDPLAN_VERSION),
        "synaps_commit": meta.get("synaps_commit", SYNAPS_COMMIT),
        "status": outcome.status,
        "verified_feasible": outcome.verified_feasible,
        "verification_origin": meta.get("verification_origin", "in_memory_result"),
    }
    preamble_writer = csv.writer(buf, lineterminator="\n")
    for key, value in preamble.items():
        preamble_writer.writerow([f"# {key}", _csv_cell(value)])

    frozen_ops: set[str] = set()
    for fr in outcome.frozen_assignments:
        op = outcome.id_map.get(f"job:{fr.job_id}")
        if fr.immutable and op is not None:
            frozen_ops.add(str(op))

    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "operation_id",
            "work_center_id",
            "start_time",
            "end_time",
            "setup_minutes",
            "frozen",
            "status",
            "source",
        ],
        lineterminator="\n",
    )
    writer.writeheader()
    for a in outcome.schedule.assignments:
        writer.writerow(
            {
                "operation_id": str(a.operation_id),
                "work_center_id": str(a.work_center_id),
                "start_time": a.start_time.isoformat(),
                "end_time": a.end_time.isoformat(),
                "setup_minutes": a.setup_minutes,
                "frozen": str(a.operation_id) in frozen_ops,
                "status": _csv_cell(outcome.status),
                "source": _csv_cell(outcome.solver_config),
            }
        )
    return buf.getvalue()


def _md_inline(value: Any) -> str:
    """Keep Markdown a single visual line; backticks cannot break out of inline code."""

    return str(value).replace("\r", " ").replace("\n", " ").replace("`", "'")


def _as_markdown(outcome: PlanOutcome) -> str:
    obj = outcome.schedule.objective
    meta = outcome.metadata or {}
    risk = meta.get("risk_proxy") or {}
    lines = [
        "# SynAPS-GridPlan report",
        "",
        f"- schema: `{_md_inline(outcome.schema_version)}`",
        f"- gridplan_version: `{_md_inline(meta.get('gridplan_version', GRIDPLAN_VERSION))}`",
        f"- synaps_commit: `{_md_inline(meta.get('synaps_commit', SYNAPS_COMMIT))}`",
        f"- solver: `{_md_inline(outcome.solver_config)}`",
        f"- status: **{_md_inline(outcome.status)}**",
        f"- claim_status: `{_md_inline(meta.get('claim_status', outcome.status))}`",
        f"- verified_feasible: **{outcome.verified_feasible}**",
        (
            "- verification_origin: "
            f"`{_md_inline(meta.get('verification_origin', 'in_memory_result'))}`"
        ),
        f"- hard_violations: {outcome.hard_violation_count}",
        f"- claim_level: `{_md_inline(meta.get('claim_level', 'experiment'))}`",
        f"- iso16290_trl: `{meta.get('iso16290_trl', ISO16290_TRL)}`",
        f"- data_provenance: `{_md_inline(meta.get('data_provenance', 'experiment'))}`",
        f"- input_hash: `{_md_inline(meta.get('input_hash', ''))}`",
        f"- config_hash: `{_md_inline(meta.get('config_hash', ''))}`",
        f"- frozen_assignments: {sum(fr.immutable for fr in outcome.frozen_assignments)}",
        f"- assignments: {len(outcome.schedule.assignments)}",
        f"- unscheduled_operations: {obj.unscheduled_operations}",
        "",
        "## Objective",
        "",
        "| makespan_min | setup_min | tardiness_min | coverage | unscheduled |",
        "| ---: | ---: | ---: | ---: | ---: |",
        (
            f"| {obj.makespan_minutes:.1f} | {obj.total_setup_minutes:.1f} | "
            f"{obj.total_tardiness_minutes:.1f} | {obj.coverage:.3f} | "
            f"{obj.unscheduled_operations} |"
        ),
        "",
        "## Risk proxy (advisory)",
        "",
        f"- before: {risk.get('risk_exposure_before')}",
        f"- after: {risk.get('risk_exposure_after')}",
        f"- delta: {risk.get('risk_exposure_delta')}",
        f"- overdue_risk_exposure: {risk.get('overdue_risk_exposure')}",
        f"- unserved_critical_jobs: "
        f"{risk.get('unserved_critical_jobs', risk.get('unserved_critical_assets'))}",
        f"- critical_jobs_late: {risk.get('critical_jobs_late')}",
        f"- note: {_md_inline(risk.get('claim_note', 'proxy only'))}",
        "",
        "## Violations",
        "",
    ]
    if meta.get("verification_origin") == "imported_snapshot_not_rechecked":
        lines[2:2] = [
            "> Saved snapshot: verification flags were not rechecked against a GridPlan problem.",
            "",
        ]
    gp = meta.get("gridplan_violations") or []
    engine = meta.get("engine_violations") or []
    for v in gp[:20]:
        lines.append(f"- `{_md_inline(v.get('kind'))}`: {_md_inline(v.get('message'))}")
    if not gp:
        lines.append("- none recorded at GridPlan layer")
    lines.append("")
    if engine:
        lines.append("Engine (SynAPS) hard violations:")
        for v in engine[:20]:
            lines.append(f"- `{_md_inline(v.get('kind'))}`: {_md_inline(v.get('message'))}")
    else:
        lines.append("Engine (SynAPS) hard violations: none")
    practice = meta.get("practice") or {}
    layer = practice.get("layer", PRACTICE_LAYER)
    security = practice.get("electrical_security", "out_of_scope")
    limit_lines = [f"- {item}" for item in applicability_limits()]
    lines.extend(
        [
            "",
            "## Applicability limits",
            "",
            *limit_lines,
            "",
            f"- practice layer: `{_md_inline(layer)}`",
            f"- electrical_security: `{_md_inline(security)}` (see PRACTICE.md).",
            "",
            "## Next step recommendation",
            "",
            "- Validate the same scenario on customer-sanitized data before any pilot claim.",
            "",
        ]
    )
    if meta.get("optimality_note"):
        lines.extend(["", f"Optimality note: {_md_inline(meta['optimality_note'])}", ""])
    return "\n".join(lines)
