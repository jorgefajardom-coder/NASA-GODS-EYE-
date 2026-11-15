# Scientific decisions (David)

## Current conclusions and review boundaries — after PR28

The owner requested reconsidering durations/resources by patch and separating
rover campaign, human EVA and drone sorties. The 20-minute JZ control is an
experimental horizon, not a general system/hardware limit. Existing JZ-P01..07
values and approval receipts remain unchanged; proposed replacement budgets,
coordinates and campaign calculations remain branch-local and unapproved.
The local science survey recommends larger context with nested local windows
and a Jezero shortlist; these are candidate requests, not delivered/selected
operational maps. See [the public conclusions](delivery_closure_plan.md).

[D-COST-02](decisions/2026-11-14-shared-scientific-cost-api.md) already selects
the existing scientific cost API. Completing its backend/context and profile
review remains open; do not keep presenting the implementation direction as
an unresolved choice. PR28 did not publish that later local backend.

Accepted [D-DEL-03](decisions/2026-11-14-delivery-freeze.md) now pauses expansion
until after submission and preserves the 15 Nov 20:00 target. The proposed HUD
is model-margin/context information only until reviewed; no new radiation,
slope, oxygen, no-return or Go/No-Go safety threshold is approved here.
This is a documentation update, not scientific approval of a full mission.

Status: David explicitly approved nominal experimental scenario decisions
JZ-P01 through JZ-P07 on 14 November 2026. Quantitative model coefficients,
planner cost agreement and execution evidence remain pending. Full scientific
model and operational approval is not granted by this scenario decision.
An assumption is not a measured result. Record date, decision, source/assumption,
units, sensitivity, owner, affected requirements and evidence for each approval.

| Decision | Baseline | State |
| --- | --- | --- |
| Mission | Daniel public jezero_mvp; A cell (12,12), B (23,23), return A | Approved for the experimental scenario only, JZ-P01/P02 |
| Agents | human_1, rover_1, drone_1; ideal P0 connectivity | Confirm with team |
| Success | Primary completed AND return in tolerance AND verified ground traversal under model AND no budget violation | Strict rule accepted; 1 m model-pose tolerance approved experimentally; physical accuracy and rates remain unverified |
| Knowledge | Immutable prior, evolving belief, evaluator-only reference | Public-loader/isolation checks implemented; local observation/execution verification remains pending |
| Resources | Activity- and grade-dependent estimates; movement + service + waiting, checked with return and separate reserves | Experimental allocations/reserves approved in JZ-P05/P06; model coefficients remain proposed |
| Human reference | Declared lunar suit analog adapted by an engineering model to Mars | Approach accepted; transfer is not Mars EVA validation |
| Tasks | Discovery -> inspect -> sample; human sampling only after primary B; return overrides optional tasks | Policy accepted; execution inputs require integration |
| Planner | Published bounded FAST/SAFE search in main; D* Lite only after benefit benchmark | Implemented; science-model agreement remains pending and authorization blocked |

## Jezero experimental scenario approval, 14 November 2026

Originally prepared at David's request as proposal `jezero-primary-review-01`.
David subsequently stated: "Apruebo los valores JZ-P01 a JZ-P07 para el escenario
experimental." The same instruction explicitly leaves profile approval, cost
agreement and execution evidence pending. Owner for all rows: David.

Current record: [approval receipt JZ-APP-20261114-01](science_approvals/jezero_scenario_20261114.json)
and [experimental configuration](../config/mission_jezero.experimental.yaml).
The configuration remains `pending_integration`; `scenario_approval` is separate
from the empty operational `approval_evidence`. Neither the runtime flags nor
the source profile approval states are changed.

Historical review evidence remains immutable: [proposal and rationale](jezero_mission_proposal.md),
[original proposed configuration](../config/mission_jezero.proposed.yaml) and
[public-prior model calculations](../evidence/jezero-proposal-review-20261114/proposal_sizing.json).
The receipt binds the reviewed proposal and approved nominal values. Sensitivity
alternatives remain analytical cases, not additional execution approvals.
FAST and ideal_global_p0 retain the existing experimental baseline; no shared
contract is frozen by this approval.

