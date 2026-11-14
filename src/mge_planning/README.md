# mge_planning

Owner: Diego; temporary coverage by the team. Status: **P0 kernel and guarded ROS service implemented; full mission integration pending**.

| Layer | Responsibility |
| --- | --- |
| R | R07, R08, R09, R10, R12, R18 |
| F | F03: route feasibility and resource verification |
| L | GridValidator, CostmapBuilder, RouteSearch, ResourceEstimator, RouteVerifier |
| P | Python core in `mge_planning/core.py`; ROS startup in `mge_planning/node.py` |
| V&V | Guide acceptance cases remain pending; record actual runs under `evidence/` |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_planning planning_node`.
This starts the PlanRoute service; explicit profiles and a coherent map batch
are required before it can return a candidate. It never publishes an active route.
`core.py` imports without ROS; NumPy and SciPy are required.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract and next work

Input: public belief, sigma, NoData/traversability masks, TerrainMeta, current cell-centre pose,
goal, base, run/request IDs, map version, route mode and per-agent budget. Output
RouteDecision with outbound/return paths, costs, reserves, version,
status and reason. SI fields use snake_case (`energy_est_wh`, `oxygen_est_l`).
FAST and SAFE are implemented; EFFICIENT explicitly returns MODE_NOT_SUPPORTED.

Unknown terrain is not free space. `UNKNOWN` and `NO_PATH` are distinct outcomes.
Humans alone have a separate oxygen budget; all profiles have hypothetical time
and energy constraints. Validate outbound + service + return + reserve for every
resource. Never read evaluator reference or undiscovered POIs.

The new D-01..D-10 tests cover independent Dijkstra comparison, corners, profiles,
directional return, oxygen, stale maps, replan and bottleneck clearance. Full
integration with Daniel's final products and David's reviewed profiles is pending.
Read [MODEL.md](MODEL.md) and [handoff](../../docs/planner_handoff.md) for commands,
strict batch assembly, illustrative opt-in and the next consumer dependency.
