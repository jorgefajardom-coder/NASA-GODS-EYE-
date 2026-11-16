# Live ROS scenario drivers (local, MOCK/SIMULATED)

Drivers used on 2026-11-15 to run the vertical MOCK stack in WSL (Ubuntu 24.04,
ROS 2 Jazzy) and watch it in the viewer with `?gateway=http://127.0.0.1:8010`.
Run each from a built, sourced workspace root:
`python3 scripts/live_scenarios/<driver>.py <run_id> 8010 <record_dir> [seed]`.

- `move_run.py`: launches the stack, fuses a SIMULATED observation, short trip,
  long trip with a mid-route map update (halt and replan). Leaves the stack running.
- `resource_run.py`: on a running stack, a far sortie with a tight budget, a
  SIMULATED wall mid-route, budget-driven replan, operator fallback list.
- `obstacle_run.py`: launches with `budget_fallback:=true`, publishes a seeded
  obstacle field (`mge_sim.obstacle_field`), tight sortie, new rocks mid-route;
  the MOCK mission picks the fallback target itself.

- `sensing_run.py`: launches with the estimated-terrain policy, `budget_fallback:=true`,
  `complete_on_return:=true` and `sensor:=true` over a seeded SIMULATED scene. The
  drone scouts and reports the current landing footprint; earlier sightings keep
  their historical context. The astronaut's sensor reports
  hazards as it walks, so every map update comes from the simulated sensors.

- `gazebo_world.py`: builds a Gazebo Harmonic world (`mge_sim.gz_world`) of the
  `jezero_mvp` crop and a scene file: heightmap from the public prior (bilinear, the
  only collision surface of the ground), albedo from the real MRO CTX orthoimage DN
  with a cosmetic Mars tint, grain and normal map, one boulder with collision per
  blocked cell (enlarged display sizes, as in the viewer) and visual-only smaller
  rocks, Mars gravity (3.721 m/s2). Open it with `gz sim -r <out>/world.sdf` and run
  `ros2 run mge_sim gz_mirror --ros-args -p run_id:=<run> -p world_json:=<out>/world.json`
  to move the visual agent models with their ROS poses. Without a physical-agent
  argument this is only a view of the kinematic run. The optional fourth argument
  `rover_1` builds that configured rover with wheel dynamics and collisions; use
  the integrated opt-in launch below rather than launching another state publisher.

- `rover_gz_run.py`: rover_1 is a physical rover in Gazebo (gz_rover_driver), the others
  stay kinematic and mirrored; the scene sensor, budget fallback and goal completion are on.
  Pass the web models with `MGE_WEB_MODELS=<repo>/web/public/assets/models`.

