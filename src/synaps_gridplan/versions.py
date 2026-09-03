"""Package / upstream version pins (explicit, reproducible)."""

from __future__ import annotations

GRIDPLAN_VERSION = "0.1.3"

# ISO 16290 TRL 4: lab fixtures and automated checks. Not a plant pilot.
ISO16290_TRL = 4

# SynAPS commit this GridPlan release is validated against.
# Bump deliberately when upgrading the engine; never float on branch tips.
SYNAPS_COMMIT = "6178c93b705ff58be21fa74a98651883a2da1169"
SYNAPS_REPO = "https://github.com/KonkovDV/SynAPS"
