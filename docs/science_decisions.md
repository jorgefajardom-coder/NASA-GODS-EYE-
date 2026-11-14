# Scientific decisions (David)

Status: implementation choices agreed with David on 14 November 2026;
quantitative model coefficients remain proposed, not scientifically approved.
An assumption is not a measured result. Record date, decision, source/assumption,
units, sensitivity, owner, affected requirements and evidence for each approval.

| Decision | Proposed baseline | State |
| --- | --- | --- |
| Mission | Daniel public jezero_mvp; proposed A cell (12,12), B (23,23), return A | Package available/validated; scenario selection and positions proposed, see JZ-P01/P02 |
| Agents | human_1, rover_1, drone_1; ideal P0 connectivity | Confirm with team |
| Success | Primary completed AND return in tolerance AND verified ground traversal under model AND no budget violation | Strict rule accepted; proposed 1 m model-pose tolerance and rates need review |
| Knowledge | Immutable prior, evolving belief, evaluator-only reference | Public-loader/isolation checks implemented; local observation/execution verification remains pending |
| Resources | Activity- and grade-dependent estimates; movement + service + waiting, checked with return and separate reserves | Source-based model with proposed coefficients; budgets pending |
| Human reference | Declared lunar suit analog adapted by an engineering model to Mars | Approach accepted; transfer is not Mars EVA validation |
| Tasks | Discovery -> inspect -> sample; human sampling only after primary B; return overrides optional tasks | Policy accepted; execution inputs require integration |
| Planner | Published bounded FAST/SAFE search in main; D* Lite only after benefit benchmark | Implemented; science-model agreement remains pending and authorization blocked |

## Concrete Jezero proposal, 14 November 2026

Prepared at David's request for review, **not approved**. Owner for all rows:
David. Evidence: [proposal and rationale](jezero_mission_proposal.md),
[candidate configuration](../config/mission_jezero.proposed.yaml) and
[public-prior model calculations](../evidence/jezero-proposal-review-20261114/proposal_sizing.json).
The configuration records units, justification and sensitivity for each new
parameter. Profiles and existing numerical coefficients remain proposed.

| ID | Proposed decision | Unit / sensitivity | State |
|---|---|---|---|
| JZ-P01 | Adopt Daniel's public jezero_mvp package, exact manifest hash in configuration; 4 m grid / 20 m native CTX | m; neighbouring cell selection requires recomputation, no reference access | Proposed adoption; technical availability is already verified |
| JZ-P02 | A=(-14,-14,-2571.199462890625), B=(30,30,-2573.264892578125); preserve adjacent robot placeholder XY, use public datum z | ENU m; +/-1 cell choices are alternatives, not position uncertainty | Proposed; latest observed poses govern execution |
| JZ-P03 | Primary B: stationary visual observation/check-in 120 s, costed as light-work `inspect`; no sampling or optional inspection completion | s; 60/120/180 | Proposed; does not unlock sampling |
| JZ-P04 | Return within 1 m in core 3D model distance | m; 0.5/1/2; physical localization accuracy unverified | Proposed model threshold, not DEM-derived physical precision |
| JZ-P05 | Human1200 s/100 Wh/25 L; rover1200 s/60 Wh; drone180 s/15 Wh | s, metabolic/electrical Wh, equivalent dry O2 L; cap ranges in configuration | Proposed experimental allocations, not hardware capacities |
| JZ-P06 | Hold 20% separately: human240 s/20 Wh/5 L; rover240 s/12 Wh; drone36 s/3 Wh, in addition to costed return | fraction; 10/20/30% | Proposed engineering policy, not NASA standard |
| JZ-P07 | Sizing-only waits human/rover60 s, drone10 s on ground; rover service120 s, drone observation30 s; optional sample180 s only after all accepted precedences | s; zero/nominal/double waits, half/nominal/1.5 service, sample60/180/300 | Proposed durations; no tasks, observations or execution generated |

The primary human cost probe is 401.12 s/45.27 Wh/9.24 L; local rover624.47 s/
23.03 Wh; drone scalar comparison99.46 s/7.72 Wh. All cells remain unobserved;
these values neither authorize routes nor demonstrate resource adequacy for an
executed mission. Minimum rover speed fails the usable time budget; a 300 s
additional human sample fails usable energy. Do not conceal those rejections
or infer joint robustness from one-at-a-time sensitivity.

## Decisions and implementation boundaries

David selected primary technical sources before quantitative assumptions, an
activity/terrain-dependent model rather than constant rates, a pure mission core
plus ROS adapter, and explicit proposals for coefficients without transferable
source values. This records those choices, not approval of every coefficient.

The proposed profile registry records each parameter's source or assumption,
unit, sensitivity and approval state. See [model specification](science_models.md)
for formulas, source catalog and limits. Generated illustrative fixtures remain
separate from operational configuration; no dataset, base/goal, mission budget
or return tolerance is approved here. The concrete Jezero proposal above uses
public observational terrain with explicitly proposed mission parameters; it
does not modify the separate synthetic fixture or operational template.

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
