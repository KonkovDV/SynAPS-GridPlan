"""Lab quotas for GridPlan I/O. These are DoS/ergonomics caps, not capacity SLAs."""

from __future__ import annotations

# 32 MiB covers the committed synthetic feeders with headroom; not a plant dump size.
MAX_JSON_BYTES = 32 * 1024 * 1024

MAX_ASSETS = 20_000
MAX_CREWS = 5_000
MAX_JOBS = 20_000
MAX_WINDOWS = 50_000
MAX_SPARES = 20_000
MAX_FROZEN = 20_000
MAX_BANS = 50_000
MAX_TRAVEL_ENTRIES = 2_000_000
MAX_CALENDAR_ROWS = 10_000
