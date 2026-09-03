# World practice (and what this repo actually implements)

GridPlan is the **combinatorial** layer of outage-window ТОиР: crews,
qualifications, agreed outage windows, one stock unit per listed spare,
linear predecessor chains, frozen ПЛ rows, and explicit “these two assets
must not be out together” bans. An independent checker (Python and Rust)
rejects a plan that breaks those rules.

Electrical security analysis is **out of scope**. Do not read this file as N-1,
SAIDI, live EL5, INFIMUM, or a plant pilot. ISO 16290 TRL 4, synthetic
fixtures. Machine-readable twin: `src/synaps_gridplan/practice.py`
(`synaps-gridplan practice`).

The architecture matches a split that utilities already use: **formalizable
resource/window rules in a scheduler**, **power-flow / CSA in another
system**. GridPlan is the first box only.

## Mapping

| Source | Year | What they do | What we take | What we refuse |
| --- | ---: | --- | --- | --- |
| Hydro-Québec TMS (Popovic et al., CP 2022) | 2022 | CP for constraints that specialists can write down; black-box power-flow simulator for the rest. Live experiments on five HQ interfaces, 200+ assets, 300 withdrawal requests. | Independent checker + formalizable crew/window/mutex/freeze. | Their simulator, annual transmission TMS, 10-year what-if. |
| Hydro-Québec follow-up (Barral et al., CPAIOR 2024) | 2024 | Active constraint acquisition of transit-power limits from HQ’s simulator, then inject into CP. | Confirms the same two-layer split. | Learning unformalized power-flow constraints. |
| Tang et al., *Energies* 18(20):5454 | 2025 | Monthly outage scheduling with DRL; objectives include power-flow convergence, voltage, losses. Constraints include simultaneous outage, mutex, maintenance windows. IEEE-39 / IEEE-118. | The **combinatorial** constraint families (windows, pairwise bans, exclusivity). | Power flow, voltage/loss KPIs, Shapley rewards, RL. |
| Goel & Meisel, EJOR 231:210–228 | 2013 | German DSO: disconnect → work → reconnect; downtime is that hull. LNS + MIP, worker routing. | Occupancy of a precedence-connected interruption chain is `[first start, last end]`. | Geographic technician routing / LNS as the product. |
| Froger et al., EJOR 251:695–706 | 2016 | Review of electricity maintenance scheduling (generation, transmission, distribution). | We sit in crew/time-window maintenance, not unit commitment. | Generator UC, market bids. |
| Li et al., arXiv:2502.15791 | 2025 | Learning-guided rolling-horizon CP-SAT for long-horizon FJSP; freeze assignments that did not need re-optimization. | Local replan that **keeps frozen ПЛ rows**. | Neural RHO / FJSP machine-fixing. |
| ENTSO-E CIM Outage Business Process | — | OPA proposes availability; TSO assesses **outage planning incompatibilities** (OPI). Detecting OPI is not proposing the plan. | Fail-closed checker ≈ “incompatibility detection ≠ search”. Declared pair bans are customer-stated incompatibilities. | CSA/OPI from a common grid model. |
| Synergrid / Elia design note (2026-05-06) | 2026 | SOGL outage-planning coordination extended to 1–25 MW production/storage and TSO-connected demand. Availability plans, freeze of coordinated slots. | Frozen ПЛ rows as agreed-slot freeze. | Becoming an Outage Planning Agent under SOGL. |
| Nordic RCC OPC | 2025 | Y-1 baseline (before 1 Dec), then W-4 and W-1 updates among TSOs. | Freeze of an agreed slot after coordination. | Regional OPC among TSOs. |
| Hexaly + PosAm at ČEZ Distribuce | — | Daily field workforce: qualifications, geography, live dispatch. Different product class (FSM), not monthly outage-window ТОиР. | FIFO EDD / GREED as **transparent OR baselines** for *this* contour. | Claiming ČEZ as a GridPlan deployment; Hexaly as the engine. |
| Uptime Institute Tier III | 2021 | Concurrent maintainability: take one path out of service without dropping IT load. | Declared dual-feed mutex (`dual-feed-hall`). | Tier certificate, UPS/cooling, fault tolerance. |
| MMTS-9 / M9 public outage (18 Aug 2026) | 2026 | Utility loss at a traffic-exchange colocation; cascade through MSK-IX is topology/traffic. | Same mutex family; DGU/UPS jobs may stay online. | Reconstructing M9, modelling IX failover, naming live campuses. |

