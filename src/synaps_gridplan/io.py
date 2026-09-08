"""Bounded file reads at the CLI trust boundary."""

from __future__ import annotations

from pathlib import Path

from synaps_gridplan.limits import MAX_JSON_BYTES


def read_text_limited(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> str:
    """Read UTF-8 text, refusing anything larger than the lab quota.

    The cap is applied to bytes actually read so a file that grows between
    ``stat`` and ``read`` cannot bypass the quota.
    """

    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"{path} is larger than {max_bytes} bytes; limit is {max_bytes}")
    return data.decode("utf-8")
