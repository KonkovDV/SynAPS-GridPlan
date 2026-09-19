"""Executable claims registry: artifacts exist; deck/README numbers are tagged."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "CLAIMS_REGISTRY.md"
GATED_HEADING = "## CI-gated (README)"
README = ROOT / "README.md"

HEADER = (
    "claim_id",
    "текст",
    "артефакт-источник",
    "команда воспроизведения",
    "статус",
)
TOKEN_RE = re.compile(r"`([^`]+)`|https?://\S+|[A-Za-z0-9_./\\-]+\.(?:py|md|toml|txt|pptx|json)")


def _gated_table_text(src: str) -> str:
    start = src.find(GATED_HEADING)
    assert start >= 0, f"missing {GATED_HEADING}"
    rest = src[start:]
    nxt = rest.find("\n## ", len(GATED_HEADING) + 1)
    return rest if nxt < 0 else rest[:nxt]


def parse_gated_rows(src: str) -> list[dict[str, str]]:
    block = _gated_table_text(src)
    rows: list[dict[str, str]] = []
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells == list(HEADER):
            continue
        if cells and set(cells[0]) <= {"-", " "}:
            continue
        if len(cells) != 5:
            continue
        rows.append(dict(zip(HEADER, cells, strict=True)))
    return rows


def _artifact_candidates(cell: str) -> list[str]:
    found = [m.group(1) or m.group(0) for m in TOKEN_RE.finditer(cell)]
    return [item.rstrip(").,;") for item in found]


def test_gated_table_has_required_columns_and_ids() -> None:
    src = REGISTRY.read_text(encoding="utf-8")
    assert "| claim_id | текст | артефакт-источник | команда воспроизведения | статус |" in src
    rows = parse_gated_rows(src)
    ids = [row["claim_id"] for row in rows]
    assert ids == ["V1", "V2", "V3", "B1", "B2", "B3", "B4", "B5", "B7", "P6", "P8", "M6", "T1"]
    for row in rows:
        assert row["статус"].split()[0] in {"verified", "assumption", "target", "withdrawn"}
        assert row["текст"]
        assert row["артефакт-источник"]
        assert row["команда воспроизведения"]


def test_gated_artifacts_exist_for_repo_paths() -> None:
    src = REGISTRY.read_text(encoding="utf-8")
    missing: list[str] = []
    for row in parse_gated_rows(src):
        for token in _artifact_candidates(row["артефакт-источник"]):
            if token.startswith("http"):
                continue
            path = ROOT / token.replace("\\", "/")
            if not path.exists():
                missing.append(f"{row['claim_id']}: {token}")
    assert missing == []


def test_readme_tags_gated_ids() -> None:
    readme = README.read_text(encoding="utf-8")
    rows = parse_gated_rows(REGISTRY.read_text(encoding="utf-8"))
    readme_ids = {"V1", "V2", "V3", "B1", "B2", "B3", "B4", "B5", "T1", "P6"}
    for row in rows:
        cid = row["claim_id"]
        if cid in readme_ids:
            assert cid in readme, cid


def _numbers_from_claim(text: str) -> list[str]:
    """Distinctive quantities: two or more digits, not leading-zero junk."""
    out: list[str] = []
    for match in re.finditer(r"\b\d{2,}(?:\.\d+)?\b", text):
        token = match.group(0)
        if set(token) <= {"0", "."}:
            continue
        out.append(token)
    return out


def test_numeric_claims_in_readme_carry_claim_id() -> None:
    rows = parse_gated_rows(REGISTRY.read_text(encoding="utf-8"))
    readme = README.read_text(encoding="utf-8")
    freq: dict[str, int] = {}
    for row in rows:
        for number in _numbers_from_claim(row["текст"]):
            freq[number] = freq.get(number, 0) + 1
    missing: list[str] = []
    for row in rows:
        if not row["статус"].startswith(("verified", "assumption")):
            continue
        cid = row["claim_id"]
        for number in _numbers_from_claim(row["текст"]):
            if number in {"2013", "2017", "2026", "16290", "58048"}:
                continue
            if freq.get(number, 0) > 1:
                continue
            if number in readme and cid not in readme:
                missing.append(f"README has {number} without {cid}")
    assert missing == []
