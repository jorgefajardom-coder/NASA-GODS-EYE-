# Scientific decisions (David)

Status: implementation choices agreed with David on 14 November 2026;
quantitative model coefficients remain proposed, not scientifically approved.
An assumption is not a measured result. Record date, decision, source/assumption,
units, sensitivity, owner, affected requirements and evidence for each approval.

| Decision | Proposed baseline | State |
| --- | --- | --- |
| Mission | Jezero; base A; human objective B; return A | Crop/positions pending |
| Agents | human_1, rover_1, drone_1; ideal P0 connectivity | Confirm with team |
| Success | Primary completed AND return in tolerance AND verified ground traversal under model AND no budget violation | Tolerance/rates pending |
| Knowledge | Immutable prior, evolving belief, evaluator-only reference | Access test pending |
| Resources | Activity- and grade-dependent estimates; movement + service + waiting, checked with return and separate reserves | Source-based model with proposed coefficients; budgets pending |
| Human reference | Declared lunar suit analog adapted by an engineering model to Mars | Approach accepted; transfer is not Mars EVA validation |
| Tasks | Discovery -> inspect -> sample; human sampling only after primary B; return overrides optional tasks | Policy accepted; execution inputs require integration |
| Planner | Repeated A* P0; D* Lite only after benefit benchmark | Implementation pending |

## Decisions and implementation boundaries

David selected primary technical sources before quantitative assumptions, an
activity/terrain-dependent model rather than constant rates, a pure mission core
plus ROS adapter, and explicit proposals for coefficients without transferable
source values. This records those choices, not approval of every coefficient.

The proposed profile registry records each parameter's source or assumption,
unit, sensitivity and approval state. See [model specification](science_models.md)
for formulas, source catalog and limits. Generated illustrative fixtures remain
separate from operational configuration; no dataset, base/goal, mission budget
or return tolerance is approved here.

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
