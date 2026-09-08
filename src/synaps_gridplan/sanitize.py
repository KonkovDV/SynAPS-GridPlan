"""Flatten untrusted strings interpolated into Markdown reports.

This is not a general HTML sanitizer: there is no tag allow-list, no CSS
filter, and no URL rewriting. Interpolated values are forced onto one visual
line, backticks cannot break inline code, and angle brackets cannot start
markup. CSV formula prefixing stays in the CSV renderer.
"""

from __future__ import annotations

from typing import Any


def display_text(value: Any) -> str:
    """Single-line Markdown/HTML-safe interpolation of a report field."""

    return (
        str(value)
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("`", "'")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
