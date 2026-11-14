# Mars Gods Eye

Route and task decision support for a Mars surface expedition with one
astronaut, one drone and one rover. Built by team "Houston, We Have a Bug!"
for the NASA Space Apps Challenge 2026, challenge *Interplanetary Survival
Guide: Martian Map*.

**Status: early development.** What exists today is the interface contract
and a workspace skeleton. Agent data published by the smoke launch is mock
data. Perception, locomotion and consumption are simulated and labelled as
such.

## Layout

| Path | Content |
|---|---|
| `src/mge_interfaces` | ROS 2 messages and services (ICD-ROS2-V1) |
| `src/mge_sim` | Simulation adapter; currently a mock agent state publisher |
| `src/mge_bringup` | Launch files and agent configuration |
| `tests/contract` | Contract tests for the interfaces |
| `docs/ICD.md` | Frames, units, channels, enumerations, open points |
| `docs/integration_log.md` | Integration evidence and blockers |

## Requirements

ROS 2 Jazzy with `colcon`. Gazebo Harmonic is needed only for simulation
work. Either install them natively or use Docker through `scripts/dev.sh`,
which runs any command in a Jazzy container with the repository mounted.
Set `MGE_IMAGE` to choose the image.

## Build and smoke test

```bash
scripts/dev.sh colcon build --symlink-install
scripts/dev.sh ros2 interface show mge_interfaces/msg/AgentState
scripts/dev.sh python3 -m pytest tests/contract
scripts/dev.sh ros2 launch mge_bringup smoke.launch.py run_id:=smoke-001
# in a second terminal
scripts/dev.sh ros2 topic echo /mge/agents/human_1/state
```

With a native install, drop `scripts/dev.sh` and source
`/opt/ros/jazzy/setup.bash` and `install/setup.bash` first.

Agents are listed in `src/mge_bringup/config/agents.yaml`; adding an entry
adds an agent without changing any contract. Pass another file with
`agents_file:=/path/to/agents.yaml`.
