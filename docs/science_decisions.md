# Scientific decisions (David)

Status: proposed specification, pending owner confirmation. An assumption is not
a measured result. Record date, decision, source/assumption, units, sensitivity,
owner, affected requirements and evidence for each approval.

| Decision | Proposed baseline | State |
| --- | --- | --- |
| Mission | Jezero; base A; human objective B; return A | Crop/positions pending |
| Agents | human_1, rover_1, drone_1; ideal P0 connectivity | Confirm with team |
| Success | Primary completed AND return in tolerance AND verified ground traversal under model AND no budget violation | Tolerance/rates pending |
| Knowledge | Immutable prior, evolving belief, evaluator-only reference | Access test pending |
| Resources | Outbound + service + optional tasks + return + reserve | Hypothetical rates/limits pending |
| Tasks | survey -> inspect -> sample; return overrides optional tasks | Implementation pending |
| Planner | Repeated A* P0; D* Lite only after benefit benchmark | Implementation pending |

## A/B/C protocol

Compare A (no prior reconnaissance), B (corridor survey), C (informative survey)
on identical data, goal, budgets, initial knowledge, POIs and seeds. Freeze
criteria first; retain failures. Primary metric: mission success with verified
return. Record verified_ground_fraction, unsafe_step_count, optional tasks
accepted/rejected, time_to_verified_route_s, mission_duration_s, energy_est_wh,
oxygen_est_l, replan_count, replan_latency_ms, max_map_age_s, N and seeds.

Do not infer generalization from one seed. A correct BLOCKED response may pass
a rejection test while mission success remains false. No benchmark exists yet.
