"""World-practice alignment: citations and an honest mapping to this contour.

Companion to ``PRACTICE.md``. Reports, plan metadata, and ``synaps-gridplan
practice`` read this module so the literature table cannot drift from the
code comments. Electrical security analysis is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PRACTICE_LAYER = "combinatorial_crew_window_mutex_freeze"
ELECTRICAL_SECURITY = "out_of_scope"

# Positive capability claims that must not appear in this module's mapping
# strings. "Not N-1" in prose docs is allowed; "we run N-1" is not.
OVERCLAIM_DENYLIST: tuple[str, ...] = (
    "reduces saidi",
    "saidi optimisation",
    "n-1 load-flow",
    "live el5",
    "infimum",
    "plant pilot",
    "industrial proof",
    "hydro-québec production",
)


@dataclass(frozen=True)
class PracticeRef:
    key: str
    year: int
    citation: str
    url: str
    kind: str  # paper | operator | industry | analogue


@dataclass(frozen=True)
class PracticeMap:
    key: str
    we_implement: str
    we_do_not: str


REFS: tuple[PracticeRef, ...] = (
    PracticeRef(
        key="popovic_cp_2022",
        year=2022,
        citation=(
            "Popovic, Côté, Gaha, Nguewouo, Cappart. Scheduling the Equipment "
            "Maintenance of an Electric Power Transmission Network Using "
            "Constraint Programming. CP 2022, LIPIcs vol. 235, article 34."
        ),
        url="https://doi.org/10.4230/LIPIcs.CP.2022.34",
        kind="paper",
    ),
    PracticeRef(
        key="barral_cpaior_2024",
        year=2024,
        citation=(
            "Barral, Gaha, Dems, Côté, Nguewouo, Cappart. Acquiring Constraints "
            "for a Non-Linear Transmission Maintenance Scheduling Problem. "
            "CPAIOR 2024 (Hydro-Québec transit-power constraint acquisition)."
        ),
        url="https://www.easychair.org/smart-slide/slide/BxT6",
        kind="paper",
    ),
    PracticeRef(
        key="tang_energies_2025",
        year=2025,
        citation=(
            "Tang, Mao, Lv, Cai, Ding. Monthly Power Outage Maintenance "
            "Scheduling for Power Grids Based on Interpretable Reinforcement "
            "Learning. Energies 18(20):5454."
        ),
        url="https://doi.org/10.3390/en18205454",
        kind="paper",
    ),
    PracticeRef(
        key="goel_meisel_2013",
        year=2013,
        citation=(
            "Goel, Meisel. Workforce routing and scheduling for electricity "
            "network maintenance with downtime minimization. EJOR 231(1):210–228."
        ),
        url="https://doi.org/10.1016/j.ejor.2013.05.021",
        kind="paper",
    ),
    PracticeRef(
        key="froger_ejor_2016",
        year=2016,
        citation=(
            "Froger, Gendreau, Mendoza, Pinson, Rousseau. Maintenance scheduling "
            "in the electricity industry: a literature review. EJOR 251(3):695–706."
        ),
        url="https://doi.org/10.1016/j.ejor.2015.08.045",
        kind="paper",
    ),
    PracticeRef(
        key="li_arxiv_2502",
        year=2025,
        citation=(
            "Li, Ouyang, Ma, Wu. Learning-Guided Rolling Horizon Optimization "
            "for Long-Horizon Flexible Job-Shop Scheduling. arXiv:2502.15791."
        ),
        url="https://arxiv.org/abs/2502.15791",
        kind="analogue",
    ),
    PracticeRef(
        key="entsoe_opi",
        year=2016,
        citation=(
            "ENTSO-E. Outage Business Process and Format (CIM). Outage planning "
            "incompatibilities (OPI) vs availability-plan proposal."
        ),
        url=(
            "https://eepublicdownloads.entsoe.eu/clean-documents/EDI/Library/"
            "cim_based/Outage_Business_Process_and_Format_V1R1.pdf"
        ),
        kind="operator",
    ),
    PracticeRef(
        key="synergrid_sogl_2026",
        year=2026,
        citation=(
            "Synergrid / Elia. Design note for outage planning coordination "
            "for 1–25 MW units (SOGL OPC extension). 2026-05-06."
        ),
        url=(
            "https://www.synergrid.be/images/downloads/PDG/iCAROS/"
            "20260506_Outage_Planning_Design_Note_FINAL.pdf"
        ),
        kind="operator",
    ),
    PracticeRef(
        key="nordic_rcc_opc",
        year=2025,
        citation=(
            "Nordic RCC. Outage Planning Coordination: Y-1, W-4, W-1 horizons (SOGL art. 82–103)."
        ),
        url="https://nordic-rcc.net/services/outage-planning-coordination-opc/",
        kind="operator",
    ),
    PracticeRef(
        key="hexaly_cez",
        year=2024,
        citation=(
            "Hexaly / PosAm. Field workforce planning at ČEZ Distribuce "
            "(daily technician routing and dispatch). Different problem class."
        ),
        url=(
            "https://www.hexaly.com/customers/"
            "advanced-field-workforce-planning-at-cez-distribuce-with-hexaly"
        ),
        kind="industry",
    ),
)

ALIGNMENT: tuple[PracticeMap, ...] = (
    PracticeMap(
        key="popovic_cp_2022",
        we_implement=(
            "Layer 1 of TMS: formalizable crew, window, freeze, and declared "
            "mutex checks with an independent checker."
        ),
        we_do_not=(
            "Layer 2 black-box power-flow simulator used at Hydro-Québec; "
            "annual TMS for 200+ transmission assets."
        ),
    ),
    PracticeMap(
        key="barral_cpaior_2024",
        we_implement="Same split: combinatorial constraints stay in the CP/checker.",
        we_do_not=(
            "Active constraint acquisition of transit-power limits from a network simulator."
        ),
    ),
    PracticeMap(
        key="tang_energies_2025",
        we_implement=(
            "Combinatorial families they list: outage windows, pairwise "
            "simultaneous/mutex bans, asset exclusivity."
        ),
        we_do_not=(
            "IEEE-39/118 power flow, voltage-violation objectives, Shapley "
            "reward decomposition, or a DRL agent."
        ),
    ),
    PracticeMap(
        key="goel_meisel_2013",
        we_implement=(
            "Interruption occupancy is the hull of a precedence-connected "
            "chain (disconnect → reconnect), not the union of task intervals."
        ),
        we_do_not=("Multi-site worker routing / LNS for a German DSO field force."),
    ),
    PracticeMap(
        key="froger_ejor_2016",
        we_implement=(
            "Crew- and window-constrained maintenance scheduling with a fail-closed checker."
        ),
        we_do_not="Generator maintenance with unit commitment or market bids.",
    ),
    PracticeMap(
        key="li_arxiv_2502",
        we_implement=(
            "Local replan that keeps frozen ПЛ rows (rolling repair of a disruption set)."
        ),
        we_do_not=(
            "Learning-guided RHO that fixes FJSP machine assignments across overlapping horizons."
        ),
    ),
    PracticeMap(
        key="entsoe_opi",
        we_implement=(
            "Declared pairwise bans are an incompatibility the checker can prove or reject."
        ),
        we_do_not=("TSO OPI from a security analysis / common grid model (CSA class)."),
    ),
    PracticeMap(
        key="synergrid_sogl_2026",
        we_implement="Availability-plan freeze of agreed slots (frozen ПЛ rows).",
        we_do_not="SOGL Outage Planning Agent process for 1–25 MW units.",
    ),
    PracticeMap(
        key="nordic_rcc_opc",
        we_implement="A frozen row is a locked agreed slot, similar in spirit to a freeze.",
        we_do_not="Regional Y-1 / W-4 / W-1 OPC among TSOs.",
    ),
    PracticeMap(
        key="hexaly_cez",
        we_implement=(
            "FIFO earliest-due-date and GREED as transparent OR baselines "
            "for the outage-window contour."
        ),
        we_do_not=(
            "Daily field-service technician routing, SLA dispatch, or Hexaly as the search engine."
        ),
    ),
)

APPLICABILITY_LIMITS: tuple[str, ...] = (
    "Synthetic/experiment results are not industrial proof.",
    "Risk metrics are advisory proxies, not failure certificates.",
    "Heuristic FEASIBLE does not imply OPTIMAL.",
    "ЗИП consumable checks are GridPlan post-checks (SynAPS aux = concurrent pool).",
    (
        "Layer is combinatorial crew/window/mutex/freeze only; power-flow, "
        "N-1 criterion, and SAIDI are out of scope."
    ),
    "SIMULTANEOUS_OUTAGE_BAN is a customer-declared pair, not CSA/OPI from load-flow.",
    "Frozen ПЛ rows freeze agreed slots; they are not a year-ahead OPC process.",
    ("FIFO/GREED are OR baselines for this contour, not a field FSM (ČEZ/Hexaly class)."),
)


def practice_snapshot() -> dict[str, Any]:
    """Compact blob attached to every PlanOutcome (not the full bibliography)."""

    return {
        "layer": PRACTICE_LAYER,
        "electrical_security": ELECTRICAL_SECURITY,
        "ref_keys": [r.key for r in REFS],
    }


def applicability_limits() -> list[str]:
    return list(APPLICABILITY_LIMITS)


def render_practice_markdown() -> str:
    """Human table for the CLI and for tests that lock citation strings."""

    lines = [
        "# SynAPS-GridPlan practice alignment",
        "",
        f"- layer: `{PRACTICE_LAYER}`",
        f"- electrical_security: `{ELECTRICAL_SECURITY}`",
        "",
        "Full narrative: `PRACTICE.md`. This is not a plant pilot.",
        "",
        "## Citations",
        "",
        "| Key | Year | Kind | Citation |",
        "| --- | ---: | --- | --- |",
    ]
    for ref in REFS:
        cite = ref.citation.replace("|", "/")
        lines.append(f"| `{ref.key}` | {ref.year} | {ref.kind} | {cite} |")
    lines.extend(["", "## Mapping", ""])
    by_key = {m.key: m for m in ALIGNMENT}
    for ref in REFS:
        row = by_key[ref.key]
        lines.extend(
            [
                f"### `{ref.key}` ({ref.year})",
                "",
                f"- url: {ref.url}",
                f"- we implement: {row.we_implement}",
                f"- we do not: {row.we_do_not}",
                "",
            ]
        )
    lines.extend(["## Applicability limits", ""])
    for item in APPLICABILITY_LIMITS:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