| ID | Approved nominal experimental decision | Unit / sensitivity | State |
|---|---|---|---|
| JZ-P01 | Adopt Daniel's public jezero_mvp package, exact manifest hash in configuration; 4 m grid / 20 m native CTX | m; neighbouring cell selection requires recomputation, no reference access | Approved experimentally; not physical terrain verification |
| JZ-P02 | A=(-14,-14,-2571.199462890625), B=(30,30,-2573.264892578125); preserve adjacent robot placeholder XY, use public datum z | ENU m; +/-1 cell choices are alternatives, not position uncertainty | Approved experimentally; latest observed poses still govern execution |
| JZ-P03 | Primary B: stationary visual observation/check-in 120 s, costed as light-work `inspect`; no sampling or optional inspection completion | s; 60/120/180 | Approved experimentally; does not unlock sampling |
| JZ-P04 | Return within 1 m in core 3D model distance | m; 0.5/1/2; physical localization accuracy unverified | Approved experimental model threshold, not DEM-derived physical precision |
| JZ-P05 | Human1200 s/100 Wh/25 L; rover1200 s/60 Wh; drone180 s/15 Wh | s, metabolic/electrical Wh, equivalent dry O2 L; cap ranges in configuration | Approved experimental allocations, not hardware capacities |
| JZ-P06 | Hold 20% separately: human240 s/20 Wh/5 L; rover240 s/12 Wh; drone36 s/3 Wh, in addition to costed return | fraction; 10/20/30% | Approved experimental policy, not NASA standard |
| JZ-P07 | Sizing-only waits human/rover60 s, drone10 s on ground; rover service120 s, drone observation30 s; optional sample180 s only after all accepted precedences | s; zero/nominal/double waits, half/nominal/1.5 service, sample60/180/300 | Approved experimental durations; no tasks, observations or execution generated |

The primary human cost probe is 401.12 s/45.27 Wh/9.24 L; local rover624.47 s/
23.03 Wh; drone scalar comparison99.46 s/7.72 Wh. All cells remain unobserved;
these values neither authorize routes nor demonstrate resource adequacy for an
executed mission. Minimum rover speed fails the usable time budget; a 300 s
additional human sample fails usable energy. Do not conceal those rejections
or infer joint robustness from one-at-a-time sensitivity.

## Decisions and implementation boundaries

### Cost and activity-duration review, 14 November 2026

This continuation reviews published main
`2f50ae697b34fe82e575b386936d0d5e4d74db64` and planner
`69101e983c9a9668ba852460c484b5db8f12a1a5` without merging or modifying
their implementations. Mission's source baseline remains `09d7d6a`; the
following packet is a proposal and model diagnostic, not a new execution.

The [cost agreement packet](cost_agreement_handoff.md) binds the scientific
API, phase schedule, model/profile/configuration hashes and existing audit
tolerances. The exact published planner comparison retains one agreeing and
six disagreeing cases, with authorization **BLOCKED**. All seven returned
feasible candidates, which does not establish numerical agreement. The
planner's fixed service power and oxygen/time rate cannot represent every
activity. `PlanRoute` carries service duration but no activity/wait identity;
Diego and Jesús must agree its run/request-bound configuration context before
integration. No shared message field or tolerance is changed here.

David requested evidence-based activity timings before sharing the packet with
Diego and Jesús. The [source review and analytical pilot](activity_duration_research.md)
separate lunar model primitives (30 s pickup, 60 s hammering, 180 s trenching),
reported D-RATS approximately 600 s documented samples, prescribed ARGOS
sampling blocks and whole-station planning context. These are different task
scopes, not interchangeable measurements or validated Mars durations.

| ID | Proposed interpretation | State and sensitivity |
|---|---|---|
| JZ-D01 | Retain the approved 120 s B check-in as a brief stationary visual task; the 300 s light-work alternative is an engineering sensitivity because no universal isolated Mars inspection duration was established | Existing 120 s unchanged; 300 s pending review, never a runtime override |
| JZ-D02 | Treat 30/60/180 s lunar model values as acquisition primitives, not a complete documented sample cycle | Source classification recorded; no added duration approval |
| JZ-D03 | Pilot a 600 s documented sample with 420 s light and 180 s heavy work, charged once | Total informed by D-RATS; phase split is our assumption and pending review; all-heavy 600 s is a separate power bound |
| JZ-D04 | Keep full cycles, primary service and waits distinct; do not add an acquisition primitive inside a cycle that already includes it | Cost accounting requirement; interrupted work still needs agreed progress evidence |

