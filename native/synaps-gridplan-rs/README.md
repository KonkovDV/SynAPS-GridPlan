# synaps-gridplan-rs

Native GridPlan contour in Rust: deterministic FIFO, the same domain checks
as Python, fingerprints, synthetic feeder. Optional bridge to Python GREED.

Version **0.1.1**. GREED is not implemented in this crate.

## Scope

| Capability | Status |
| --- | --- |
| JSON problem I/O (`gridplan.v1`) | shipped |
| Calendar FIFO (earliest due) | shipped |
| Post-checks: outage / frozen / ЗИП / quals / precedence / short duration | shipped |
| Fingerprints (`stable_int` / SHA-256) parity with Python | shipped |
| uuid5 synthetic IDs parity with Python | shipped |
| `synthesize --mode gres-block` | Python package only |
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

```bash
cargo run -- synthesize --mode small --seed 42 -o feeder.json
cargo run -- solve feeder.json --engine fifo -o plan.json
cargo run -- report plan.json --format markdown
cargo run -- check feeder.json plan.json
# optional, requires `pip install -e .` at repo root:
cargo run -- solve feeder.json --engine greed -o greed.json
```

## License

MIT — same as SynAPS-GridPlan.
