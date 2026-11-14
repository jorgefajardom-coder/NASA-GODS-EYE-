# Requirements and acceptance baseline

Source: general team R-F-L-P guide, 14 November 2026, pages 2-3 and 6-7.
All cases below are **PENDING**. Scaffold tests do not constitute acceptance.
Store actual run results under immutable `evidence/<run_id>/`.

| ID | Owner | Requirement | Minimum evidence |
| --- | --- | --- | --- |
| R01 | David | Primary goal and return | E2E start, goal, return or reasoned abort |
| R02 | Jesus | Human, rover, drone; configurable IDs | Three-agent startup, scale through config |
| R03 | Daniel | Meaningful MRO and MGS/MOLA | Actual products and appropriate scale |
| R04 | Daniel | Shared ENU grid, SI, NoData, datum | Three matching control points and mask test |
| R05 | David / Jesus | Prior/belief/reference separation | No planner access to reference or future goals |
| R06 | Daniel | Versioned simulated observations | Footprint-only update, one revision per observation |
| R07 | Diego | Traversability and unknowns | Barrier, diagonal-corner and corridor cases |
| R08 | Diego | Feasible routes and costs | A* vs Dijkstra minigrids; NO_PATH |
| R09 | Diego / Jesus | Replan from current pose | Obstacle invalidates old route; new version or block |
| R10 | David / Diego | Time, energy, human oxygen and reserve | Reject insufficient budget; preserve return |
| R11 | David | Task precedence | Observe before inspect before sample |
| R12 | David / Diego | Optional task preserves primary/return | One accepted and rejected POI with reasons |
| R13 | Jesus | One authority, ordered IDs | ROS/API/replay agree; stale response discarded |
| R14 | Jorge | Clear map, routes and reasons | Outside viewer explains route/task changes |
| R15 | Jesus / Jorge | Public static replay | Private browser and backend-off checks |
| R16 | David / Jesus | Reproducible three-policy benchmark | Same scenarios/seeds; failures retained |
| R17 | Everyone | Submission compliance | English, public links, demo limits, NASA and AI audit |
| R18 | Everyone | Explicit invalid states | UNKNOWN, NO_PATH, INSUFFICIENT_BUDGET, STALE_MAP visible |

## Function to implementation

| Function | Logical component | Package | Requirements |
| --- | --- | --- | --- |
| F01 ingest/align | DataProvider | mge_data | R03, R04 |
| F02 update knowledge | BeliefMap | mge_mapping | R05, R06 |
| F03 route/resources | RoutePlanner | mge_planning | R07-R10, R18 |
| F04 mission/tasks | MissionManager | mge_mission | R01, R11, R12, R16 |
| F05 sensors | SimulationAdapter | mge_sim | R02, R06, R13 |
| F06 view/replay | WebGateway / MissionView | mge_gateway, web | R13-R15, R17 |
| F07 verify | TestHarness | tests, CI, evidence | R01-R18 |

General scenarios: T01 fusion; T02 invalidation; T03 admissible traversal;
T04 resources; T05 optional task; T06 race; T07 A/B/C; T08 offline replay;
T09 submission. Individual guides add J-01..06, I-01..08, D-01..10,
data T-01..08 and S-01..08. Owners implement and record them.
