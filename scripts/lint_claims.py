"""Fail CI if banned promotional phrases appear as live claims.

Retract notes, LIMITS, and this scanner are skipped. A hit on a line that
already negates the phrase (нет / не / withdrawn / …) is not a failure.

Historical catalog is skipped on purpose (CLAIMS_REGISTRY.md): numbered
``docs/0…29_*``, ``_SUBMIT_MIK_2026_08_18/``, ``docs/rfc/``. Binary
suffixes including ``.pdf`` are skipped — this scanner is text/OOXML.
"""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED_FILE = ROOT / "docs" / "BANNED_CLAIMS.txt"
A_T = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"

SKIP_NAMES = {
    "docs/BANNED_CLAIMS.txt",
    "docs/PITCH_V7_FACTCHECK.md",
    "docs/LIMITS.md",
    "docs/CLAIMS_REGISTRY.md",
    "scripts/lint_claims.py",
    "scripts/export_test_count.py",
    "tests/test_lint_claims.py",
    "CHANGELOG.md",
    "AUDIT.md",
}
SKIP_PREFIXES = ("_SUBMIT_MIK_2026_08_18/", "docs/rfc/")
SKIP_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".lock", ".svg"}
NEGATION_MARKERS = (
    "не ",
    "нет ",
    "не\u00a0",
    "запрещ",
    "withdrawn",
    "retract",
    "не утвержд",
    "не заявл",
    "не копир",
    "не ставить",
    "не является",
    "не партнёр",
    "удалить",
)


def load_phrases() -> list[str]:
    phrases: list[str] = []
    for raw in BANNED_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        phrases.append(line)
    if not phrases:
        raise ValueError(f"no phrases in {BANNED_FILE}")
    return phrases


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def skip_path(path: Path) -> bool:
    rel = _rel(path)
    if rel in SKIP_NAMES or path.suffix.lower() in SKIP_SUFFIXES:
        return True
    if any(rel.startswith(prefix) for prefix in SKIP_PREFIXES):
        return True
    return bool(re.match(r"docs/\d", rel))


def pptx_text(path: Path) -> str:
    chunks: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not re.match(r"ppt/slides/slide\d+\.xml$", name):
                continue
            root = ET.fromstring(zf.read(name))
            chunks.extend(node.text or "" for node in root.iter(A_T))
    return "\n".join(chunks)


def file_text(path: Path) -> str | None:
    if path.suffix.lower() == ".pptx":
        return pptx_text(path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def line_is_negated(line: str, phrase: str) -> bool:
    low = line.lower()
    idx = low.find(phrase.lower())
    if idx < 0:
        return False
    window = low[max(0, idx - 96) : idx]
    return any(marker in window for marker in NEGATION_MARKERS)


def find_hits(text: str, phrases: list[str]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        for phrase in phrases:
            if phrase.lower() in line.lower() and not line_is_negated(line, phrase):
                hits.append((i, phrase))
    return hits


def _tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / name.decode("utf-8") for name in raw.split(b"\0") if name]


def iter_hits() -> list[str]:
    phrases = load_phrases()
    rows: list[str] = []
    for path in _tracked_files():
        if not path.is_file() or skip_path(path):
            continue
        if path.suffix.lower() not in {".md", ".js", ".txt", ".pptx"}:
            continue
        text = file_text(path)
        if text is None:
            continue
        rel = _rel(path)
        for line_no, phrase in find_hits(text, phrases):
            rows.append(f"{rel}:{line_no}: {phrase}")
    return rows


def main() -> int:
    hits = iter_hits()
    if hits:
        sys.stderr.write("banned-claim hits:\n")
        sys.stderr.write("\n".join(hits) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
