"""Small shift fixture for section E. Not the 55-job monthly ``res_severny`` plan."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from synaps_gridplan.model import Asset, Crew, CrewCalendarWindow, GridPlanProblem, MaintenanceJob

MSK = timezone(timedelta(hours=3))
DAY = datetime(2026, 10, 5, tzinfo=MSK)


def build_res_severny_shifts() -> GridPlanProblem:
    """Two Moscow day shifts and one job longer than a single shift.

    Synthetic. Zero travel, so a day part can fill a shift exactly.
    """

    asset = Asset(code="VL-SHIFT", location_code="L")
    rows = []
    for offset in range(2):
        start = DAY + timedelta(days=offset, hours=8)
        rows.append(CrewCalendarWindow(start=start, end=start + timedelta(hours=9)))
    crew = Crew(code="BR-SHIFT", home_location_code="L", shift_calendar=rows)
    job = MaintenanceJob(
        external_ref="TO-LONG",
        asset_id=asset.id,
        duration_min=600,
        eligible_crew_ids=[crew.id],
    )
    return GridPlanProblem(
        assets=[asset],
        crews=[crew],
        jobs=[job],
        planning_horizon_start=DAY,
        planning_horizon_end=DAY + timedelta(days=2),
    )


def render_section_e(*, greed_ok: bool, cpsat_ok: bool, part_count: int) -> str:
    greed = "да" if greed_ok else "нет"
    cpsat = "да" if cpsat_ok else "нет"
    return (
        "## E. Смены 08–17 МСК (res_severny_shifts)\n\n"
        "Отдельный синтетический срез, не месячный план «Северный» и не те же 55 работ. "
        "Смена 08:00–17:00 по Москве, два дня, переезд 0. Работа 600 минут длиннее смены "
        f"и собрана в {part_count} дневные части одной цепочки. "
        "Отключение — от старта первой части до конца последней. "
        "Это не трудовой ростер.\n\n"
        "| Проверка | GREED | CPSAT-10 |\n"
        "| --- | --- | --- |\n"
        f"| verified_feasible | {greed} | {cpsat} |\n"
    )