## Papers (verified URLs)

- Popovic et al., CP 2022: <https://doi.org/10.4230/LIPIcs.CP.2022.34>
- Barral et al., CPAIOR 2024 slides: <https://www.easychair.org/smart-slide/slide/BxT6>
- Tang et al., Energies 2025, 18(20), 5454: <https://doi.org/10.3390/en18205454>
- Goel & Meisel, EJOR 2013: <https://doi.org/10.1016/j.ejor.2013.05.021>
- Froger et al., EJOR 2016: <https://doi.org/10.1016/j.ejor.2015.08.045>
- Li et al., arXiv:2502.15791: <https://arxiv.org/abs/2502.15791>

## Operator processes

- ENTSO-E outage business process (OPI): <https://eepublicdownloads.entsoe.eu/clean-documents/EDI/Library/cim_based/Outage_Business_Process_and_Format_V1R1.pdf>
- Synergrid/Elia OPC design note (2026-05-06): <https://www.synergrid.be/images/downloads/PDG/iCAROS/20260506_Outage_Planning_Design_Note_FINAL.pdf>
- Nordic RCC OPC (Y-1 / W-4 / W-1): <https://nordic-rcc.net/services/outage-planning-coordination-opc/>

## Industry case, with the honest boundary

Hexaly’s public ČEZ Distribuce write-up is **field technician routing and
daily dispatch** (PosAm FSM). ČEZ is a real DSO; the case is real; it is
**not** this product’s core (monthly crew × outage-window × ЗИП × freeze).
Citing it as “GridPlan in production at ČEZ” would be false.

Hydro-Québec TMS is the closest **architectural** cousin: CP for what can
be written as constraints, a separate simulator for what cannot. GridPlan
ships layer 1 and an independent checker. It does not ship layer 2.

## Dual-feed hall (concurrent maintainability)

Uptime Institute Tier III: each utility/distribution path can be taken out
of service on a **planned** basis without dropping the IT load. That is a
declared mutex on two paths — the same combinatorial family as
`SIMULTANEOUS_OUTAGE_BAN`. GridPlan ships that mutex on a synthetic hall
(`synthesize --mode dual-feed-hall`). It does **not** certify a Tier, model
UPS/cooling, or prove fault tolerance (Tier IV).

Public incident class, 18 Aug 2026: utility loss at MMTS-9 / M9 (MSK-IX
colocation) after a substation event on Vavilova, reported by open news
(Meduza, Habr). The cascade through an exchange is **traffic and topology**,
out of scope here. The fixture is not a reconstruction of M9, not Yandex/VK
campuses, not a siting study for «ЦОД у ТЭС», and not PVO.

- Uptime Tier III: <https://journal.uptimeinstitute.com/explaining-uptime-institutes-tier-classification-system/>
- Meduza, 18 Aug 2026: <https://meduza.io/news/2026/08/18/polzovateli-po-vsey-rossii-pozhalovalis-na-rabotu-runeta-veroyatnaya-prichina-sboya-avariya-na-krupnom-uzle-svyazi-v-moskve-v-etom-rayone-otklyuchilsya-svet>

## What this release changed in code

- Plan JSON and markdown reports carry `practice.layer` /
  `electrical_security=out_of_scope` and the applicability list from
  `practice.py` (single source).
- `SIMULTANEOUS_OUTAGE_BAN` occupancy stays the Goel hull; comments cite
  the verified EJOR DOI (`10.1016/j.ejor.2013.05.021`), not a guessed one.
- CLI: `python -m synaps_gridplan practice`.
- Synthetic dual-feed hall (`dual-feed-hall`): concurrent-maintainability
  mutex on two utility paths. Not M9, not a live campus.

No power-flow, no RL, no Hexaly, no SOGL OPA adapter. Those belong in
other systems — the same split Hydro-Québec documents.