Since the scientific cost integration (#50) the real planner needs a scientific
planning context from the mission; the MOCK mission does not register one, so these
drivers launch with `allow_legacy_cost_model:=true`, as main's own MOCK integration
tests do. Their routes use the legacy illustrative cost model.

Stop a launched stack with `kill -INT -<pid>` (pid in `<record_dir>/<run_id>-launch.pid`)
so the recorder closes the package. Observations are SIMULATED test inputs and
budgets are illustrative; no run is a validated LIVE mission. AI-assisted
(Claude through Claude Code); see docs/AI_USAGE.md.

## Integrated Gazebo rover experiment

`gazebo_mock.launch.py` is a separate, opt-in **MOCK** experiment on the default
public `jezero_mvp` crop. One rover receives physics odometry from Gazebo; the
human and drone remain kinematic MOCK companions. Mission authority is the
existing `mock_mission`, resources are illustrative, and optional scene sensing
is **SIMULATED** declared-scene sensing, not a Gazebo camera or lidar. This does
not enable the gated `simulation` profile, a real MissionManager, three-role
acceptance, scientific success or a validated LIVE mission.

Use Ubuntu 24.04, ROS 2 Jazzy and Gazebo Harmonic in a workspace path without
spaces. Build with `colcon build --symlink-install` and source both
`/opt/ros/jazzy/setup.bash` and `install/setup.bash`. The launch requires the
installed `ros_gz_bridge` `parameter_bridge` executable and the Gazebo Python
`gz.transport13`/`gz.msgs10` bindings. Check them locally; the launch does not
install dependencies or fetch a model.

Choose an unused `ROS_DOMAIN_ID` explicitly and run exactly one launcher in it.
The example domain below is illustrative; do not reuse it when another member
or process is using it. The preflight checks existing MGE publishers, mission
and planner services and `/clock`; it is a bounded discovery check, not a DDS
lock. Stop existing experiments before starting a new one.

```bash
export ROS_DOMAIN_ID=219
SCENE=/absolute/path/to/reviewed-simulated-scene.json
AGENTS="$(realpath src/mge_bringup/config/agents_jezero.yaml)"
WORLD="$(pwd)/.local/gazebo-rover-world"

# Same scene and canonical NEW_SCENE initialization as the ROS agent producers.
# The fourth argument selects exactly the rover that the launch will drive.
python3 scripts/live_scenarios/gazebo_world.py "$SCENE" "$AGENTS" "$WORLD" rover_1

ros2 launch mge_bringup gazebo_mock.launch.py \
  run_id:=gazebo-rover-experiment-001 rover_id:=rover_1 \
  world_sdf:="$WORLD/world.sdf" world_json:="$WORLD/world.json" \
  agents_file:="$AGENTS" \
  profiles_file:="$(realpath config/planner_profiles.illustrative.json)" \
  allow_legacy_cost_model:=true \
  exploration_policy_file:="$(realpath config/exploration_policy.illustrative.json)" \
  allow_continuous_starts:=true \
  sensor:=true sensor_scene_file:="$SCENE" \
  record:=true record_dir:="$(pwd)/.local/gazebo-recordings" port:=8010
```

The scene must use `mge-sim-scene-1.0.0`, `source_kind: SIMULATED`, the public
crop's rows/columns and in-bounds blocked indices. It is synthetic input, never
evaluator truth or a NASA observation. Keep its revision/hash with the run.
PR50 requires registered scientific planning context by default. This wrapper
uses the historical MOCK mission and must explicitly select
`allow_legacy_cost_model:=true` for its legacy consumer. The default remains
false; the wrapper never silently falls back or claims scientific-model agreement.
The corrected generator records scene, agent-file and SDF SHA-256 hashes in
the local `world.json` input receipt. Bound files must still match; `sensor:=true`
requires that exact scene file. Regenerate older worlds before enabling sensing.
These local world hashes do not change a ROS, raster or replay contract.
`allow_continuous_starts:=true` is an explicit experimental opt-in because a
physical rover may settle away from an exact grid centre; it does not project
telemetry onto the terrain or authorize a route. The planner may still return
UNKNOWN or reject an unsupported physical pose.

The wrapper checks world names, grid, agent IDs/kinds, initial positions,
resources and the rover's physical plugins/topics before starting a process.
Exactly that rover is excluded from `kinematic_executor`; `gz_mirror` skips
physical models. Each agent state therefore has one intended producer. A
dedicated Gazebo transport partition `mge-<run_id>` is inherited by the server,
bridge, driver and mirror. Reusing a run ID on another machine/launcher does not
provide isolation; choose unique run IDs and dedicated ROS domains.

By default `gz sim -r -s` runs headless; `gui:=true` opens the server and GUI.
Only `/world/<world_name>/clock` is bridged, unidirectionally into ROS `/clock`.
Consumers start after one advancing clock publisher is observed and all receive
`use_sim_time=true`. Gazebo pause stops simulated time; driver odometry freshness
checks remain independent of that pause. Server, bridge or driver exit shuts
down the experiment. Ctrl+C closes the launcher and recorder; verify recorder
closure and run/package hashes rather than killing arbitrary ROS processes.

The launcher **sends no mission goal**. The web gateway bar is read-only and does
not animate the saved replay scene from current ROS telemetry. Use the existing
operator/API workflow only after checking the current run, map, pose, budgets
and proposed target. Do not run `sensing_run.py` or `obstacle_run.py` beside this
launcher: those scripts start their own vertical stack. `budget_fallback` and
`complete_on_return` remain off unless explicitly selected; returning to base in
this MOCK experiment is not scientific mission completion.

For review, retain source/config/world/scene hashes, the exact ROS domain and run
identity, build/interface checks, state-publisher counts and evidence of actual
motion, stop, pause/stale odometry and reauthorization. Validate the exact closed
replay separately with backends off. Final captures/exports must preserve the
MOCK/SIMULATED labels and required visible AI-generated disclosures. Jesus reviews
integration and David scientific assumptions; this recipe grants neither approval.
