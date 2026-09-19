"""Extract comparable text from the committed submission pptx."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "SynAPS_GridPlan.pptx"
OUT = ROOT / "docs" / "DECK_TEXT.txt"
A_T = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
CSLD = "{http://schemas.openxmlformats.org/presentationml/2006/main}cSld"
DESCRIBE_RE = re.compile(r"v\d+\.\d+\.\d+(?:-\d+-g[0-9a-f]+)?(?:-dirty)?")


def slide_blobs(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with zipfile.ZipFile(path) as zf:
        names = sorted(
            (n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
            key=lambda n: int(re.search(r"(\d+)", n).group(1)),
        )
        for name in names:
            root = ET.fromstring(zf.read(name))
            title = ""
            for node in root.iter(CSLD):
                title = node.attrib.get("name", "")
            text = " ".join(t.text or "" for t in root.iter(A_T))
            rows.append((title, text))
    return rows


def core_fields(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("docProps/core.xml"))

    def _t(tag: str) -> str:
        node = root.find(tag)
        return (node.text or "").strip() if node is not None else ""

    company = ""
    try:
        with zipfile.ZipFile(path) as zf:
            app = zf.read("docProps/app.xml").decode("utf-8")
        m = re.search(r"<Company>([^<]*)</Company>", app)
        company = m.group(1) if m else ""
    except KeyError:
        company = ""
    return {
        "title": _t("{http://purl.org/dc/elements/1.1/}title"),
        "creator": _t("{http://purl.org/dc/elements/1.1/}creator"),
        "last_modified_by": _t(
            "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastModifiedBy"
        ),
        "company": company,
    }


def render(path: Path) -> str:
    core = core_fields(path)
    lines = [
        f"title={core['title']}",
        f"creator={core['creator']}",
        f"last_modified_by={core['last_modified_by']}",
        f"company={core['company']}",
        "",
    ]
    for i, (title, text) in enumerate(slide_blobs(path), 1):
        blob = DESCRIBE_RE.sub("{git_describe}", f"{title} | {text}")
        lines.append(f"SLIDE {i}: {blob}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--deck", type=Path, default=DECK)
    args = parser.parse_args()
    text = render(args.deck)
    if args.write:
        OUT.write_text(text, encoding="utf-8", newline="\n")
    if args.check:
        committed = OUT.read_text(encoding="utf-8")
        if committed != text:
            sys.stderr.write("docs/DECK_TEXT.txt does not match extracted pptx text\n")
            return 1
    if not args.write and not args.check:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
