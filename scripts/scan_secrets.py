"""Pattern scan of tracked files for high-risk credential shapes.

This is not entropy analysis, a licensed secret-scanning product, or a
guarantee that every credential form is recognised.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".lock"}
PATTERNS = (
    (re.compile(r"BEGIN [A-Z ]{0,20}PRIVATE KEY"), "private-key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws-access-key-id"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "github-pat"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{22,}"), "github-fine-grained-pat"),
)


def _tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / name.decode("utf-8") for name in raw.split(b"\0") if name]


def main() -> int:
    hits: list[str] = []
    for path in _tracked_files():
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        if path.name == "scan_secrets.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for compiled, label in PATTERNS:
            if compiled.search(text):
                hits.append(f"{path.relative_to(ROOT)}: {label}")
    if hits:
        sys.stderr.write("secret-pattern hits:\n")
        sys.stderr.write("\n".join(hits) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
