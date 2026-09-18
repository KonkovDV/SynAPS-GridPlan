"""Build benchmark/results/deck_facts.json from jury_report.md and versions.py."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from repo_describe import git_describe  # noqa: E402
from synaps_gridplan.versions import GRIDPLAN_VERSION, ISO16290_TRL, SYNAPS_COMMIT  # noqa: E402

JURY = ROOT / "benchmark" / "results" / "jury_report.md"
PILOT = ROOT / "docs" / "PILOT_ONEPAGER.md"
TEST_COUNT = ROOT / "docs" / "TEST_COUNT.txt"
OUT = ROOT / "benchmark" / "results" / "deck_facts.json"


def _int(pattern: str, text: str) -> int:
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"no match for {pattern!r}")
    return int(match.group(1))


def parse_jury(text: str) -> dict[str, object]:
    jobs = _int(r"\*\*Состав:\*\*\s+(\d+) работ", text)
    crews = _int(r"Состав:\*\*\s+\d+ работ, (\d+) бригад", text)
    assets = _int(r"бригад, (\d+) активов", text)
    windows = _int(r"активов,\s*(\d+) окон", text)
    fifo_hard = _int(r"Жёстких нарушений \| \*\*(\d+)\*\* \| \*\*\d+\*\*", text)
    greed_hard = _int(r"Жёстких нарушений \| \*\*\d+\*\* \| \*\*(\d+)\*\*", text)
    fifo_check = re.search(r"\| Проверка \| (нет|да) \| (нет|да) \|", text)
    if fifo_check is None:
        raise ValueError("FIFO/GREED checker row missing")
    freeze = _int(r"Конфликтов с заморозкой \| \*\*(\d+)\*\*", text)
    moved = _int(r"Слотов изменено \| (\d+)", text)
    greed_sha = re.search(r"Отпечаток \(SHA-256\) \| `([0-9a-f]{16})", text)
    if greed_sha is None:
        raise ValueError("GREED fingerprint missing")
    d_block = text.split("## D.", 1)
    if len(d_block) < 2:
        raise ValueError("jury_report.md has no section D")
    d_text = d_block[1]
    cpsat_status = re.search(r"\| status \| `?(\w+)`? \|", d_text)
    cpsat_hard = _int(r"Жёстких нарушений \| (\d+)", d_text)
    cpsat_verified = re.search(r"verified_feasible \| (да|нет)", d_text)
    if cpsat_status is None or cpsat_verified is None:
        raise ValueError("CP-SAT status/verified missing")
    return {
        "jobs": jobs,
        "crews": crews,
        "assets": assets,
        "windows": windows,
        "fifo_hard": fifo_hard,
        "greed_hard": greed_hard,
        "fifo_checker": fifo_check.group(1),
        "greed_checker": fifo_check.group(2),
        "freeze_conflicts": freeze,
        "slots_moved": moved,
        "greed_sha16": greed_sha.group(1),
        "cpsat_status": cpsat_status.group(1),
        "cpsat_hard": cpsat_hard,
        "cpsat_verified": cpsat_verified.group(1),
    }


def parse_pilot_budget(text: str) -> str:
    match = re.search(
        r"данные (\d+); solver/checker (\d+); интеграция (\d+); "
        r"ИБ (\d+); пилот (\d+); IP/резерв (\d+)",
        text,
    )
    if match is None:
        raise ValueError("PILOT_ONEPAGER.md budget line missing")
    parts = [int(g) for g in match.groups()]
    total = sum(parts)
    if total != 1500:
        raise ValueError(f"budget parts {parts} sum to {total}, not 1500")
    return f"{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}/{parts[4]}/{parts[5]} = {total}"


def parse_test_count(text: str) -> int:
    match = re.search(r"^collected=(\d+)\s*$", text, re.M)
    if match is None:
        raise ValueError("docs/TEST_COUNT.txt missing collected=")
    return int(match.group(1))


def build_facts() -> dict[str, object]:
    jury = parse_jury(JURY.read_text(encoding="utf-8"))
    return {
        "gridplan_version": GRIDPLAN_VERSION,
        "iso16290_trl": ISO16290_TRL,
        "trl_sentence": "TRL 4 по ISO 16290: лабораторные фикстуры, не пилот на предприятии",
        "synaps_commit": SYNAPS_COMMIT,
        "synaps_commit12": SYNAPS_COMMIT[:12],
        "git_describe": git_describe(),
        "author": "Коньков Д.В.",
        "company": "SynAPS",
        "budget": parse_pilot_budget(PILOT.read_text(encoding="utf-8")),
        "budget_status": "assumption",
        "pytest_collected": parse_test_count(TEST_COUNT.read_text(encoding="utf-8")),
        "jury": jury,
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = build_facts()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(str(OUT) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
