"""Crew shift windows compiled into the solver calendar.

An empty ``shift_calendar`` and an empty ``availability`` together mean
round-the-clock. Either list alone is the calendar. Both lists contribute
their intersection. A disjoint pair must not collapse back to round-the-clock.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from synaps_gridplan.model import Crew, CrewCalendarWindow


def compiled_crew_windows(
    crew: Crew, *, horizon_start: datetime
) -> list[tuple[datetime, datetime]]:
    shift = _rows(crew.shift_calendar)
    available = _rows(crew.availability)
    if not shift and not available:
        return []
    if not shift:
        return available
    if not available:
        return shift
    overlap = _intersect(shift, available)
    if overlap:
        return overlap
    # A closed crew is not a 24/7 crew. One minute before the horizon fits
    # no in-horizon occupancy.
    return [(horizon_start - timedelta(minutes=1), horizon_start)]


def longest_open_minutes(crew: Crew, *, horizon_start: datetime) -> int | None:
    """Longest open interval in minutes. ``None`` means round-the-clock."""

    windows = compiled_crew_windows(crew, horizon_start=horizon_start)
    if not windows:
        return None
    return max(int((end - start).total_seconds() // 60) for start, end in windows)


def day_part_minutes(duration_min: int, window_minutes: int) -> list[int]:
    """Split a job that does not fit in one open interval. Parts sum to the job."""

    if window_minutes <= 0 or duration_min <= window_minutes:
        return [duration_min]
    parts: list[int] = []
    remaining = duration_min
    while remaining > 0:
        piece = min(window_minutes, remaining)
        parts.append(piece)
        remaining -= piece
    return parts


def _rows(windows: list[CrewCalendarWindow]) -> list[tuple[datetime, datetime]]:
    return _merge((window.start, window.end) for window in windows)


def _intersect(
    left: list[tuple[datetime, datetime]],
    right: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    pieces: list[tuple[datetime, datetime]] = []
    for left_start, left_end in left:
        for right_start, right_end in right:
            start = max(left_start, right_start)
            end = min(left_end, right_end)
            if end > start:
                pieces.append((start, end))
    return _merge(pieces)


def _merge(rows: Iterable[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(rows):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        if end > previous_end:
            merged[-1] = (previous_start, end)
    return merged