The mixed 600 s additional workflow produces a combined public-prior cost probe
of 1001.12 s / 110.10 Wh / 22.48 L, exceeding usable resources of
960 s / 80 Wh / 20 L after the approved reserve. This rejection excludes
additional optional travel; it must not be concealed by removing the reserve
or widening tolerances. The existing approved 180 s sampling example remains
unchanged and must not be presented as a complete documented sample cycle.
Pilot durations do not establish rover or drone timing.

The [success criteria](mission_success_contract.md) retain the four existing
conjunctive predicates, the approved 120 s service and 1 m model tolerance.
They explicitly record missing runtime duration/progress enforcement and
execution inputs. They are a reviewable contract, not completed execution
acceptance. CONT-DAV-01/02 remain prepared for joint review, not closed.
Profiles, cost agreement, execution evidence and operational authorization
remain pending; no new approval receipt or operational flag is issued.

The accepted [D-EST-01 scope decision on main](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/2f50ae697b34fe82e575b386936d0d5e4d74db64/docs/decisions/2026-11-14-estimated-terrain-planning.md)
allows hypothetical planning over valid unobserved estimates while preserving
uncertainty and NoData distinctions. Thus unobserved prior cells are not
automatically NoData; planning permission does not prove executed traversal.
Coordinated producer/planner implementation remains with Daniel and Diego.
No local observation flag, sigma threshold or shared occupancy code is changed.

Validation and retained hashes for this packet are recorded separately under
`evidence/mission-cost-closure-20261114/`; initial diagnostics and final
configuration-bound vectors/pilot remain distinguishable. Software checks and
model diagnostics do not constitute an integrated mission or A/B/C result.

David selected primary technical sources before quantitative assumptions, an
activity/terrain-dependent model rather than constant rates, a pure mission core
plus ROS adapter, and explicit proposals for coefficients without transferable
source values. This records those choices, not approval of every coefficient.

The proposed profile registry records each parameter's source or assumption,
unit, sensitivity and approval state. See [model specification](science_models.md)
for formulas, source catalog and limits. Generated illustrative fixtures remain
separate from operational configuration. The approved Jezero experimental
scenario above fixes its nominal dataset, positions, service, allocations,
reserves and model-pose tolerance only. It does not approve profile coefficients,
planner-model agreement, physical execution, or a completed mission, and does
not modify the separate synthetic fixture or operational template.

Human Wh means estimated metabolic expenditure; robot Wh means modeled
electrical consumption. Human oxygen is a model estimate derived from BVAD's
average relation to metabolic energy. It is not an activity-specific measured
oxygen model or a complete suit-loss model. Proposed `_l` semantics are dry ideal
gas equivalent at 273.15 K and 101.325 kPa; consumers must confirm the same
convention before quantitative integration is approved.

Resource checks use current remaining resources, not the initial allocation.
Service and waiting must be charged exactly once. A projected planner profile is
explicitly approximate: a file conversion does not establish model agreement.
The existing ROS wire has no model identity field, so preserve deployment model
IDs/configuration hashes as evidence and separately audit route costs.

Mission authority must not create discoveries from hidden POIs or infer completed
work/verified traversal from a plan. ROS discovery/completion/traversal inputs
remain integration dependencies. Clearing a route is an invalidation signal, not
proof that a simulator or physical agent acknowledged a stop.

## A/B/C protocol

Compare A (no prior reconnaissance), B (corridor survey), C (informative survey)
on identical data, goal, budgets, initial knowledge, POIs and seeds. Freeze
criteria first; retain failures. Primary metric: mission success with verified
return. Record verified_ground_fraction, unsafe_step_count, optional tasks
accepted/rejected, time_to_verified_route_s, mission_duration_s, energy_est_wh,
oxygen_est_l, replan_count, replan_latency_ms, max_map_age_s, N and seeds.

Do not infer generalization from one seed. A correct BLOCKED response may pass
a rejection test while mission success remains false. No integrated benchmark
exists yet. Follow the [frozen-before-running protocol](science_benchmark.md) and
retain the [integration handoff](mission_handoff.md) with each review.
