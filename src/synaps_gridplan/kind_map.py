"""Canonical GridPlan-layer violation kinds: Python checker vs native Rust.

Engine (SynAPS ``FeasibilityChecker``) kinds stay Python-only and are not
compared in the native parity guard.
"""

from __future__ import annotations

from collections import Counter

# Rust name → Python name (domain layer only).
RUST_TO_PYTHON_KIND: dict[str, str] = {
    "UNKNOWN_JOB": "UNKNOWN_OPERATION",
    "DUPLICATE_JOB_ASSIGNMENT": "DUPLICATE_ASSIGNMENT",
}


def canonicalize_rust_kind(kind: str) -> str:
    """Map a native checker kind onto the Python GridPlan name."""

    return RUST_TO_PYTHON_KIND.get(kind, kind)


def kind_multiset(kinds: list[str]) -> Counter[str]:
    return Counter(kinds)
