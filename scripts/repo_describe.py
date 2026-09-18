"""Return ``git describe --tags --always --dirty`` for deck footers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_describe(*, cwd: Path = ROOT) -> str:
    raw = subprocess.check_output(
        ["git", "describe", "--tags", "--always", "--dirty"],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    value = raw.strip()
    if not value:
        raise RuntimeError("git describe returned empty")
    return value


def main() -> int:
    sys.stdout.write(git_describe() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
