# synaps-gridplan-rs

Experimental Rust contour: deterministic FIFO, domain-layer checks with targeted
Python parity, fingerprints and a synthetic feeder. Optional bridge to Python GREED.

Package version **0.1.7**.
GREED and the SynAPS engine checker are not implemented in this crate.

## Scope

| Capability | Boundary |
| --- | --- |
| Domain JSON I/O | Version gate accepts `gridplan.v1` / `gridplan.v2`; this is not a full v2-schema compatibility guarantee |
| Calendar FIFO | Experimental candidate generator, not an optimizer or routing engine |
| Domain checks | Outage / frozen / stock / qualifications / precedence / duration / capacity / calendars |
| Travel/setup verification | **Not implemented**; nonempty travel matrices prevent native verification for nonempty workloads |
| Fingerprints / synthetic uuid5 IDs | Targeted parity tests, not authenticated provenance |
| `gres-block` / `dual-feed-hall` synthesis | Python package only |
| GREED / CPSAT / LBBD | Python SynAPS-GridPlan |
| Customer deployment / electrical approval | Not claimed |

### Verification contract

`check` reports `verification_scope="gridplan_domain"`,
`verification_origin="independent_recheck"` and `engine_checked=false`.
`domain_verified_feasible` describes the domain checker only. `verified_feasible`
is additionally false when `unsupported_constraints` is nonempty.

Currently, a nonempty `travel_minutes` matrix produces
`unsupported_constraints=["travel_minutes"]` for a nonempty workload, even if its
entries are zero. The crate does not validate the complete routing/setup model.
An empty matrix is the explicit zero-travel assumption; an empty workload remains
vacuously feasible. Do not erase real travel data merely to obtain a green result.
Use the Python/SynAPS path when travel matters.

Native FIFO applies the same verification boundary. For validated inputs, it
records its scope and unsupported constraints in metadata. A zero domain-violation
count alone is not proof that all requested constraints were checked. The low-level
`check_plan` function deliberately remains a domain-only component, not a full
engine checker.

## Build

```bash
cd native/synaps-gridplan-rs
cargo fmt --check
cargo test --locked
cargo clippy --locked -- -D warnings
cargo build --locked --release
```

## CLI

Claim-gated synthetic demo (Python):

```bash
# from repo root
python benchmark/jury_benchmark.py
```

Native FIFO on the default small seed is a fail-closed example:

```bash
cargo run --locked -- synthesize --mode small --seed 42 -o feeder.json
cargo run --locked -- solve feeder.json --engine fifo -o plan.json
# A candidate file can exist even when the command returns 2.
cargo run --locked -- report plan.json --format markdown
cargo run --locked -- check feeder.json plan.json
# Optional; requires the Python package and its pinned engine:
cargo run --locked -- solve feeder.json --engine greed -o greed.json
```

Native exit codes (not identical to the Python CLI):

- **0**: command completed; for native `solve` / `check`, the supported verification
  contract also passed. `report` returning 0 means rendering succeeded only.
- **2**: plan not verified, including unsupported travel; also used by Clap for
  argument errors. An unsupported constraint is not itself a proven violation or
  an infeasibility certificate.
- **1**: handled input, parsing or I/O error. A failure before solving may leave no
  output artifact.

`check` accepts native `PlanResult`, a native assignment fragment, or Python CLI
solve JSON (`outcome.id_map` + `schedule.assignments` with `operation_id`).
Mandatory problem freezes cannot be removed or redefined by a plan payload.

## Reports and untrusted files

`report` does not recheck a saved result against its original problem. It rejects
contradictory positive verification flags and non-object metadata, and stamps
`verification_origin="imported_snapshot_not_rechecked"`, including JSON output.
The input file is not changed. This marker is not a signature or authentication.

Markdown and CSV warn that rendering is not a new verification. CSV quotes commas,
quotes and line breaks and prefixes formula-like text (`=`, `+`, `-`, `@`, including
leading whitespace/BOM, and leading tab/CR/LF) with an apostrophe. The protection
also covers metadata/preamble cells. JSON does not add these CSV safety prefixes
to exported strings; typed rendering is not a byte-for-byte JSON round trip.
This is not a general Markdown/HTML sanitizer or a guarantee for every spreadsheet
application's behavior. Interpolated Markdown fields are flattened (newlines,
backticks, angle brackets) so they cannot break surrounding markup.

## Kind names and parity

The test suite compares **domain violation-kind multisets**, not all engine rules
or a formal equivalence of the two implementations. Two established aliases are:

| Python | Rust |
| --- | --- |
| `UNKNOWN_OPERATION` | `UNKNOWN_JOB` |
| `DUPLICATE_ASSIGNMENT` | `DUPLICATE_JOB_ASSIGNMENT` |

Shared domain kinds include `ASSET_OVERLAP`, `CREW_OVERLAP`, `OUTAGE_WINDOW_*` and
`FROZEN_ASSIGNMENT_CONFLICT`. Malformed-input guard kinds are not promised to be
identical across languages. Engine-only kinds (`MACHINE_OVERLAP`,
`DURATION_BELOW_GRAIN`, etc.) stay in Python.

Parity guard: `tests/test_native_parity.py` (needs `cargo` on PATH). It retains the
kind comparison and separately tests the stricter verification/coverage flags.

## License

MIT — same as SynAPS-GridPlan.
