# mge_planning

Owner: Diego. Status: **scaffold; operational implementation pending**.

| Layer | Responsibility |
| --- | --- |
| R | R07, R08, R09, R10, R12, R18 |
| F | F03: route feasibility and resource verification |
| L | GridValidator, CostmapBuilder, RouteSearch, ResourceEstimator, RouteVerifier |
| P | Python core in `mge_planning/core.py`; ROS startup in `mge_planning/node.py` |
| V&V | Guide acceptance cases remain pending; record actual runs under `evidence/` |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_planning planning_node`.
This only starts a warning-only node; it does not claim to provide the planned ROS services or topics.
`core.py` imports without ROS so future unit tests can run independently.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract and next work

Input: public belief, sigma, NoData/traversability masks, TerrainMeta, current pose,
goal, base, run/request IDs, map version, route mode and per-agent budget. Output
(pending): RouteDecision with outbound/return paths, costs, reserves, version,
status and reason. SI fields use snake_case (`energy_est_wh`, `oxygen_est_l`).
`plan_route` deliberately raises `NotImplementedError`; no route is fabricated.

Unknown terrain is not free space. `UNKNOWN` and `NO_PATH` are distinct outcomes.
Humans alone have a separate oxygen budget; all profiles have hypothetical time
and energy constraints. Validate outbound + service + return + reserve for every
resource. Never read evaluator reference or undiscovered POIs.

Diego's first tasks: A* against Dijkstra on small nonnegative-cost grids, block
diagonal corner cutting, honor profile-specific slope/step limits, calculate the
directional return cost, reject stale versions and replan from the current pose.
Implement FAST and SAFE before adding EFFICIENT or D* Lite. All individual guide
D-01 through D-10 remain pending, including real TerrainMeta consumer integration.
