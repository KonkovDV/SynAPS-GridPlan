"""Emit a reviewable CycloneDX 1.5 SBOM from the committed lockfiles.

This is a lockfile inventory, not a vulnerability scan and not a guarantee
that every transitive native/C-extension is enumerated the way a full
build-from-source SBOM would be.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from synaps_gridplan.versions import GRIDPLAN_VERSION

ROOT = Path(__file__).resolve().parents[1]
SBOM_DIR = ROOT / "sbom"


def _python_components() -> list[dict[str, object]]:
    lock = (ROOT / "requirements-lock.txt").read_text(encoding="utf-8")
    components: list[dict[str, object]] = []
    for raw in lock.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " @ " in line:
            name, locator = line.split(" @ ", 1)
            pin = locator.rsplit("@", 1)[-1].strip()
            components.append(
                {
                    "type": "library",
                    "name": name.strip(),
                    "version": pin,
                    "purl": f"pkg:generic/{name.strip()}@{pin}",
                    "description": locator.strip(),
                }
            )
            continue
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        components.append(
            {
                "type": "library",
                "name": name.strip(),
                "version": version.strip(),
                "purl": f"pkg:pypi/{name.strip().lower()}@{version.strip()}",
            }
        )
    return components


def _cargo_components() -> list[dict[str, object]]:
    lock = (ROOT / "native" / "synaps-gridplan-rs" / "Cargo.lock").read_text(encoding="utf-8")
    components: list[dict[str, object]] = []
    blocks = re.split(r"\n\[\[package\]\]\n", lock)
    for block in blocks[1:]:
        name_match = re.search(r'^name = "([^"]+)"', block, re.MULTILINE)
        version_match = re.search(r'^version = "([^"]+)"', block, re.MULTILINE)
        if not name_match or not version_match:
            continue
        name, version = name_match.group(1), version_match.group(1)
        source_match = re.search(r'^source = "([^"]+)"', block, re.MULTILINE)
        checksum_match = re.search(r'^checksum = "([^"]+)"', block, re.MULTILINE)
        item: dict[str, object] = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:cargo/{name}@{version}",
        }
        if checksum_match:
            item["hashes"] = [{"alg": "SHA-256", "content": checksum_match.group(1)}]
        if source_match:
            item["description"] = source_match.group(1)
        components.append(item)
    return components


def _bom(name: str, components: list[dict[str, object]]) -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": name,
                "version": GRIDPLAN_VERSION,
            }
        },
        "components": components,
    }


def main() -> int:
    SBOM_DIR.mkdir(parents=True, exist_ok=True)
    python = _bom("synaps-gridplan", _python_components())
    native = _bom("synaps-gridplan-rs", _cargo_components())
    (SBOM_DIR / "cyclonedx-python.json").write_text(
        json.dumps(python, indent=2) + "\n", encoding="utf-8"
    )
    (SBOM_DIR / "cyclonedx-native.json").write_text(
        json.dumps(native, indent=2) + "\n", encoding="utf-8"
    )
    (SBOM_DIR / "README.md").write_text(
        "# SBOM\n\n"
        "CycloneDX 1.5 inventories generated from `requirements-lock.txt` and "
        "`native/synaps-gridplan-rs/Cargo.lock` by `scripts/export_sbom.py`.\n\n"
        "These files are a lockfile inventory for review. They are not a "
        "vulnerability scan, license legal opinion, or complete provenance of "
        "compiled native extensions.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
