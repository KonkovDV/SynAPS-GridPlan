# synaps-gridplan-rs

Native GridPlan contour in Rust: deterministic FIFO, the same domain checks
as Python, fingerprints, synthetic feeder. Optional bridge to Python GREED.

Version **0.1.4**. GREED is not implemented in this crate.

## Scope

| Capability | Status |
| --- | --- |
| JSON problem I/O (`gridplan.v1`) | shipped |
| Calendar FIFO (earliest due) | shipped |
| Post-checks: outage / frozen / ЗИП / quals / precedence / short duration | shipped |
| Fingerprints (`stable_int` / SHA-256) parity with Python | shipped |
| uuid5 synthetic IDs parity with Python | shipped |
| `synthesize --mode gres-block` | Python package only |
| `synthesize --mode dual-feed-hall` | Python package only |
| Native FIFO on a Python-emitted `gres-block` JSON | checks run; no native GRES synthesizer |
| GREED / CPSAT / LBBD | Python SynAPS-GridPlan |
| Customer deployment | not claimed |

## Build

```bash
cd native/synaps-gridplan-rs
cargo test
cargo build --release
```

## CLI

Verified contest demo (Python, GREED checks clean):

```bash
# from repo root
python benchmark/jury_benchmark.py
```

Native FIFO on the default small seed is the fail-closed example:

```bash
cargo run -- synthesize --mode small --seed 42 -o feeder.json
cargo run -- solve feeder.json --engine fifo -o plan.json
# exit 2 = fail-closed (FIFO on this seed is not verified). Exit 0 = checked plan.
cargo run -- report plan.json --format markdown
cargo run -- check feeder.json plan.json
# optional, requires `pip install -e .` at repo root:
cargo run -- solve feeder.json --engine greed -o greed.json
```

Exit **2** means the checker rejected the plan. It is not a build failure.
Verified contest demo: `python benchmark/jury_benchmark.py` at repo root.

`check` accepts native `PlanResult` **or** Python CLI solve JSON
(`outcome.id_map` + `schedule.assignments` with `operation_id`).

## Kind names (GridPlan layer)

Rust does not reimplement the SynAPS engine checker. Domain kinds match
except two aliases:

| Python | Rust |
| --- | --- |
| `UNKNOWN_OPERATION` | `UNKNOWN_JOB` |
| `DUPLICATE_ASSIGNMENT` | `DUPLICATE_JOB_ASSIGNMENT` |

Other domain kinds (`ASSET_OVERLAP`, `CREW_OVERLAP`, `OUTAGE_WINDOW_*`,
`FROZEN_ASSIGNMENT_CONFLICT`, …) are identical strings. Engine-only kinds
(`MACHINE_OVERLAP`, `DURATION_BELOW_GRAIN`, …) stay in Python.

Parity guard: `tests/test_native_parity.py` (needs `cargo` on PATH).

## License

MIT — same as SynAPS-GridPlan.
