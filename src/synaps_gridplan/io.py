"""Bounded file reads at the CLI trust boundary."""

from __future__ import annotations

from pathlib import Path

from synaps_gridplan.limits import MAX_JSON_BYTES


def read_text_limited(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> str:
    """Read UTF-8 text only after the on-disk size is within the lab quota."""

    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"{path} is {size} bytes; limit is {max_bytes}")
    return path.read_text(encoding="utf-8")
