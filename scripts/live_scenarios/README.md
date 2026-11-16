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
  drone scouts and reports what it saw on landing; the astronaut's sensor reports
  hazards as it walks, so every map update comes from the simulated sensors.

- `gazebo_world.py`: builds a Gazebo Harmonic world (`mge_sim.gz_world`) of the
  `jezero_mvp` crop and a scene file: heightmap from the public prior (bilinear, the
  only collision surface of the ground), albedo from the real MRO CTX orthoimage DN
  with a cosmetic Mars tint, grain and normal map, one boulder with collision per
  blocked cell (enlarged display sizes, as in the viewer) and visual-only smaller
  rocks, Mars gravity (3.721 m/s2). Open it with `gz sim -r <out>/world.sdf` and run
  `ros2 run mge_sim gz_mirror --ros-args -p run_id:=<run> -p world_json:=<out>/world.json`
  to move the agent models with their ROS poses. Gazebo only SHOWS the run: agents
  are visual-only models moved by `set_pose`, so this is not a physics simulation
  of the agents and not the `simulation` launch profile.

- `rover_gz_run.py`: rover_1 is a physical rover in Gazebo (gz_rover_driver), the others
  stay kinematic and mirrored; the scene sensor, budget fallback and goal completion are on.
  Pass the web models with `MGE_WEB_MODELS=<repo>/web/public/assets/models`.

Stop a launched stack with `kill -INT -<pid>` (pid in `<record_dir>/<run_id>-launch.pid`)
so the recorder closes the package. Observations are SIMULATED test inputs and
budgets are illustrative; no run is a validated LIVE mission. AI-assisted
(Claude through Claude Code); see docs/AI_USAGE.md.
