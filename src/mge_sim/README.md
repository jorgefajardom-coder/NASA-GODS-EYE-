# Simulation adapter scaffold

Owner: Jesus (integration), Daniel (observations), David (model approval).
R02/R06/R13; F05; SimulationAdapter; executable `sim_node`.

The `sim_node` placeholder starts and emits a warning; it publishes no clock,
state or observation. The existing `mock_agents` executable is also preserved:
it publishes clearly labelled, static MOCK agent states from an agents YAML file.
Its poses do not move and resources do not deplete. `smoke.launch.py` starts that
mock publisher using wall time by default, for graph inspection only; its output
is not a simulated mission, a perception result or resource validation.

Three more labelled MOCK executables let the gateway be integrated before the
owning modules exist; `vertical_mock.launch.py` starts them together.
`mock_terrain` publishes the coherent map batch of a synthetic flat grid
(metadata, belief, sigma and one mask per agent kind, one stamp per map version)
and bumps the version once per new observation ID; it carries no Mars data.
`mock_planner` answers PlanRoute with a straight line and placeholder rates; it
does not read terrain, so its FEASIBLE is not a verified route. `mock_mission`
covers goal, route and replan only, up to READY. They are to be replaced by
`mge_data`/`mge_mapping`, `mge_planning` and `mge_mission`.

`kinematic_executor` (`agents:=kinematic` in `vertical_mock.launch.py`) replaces
`mock_agents`; only one of them publishes the agent states. It is a labelled
MOCK stand-in for the simulation backend. The mission's primary agent follows
`/mge/planner/active_path` once the path matches the authorized route of the
current MissionState and starts at the agent's horizontal position (height
comes from the path, the public belief surface). It moves at the constant
speed and spends time, energy and oxygen at the constant rates implied by that
route's own planner estimates; nothing is replenished. When the route ID
changes or clears, or the path empties or changes, the agent halts where it is
and keeps publishing mode `HALTED` with zero velocity: that AgentState is the
stop acknowledgement. It never continues to the next waypoint, never plans and
never moves robots that only have assignments. Not dynamics, terrain contact,
a resource model or Gazebo.

No Gazebo world, physical dynamics or real perception is supplied. First implement
a clearly labelled SIMULATED adapter with agent IDs matching shared configuration.
Then validate observation footprints, simulated clock and one map update per event.
The evaluator's hidden reference must never be supplied to the route planner.

Gazebo Harmonic is the target. `ros_gz_bridge` may bridge supported native types
such as Clock, Image, Odometry and Twist. Custom `mge_interfaces` messages stay
inside ROS and are serialized by the web gateway. Add bridge mappings only after
checking actual Gazebo topic names and types; no invented mapping is included.

Acceptance: clock consistency, duplicate observation rejection with Mapping,
three-agent startup, and an evidence run showing an observation causes replanning.
All are pending. The existing MIT package metadata/version are preserved;
maintainer contact is a placeholder and repository/asset licensing needs review.

## Local additions (15 November 2026, uncommitted)

- `scene_sensing.py` / `scene_sensor` node (opt-in `sensor:=true`): SIMULATED on-board sensing of a declared test scene; the drone reports on landing, ground agents report hazards as they walk.
- `obstacle_field.py`: seeded obstacle scenes (ridge with one gap and rock clusters) that always keep a passage.
- MOCK mission opt-ins: `budget_fallback` (nearer targets, then base) and `complete_on_return`; goals off the terrain grid are rejected (`OUT_OF_MAP`).
- `gz_world.py` heightmap: its vertices sit on the planner's cell centres with the planner's heights (linear in between), so Gazebo's ground matches the planner's terrain model.
- `gz_rover_driver` node (with `external_agents:=rover_1` and `completion_tolerance_m:=1.0`): a six-wheel DiffDrive rover driven by Gazebo physics along the authorized route, publishing measured AgentState. The contributed one-time DEM/datum comparison remains available as a diagnostic; it does not shift authoritative telemetry to make a route admissible. Reported Z uses physics Z plus the declared world reference. Resources are illustrative MOCK accounting.
- With `web/public/assets/models`, the world draws the web viewer's GLB models (astronaut, rover, drone, habitat) at the web's true sizes; the rover's collision shapes stay simple and invisible.
- `gz_world.py` + `gz_mirror` node: a Gazebo Harmonic view of a run (public terrain, scene rocks with collision, Mars gravity; agents mirrored from ROS by `set_pose`). Mirrored agents only show the run; a physical rover (`gz_rover_driver`) is driven by Gazebo. The opt-in wrapper below bridges Gazebo's clock; this is not the approved `simulation` profile.

## Experimental Gazebo correction cut (15 November 2026)

The opt-in `gazebo_mock.launch.py` recipe in
[the scenario guide](../../scripts/live_scenarios/README.md) connects one physical
rover to the existing MOCK mission. Gazebo supplies physics and an explicitly
bridged clock; the other agents remain kinematic display/execution stand-ins.
This does not replace the reviewed `simulation` profile or approve a real mission.

The physical driver preserves the odometry acquisition timestamp, orientation
and six velocity axes. A steady-clock watchdog brakes on missing data, including
simulator pause. HALTED requires advancing stationary samples with a stable pose;
the driver never freezes a physical pose or invents a fresh stop acknowledgement.
Routes must preserve current finite XYZ and immutable run/map/route context.

The declared scene sensor serializes reports and confirms only matching public
map evidence. Expired reports require fresh acquisition. Drone sightings retain
their original context; the footprint sampled at landing is the current footprint,
not the union of an earlier flight relabelled with a new timestamp. Full survey
history, three-role mission acceptance and Gazebo camera/LiDAR perception remain
separate work. ROS, replay and raster versions are unchanged.
