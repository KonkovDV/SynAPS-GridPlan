"""Package / upstream version pins (explicit, reproducible)."""

from __future__ import annotations

GRIDPLAN_VERSION = "0.1.1"

# ISO 16290 TRL 4: lab fixtures and automated checks. Not a plant pilot.
ISO16290_TRL = 4

# SynAPS commit this GridPlan release is validated against.
# Bump deliberately when upgrading the engine; never float on branch tips.
SYNAPS_COMMIT = "af7294349fa9a376907b152988ac31b17b3ce6da"
SYNAPS_REPO = "https://github.com/KonkovDV/SynAPS"
