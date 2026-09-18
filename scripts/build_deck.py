"""Rebuild SynAPS_v8_Evidence.pptx from jury_report.md + versions.py + git describe."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "SynAPS_v8_Evidence.pptx"
SLIDE_TITLES = (
    "01 Title",
    "02 Thesis",
    "03 Product",
    "04 Evidence FIFO vs GREED vs CPSAT",
    "05 Limits",
    "06 Customer",
    "07 UGT",
    "08 Pilot",
    "09 Budget assumption",
    "10 Team",
    "11 Ask",
    "12 Repro",
)


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _patch_core(data: bytes, *, author: str, company: str) -> bytes:
    del company
    text = data.decode("utf-8")
    text = re.sub(r"<dc:creator>[^<]*</dc:creator>", f"<dc:creator>{author}</dc:creator>", text)
    text = re.sub(
        r"<cp:lastModifiedBy>[^<]*</cp:lastModifiedBy>",
        f"<cp:lastModifiedBy>{author}</cp:lastModifiedBy>",
        text,
    )
    return text.encode("utf-8")


def _patch_app(data: bytes, *, company: str) -> bytes:
    text = data.decode("utf-8")
    if "<Company>" in text:
        text = re.sub(r"<Company>[^<]*</Company>", f"<Company>{company}</Company>", text)
    else:
        text = text.replace("</Properties>", f"<Company>{company}</Company></Properties>")
    return text.encode("utf-8")


def _patch_slide(data: bytes, title: str) -> bytes:
    text = data.decode("utf-8")
    text, n = re.subn(
        r"<p:cSld(?: name=\"[^\"]*\")?",
        f'<p:cSld name="{title}"',
        text,
        count=1,
    )
    if n != 1:
        raise ValueError("slide is missing p:cSld")
    return text.encode("utf-8")


def stamp_metadata(path: Path, *, author: str, company: str) -> None:
    buf = BytesIO()
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(buf, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            name = item.filename
            if name == "docProps/core.xml":
                data = _patch_core(data, author=author, company=company)
            elif name == "docProps/app.xml":
                data = _patch_app(data, company=company)
            elif re.match(r"ppt/slides/slide\d+\.xml$", name):
                idx = int(re.search(r"(\d+)", name).group(1)) - 1
                data = _patch_slide(data, SLIDE_TITLES[idx])
            zout.writestr(item, data)
    path.write_bytes(buf.getvalue())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-extract", action="store_true")
    args = parser.parse_args()
    if shutil.which("node") is None:
        sys.stderr.write("node is required to rebuild the deck\n")
        return 2
    _run([sys.executable, str(ROOT / "scripts" / "deck_facts.py")])
    _run(["node", str(ROOT / "scripts" / "build_pitch_v8.js")])
    facts = json.loads(
        (ROOT / "benchmark" / "results" / "deck_facts.json").read_text(encoding="utf-8")
    )
    stamp_metadata(DECK, author=str(facts["author"]), company=str(facts["company"]))
    if not args.skip_extract:
        _run([sys.executable, str(ROOT / "scripts" / "extract_deck_text.py"), "--write"])
    sys.stdout.write(str(DECK) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
