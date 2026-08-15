# Changelog

## 0.1.1 — 2026-08-15

Public contest packet: crew- and window-constrained ТОиР scheduling on SynAPS.

- Assign crews under qualifications, outage windows, spares, precedence,
  frozen ПЛ rows, and explicit simultaneous-outage bans.
- Independent checker (Python and Rust). A plan with hard violations is not
  marked verified. Heuristic GREED/FIFO never report `optimal`.
- Synthetic РЭС «Северный»: GREED verifies, calendar FIFO does not. CP-SAT
  can prove optimal makespan on that instance (pytest marker `slow`).
- Synthetic GRES-block fixture. ISO 16290 TRL 4 (lab). Not a plant pilot.
