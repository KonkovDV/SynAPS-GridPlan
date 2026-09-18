# Synthetic fixtures

These JSON files are **laboratory** GridPlan documents. Every asset carries
`data_provenance=synthetic`. They are not a live DZO dump, not EL5, and not a
named-station extract.

| File | Role |
| --- | --- |
| `feeder-small.json` / `feeder-medium.json` | Generator snapshots |
| `feeder12.json` / `result12.json` | Seed 12: GREED verified on the small feeder |
| `feeder42.json` / `result42.json` | Seed 42: GREED fail-closed (`ASSET_OVERLAP`) |
| `../scenarios/disruption.json` | Repair/diff smoke for the jury feeder |

Regenerate with `python -m synaps_gridplan synthesize` / `solve`. Committed
copies exist so an auditor can inspect the exact bytes that sat next to the
markdown reports without re-running solvers.
