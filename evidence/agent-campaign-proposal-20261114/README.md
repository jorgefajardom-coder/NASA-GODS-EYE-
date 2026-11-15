# Local per-agent campaign proposal

Source: `c3ec4c1f1515dbc981ba82eed2ab1f54e9586264`, dirty `feat/mission`.
Local review packet, not an approved configuration, hardware sizing result,
mapped route, simulated observation or integrated mission. No publication.

| Artifact | Meaning |
|---|---|
| [Proposal](../../docs/agent_campaign_proposal.md) | Spanish rationale, per-agent allocations, causal schedule, limits and next decisions |
| [sources.json](sources.json) | 15 primary references with facts, locators and limits |
| [assumptions.proposed.json](assumptions.proposed.json) | Explicit workload, timing, rounding and reserve assumptions; not runtime input |
| [reproduce_agent_campaign.py](reproduce_agent_campaign.py) | Standalone cost analysis through the unchanged mission scientific API |
| [campaign_analysis.json](campaign_analysis.json) | Hash-bound analytical costs, phases, clocks, cumulative sorties, nominal/adverse margins and unknowns |
| [validation/validation.json](validation/validation.json) | Actual local verification commands, outcomes, versions and hashes |

## Interpretation

The three analytical cases are Bunsen / Bright Angel / Hawksbill. Geometry is
not extracted from terrain. The new requested crops are unavailable; distances,
ascents and station counts are proposed design workloads rather than measured
science-target routes. Approved JZ-P01..07 values, profiles, receipts, source
contracts and other owners' implementations remain unchanged.

Human energy is metabolic Wh, with metabolic dry O2 equivalents at 273.15 K
and 101.325 kPa; it does not describe complete suit life support. Rover Wh are
gross electrical expenditure requirements, not storage capacity. Reserves are
20% of the rounded total allocation, kept separate from costed return. Ten and
thirty percent policies are also calculated, without changing approvals.

All nine nominal envelopes fit **by construction**, not independent validation.
All nine joint adverse envelopes fail and remain in the record. Removing one
optional sample assumes no route shortening and does not cure the joint human
or rover rejection. A 300 s rover inspection is a proposed future alternative,
not an isolated sensitivity run in this packet.

The rover's predeployment is paid before human EVA starts; its charged wait
tracks actual modeled human EVA duration. Drone per-sortie limits and desired
sortie totals are distinct, with no resource reset or recharge credit. Full
drone campaign energy/feasibility remains unknown while thermal, sleep and
recharge support is absent. Awake-gap/one-two-sol calculations are explicitly
thought experiments, not hardware feasibility or an operational calendar.

## Reproduction

From the pinned checkout with Python dependencies installed:

```powershell
python evidence/agent-campaign-proposal-20261114/reproduce_agent_campaign.py --output tmp/new-agent-campaign-analysis.json
```

The destination must not exist; writes use exclusive creation. The reproducer
checks HEAD, records input/config/model/code hashes and rechecks its inputs
before writing. Its analytic `run_id` is not a new execution identity. The
retained report was generated to a fresh ignored temporary output and copied
unchanged here; its recorded command preserves that actual origin. A repeat
changes only recording time and command, while deterministic results agree.

The original control scenario, resource coefficients, planner agreement and
execution gates are retained. No ROS, simulator, planner or discovery provider
is started for this analytical proposal. Software regression results do not
close Ubuntu/Jazzy or real three-agent acceptance. Required AI-use disclosures
are in docs/AI_USAGE.md and docs/ai_usage.json; no generated media is supplied.

## Actual local checks

Fresh Python: 979 passed, 19 skipped for ROS dependencies/Windows symlink
privileges, one existing Starlette warning. Frontend: 161 passed, one optional
replay-package skip; production build and repository checks passed. Python
3.12.14, Node 24.18.0 (matching .nvmrc), npm 12.0.1. Repetition, source hashes,
overwrite refusal, phase/resource ledgers and approval preservation checks
passed. Full commands, logs/JUnit and limitations are in validation/. No
Ubuntu/Jazzy build or real ROS exchange was attempted for this proposal.
