# Workspace bringup

Owner: Jesus. R02/R13/R15; Bringup component; F05/F06/F07.

On Ubuntu 24.04 with ROS 2 Jazzy, install dependencies using rosdep, build with
`colcon build --symlink-install`, source `install/setup.bash`, then run:

```sh
ros2 launch mge_bringup demo.launch.py
```

The launch file starts six **scaffold processes**, not an operational mission.
Data, Mapping, Planning, Mission and Simulation currently publish nothing; gateway
health says NOT_READY. `/clock` is not supplied until the simulation adapter is
implemented. `use_sim_time=true` is the default for simulation wiring; no clock
progress or valid simulated timestamp is implied by starting the nodes.

Profiles and mission assumptions live in repository `config/`. They must be
reviewed by David and wired into consuming nodes by their owners; this base does
not silently load unapproved parameters. No Gazebo bridge is configured until
actual topics/types and supported mappings are verified.

Assign one agreed `ROS_DOMAIN_ID` per team trial. Validate all eight interfaces,
then a map-to-route-to-gateway flow, stale responses, duplicates and replay fallback.
Record commands and results under a unique run ID; these checks are pending on a
ROS-enabled machine. Placeholder maintainer email and unspecified license must
be resolved by the team before release.
