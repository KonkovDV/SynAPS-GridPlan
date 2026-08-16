"""Package / upstream version pins (explicit, reproducible)."""

from __future__ import annotations

GRIDPLAN_VERSION = "0.1.1"

# ISO 16290 TRL 4: lab fixtures and automated checks. Not a plant pilot.
ISO16290_TRL = 4

# SynAPS commit this GridPlan release is validated against.
# Bump deliberately when upgrading the engine; never float on branch tips.
SYNAPS_COMMIT = "bd09d13561b3bd690845d07546def59b4521b16c"
SYNAPS_REPO = "https://github.com/KonkovDV/SynAPS"
