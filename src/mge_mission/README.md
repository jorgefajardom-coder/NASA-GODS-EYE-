# mge_mission

Owner: David; integration by Jesus. Status: **mission core and ROS adapter;
integrated execution and scientific approval remain pending**.

| Layer | Responsibility |
| --- | --- |
| R | R01, R05, R10, R11, R12, R16, R18 |
| F | F04: mission authority, task precedence and acceptance |
| L | MissionSpec, TaskGraph, TaskAllocator, ScientificBenchmark |
| P | Python core in `mge_mission/core.py`; ROS startup in `mge_mission/node.py` |
| V&V | Unit/ROS contract tests; guide acceptance requires actual evidence under `evidence/` |

The resource estimators, mission reducer and adapter conversions import without
ROS. `node.py` defers ROS imports until `create_node_class()` or its console entry
point is called. The node uses the existing interfaces without wire changes.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract

The ROS node subscribes to `/clock`, `/mge/terrain/meta` and each configured
`/mge/agents/{id}/state`. It serves `/mge/mission/set_goal`, asynchronously calls
`/mge/planner/plan_route`, and publishes authoritative `/mge/mission/state`,
`/mge/mission/events` and `/mge/planner/active_path`. Reliable retained QoS is
explicit for terrain metadata, mission state and active path; agent/events are
reliable volatile, and `/clock` uses the standard clock QoS.

Only the primary human's authorized outbound locomotion path reaches
`active_path`. The complete candidate and reserved return remain in
`MissionState.active_route`. Map invalidation publishes an empty path before
replanning. This is an invalidation instruction, not physical stop confirmation.

The core alone authorizes candidates. It checks current run/request/map/pose,
profile approval, explicit model agreement, costs recomputed with the science
model, remaining resources and return/reserves. Uppercase ROS kinds are mapped
explicitly; non-human oxygen must be NaN on ROS and becomes `None` internally.
Source agent orientation, velocity and timestamps are preserved in snapshots.

The compatibility baseline is the published planner at
`34c515b6b86f73336844e8b3614c70b144574ec3` (`origin/feat/planner` at inspection).
Its non-FEASIBLE responses use NaN for unavailable costs/reserves/clearance,
including human oxygen; mission converts those values to `None` and preserves
the explicit failure reason. It never replaces unavailable estimates with zero.
A failure may have stamp zero before a map is loaded, but still requires the
canonical `map` frame and matching run/request/map context.

A FEASIBLE response must have finite applicable estimates and the exact
timestamp of the terrain batch captured at dispatch. That stamp may precede the
current agent timestamp: the core independently audits the requested pose and
current remaining resources. Metadata batches retain one timestamp per map
version, with a new timestamp for each new version. These representation checks
do not establish agreement between the planner and scientific resource models.

No evaluator reference or hidden future POI belongs in mission input. Discovery,
inspection/sampling completion and verified traversal have core-only evidence
APIs; their ROS input contracts remain pending integration. The node does not
invent those events or automatically declare `COMPLETE`.

`mission_success` retains the four explicit evidence checks: primary goal,
return within the declared tolerance, verified traversal under the model, and no
budget violation. A `FEASIBLE` plan never establishes these facts.

## Configured ROS startup

After building and sourcing a Jazzy workspace, an explicitly illustrative adapter
session can be started from the repository root:

```sh
ros2 run mge_mission mission_node --ros-args \
  -p use_sim_time:=true \
  -p run_id:=illustrative-mission \
  -p profiles_path:="$PWD/config/scenario_demo.yaml" \
  -p mission_path:="$PWD/config/scenario_demo.yaml" \
  -p allow_illustrative:=true \
  -p model_agreement_confirmed:=false \
  -p approved_model_id:=mge-science-1.0.0
```

This starts no simulator or planner and proves no mission. Before accepting a
route, deployment must explicitly confirm that the actual planner uses the same
model; this flag is an operator acknowledgment, not wire identity proof. The
numerical audit still rejects mismatched candidates. The current projected
planner profile is an approximation, so running it does not establish agreement.

Runtime parameters are `run_id`, `profiles_path`, `mission_path`,
`allow_illustrative` (default false), `model_agreement_confirmed` (default false),
`approved_model_id` and `planner_timeout_s` (positive wall-clock seconds, default
5). Mission YAML may contain a nested `mission` object, as in the demo, or flat
fields. A file requires `status: approved` or `status: illustrative`; illustrative
mission configuration and profiles both require the explicit opt-in.

`base_enu_m`, `return_tolerance_m`, `primary_service_time_s` and
`primary_service_activity` may be supplied as explicit ROS parameters instead of
the mission fields (`primary_activity` in YAML). Missing coordinates, tolerances
or service assumptions leave the service unavailable with `CONFIG_NOT_READY`.
Profile loading never promotes proposed assumptions to approval.

`use_sim_time=true` plus an actually received `/clock` is required, including when
the clock starts at zero. Cross-run, wrong-frame, future-dated and older telemetry
is rejected. A clock reset clears the route, publishes a `BLOCKED` snapshot at
the last valid simulated timestamp, and requires restarting with a new run ID.
Unavailable/timed-out planner services produce explicit blocking reasons.
Every nonempty goal request ID retains its first response, including a boundary
rejection before a clock exists. Use a new request ID for a revised attempt;
reusing an ID with changed fields returns `REQUEST_ID_CONFLICT`.

## Validation and remaining work

```sh
python -m pytest tests/mission
# On Jazzy, with the built workspace sourced:
python3 -m pytest tests/contract/test_mission_service.py
```

The ROS tests use a controlled planner and synthetic configuration to exercise
actual services and topics. They are contract evidence, not a Gazebo mission.
Guide S-01 through S-08, approved operational parameters, public discovery/work
evidence, physical motion/stop acknowledgment and the A/B/C benchmark still need
integration evidence. Benchmark policies must share scenarios/seeds and retain
failures. Return has priority over optional work.
