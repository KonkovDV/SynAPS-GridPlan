"""Stable hashing and plan fingerprints (no Python built-in hash())."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_digest(*parts: str, length: int = 16) -> str:
    """SHA-256 hex digest of joined parts — process-stable."""

    payload = "\u001f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


def stable_int(*parts: str, modulo: int) -> int:
    """Deterministic non-negative integer in ``[0, modulo)``."""

    if modulo <= 0:
        raise ValueError("modulo must be positive")
    digest = hashlib.sha256("\u001f".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % modulo


def canonical_json(data: Any) -> str:
    """Canonical JSON for hashing (sorted keys, compact separators)."""

    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint_payload(data: Any) -> str:
    """SHA-256 of canonical JSON (full hex)."""

    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
