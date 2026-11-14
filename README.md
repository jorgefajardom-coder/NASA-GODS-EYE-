# Mars Gods Eye

Route and task decision support for a Mars surface expedition with one
astronaut, one drone and one rover. Built by team "Houston, We Have a Bug!"
for the NASA Space Apps Challenge 2026, challenge *Interplanetary Survival
Guide: Martian Map*.

**Status: early development.** What exists today is the interface contract,
the ROS-to-web gateway and an end-to-end path built on mock producers. The
terrain, planner and mission nodes are labelled stand-ins: routes are straight
lines and no Mars data is loaded yet. Perception, locomotion and consumption
are simulated and labelled as such.

## Layout

| Path | Content |
|---|---|
| `src/mge_interfaces` | ROS 2 messages and services (ICD-ROS2-V1) |
| `src/mge_sim` | Simulation adapter; currently mock agents, terrain, planner and mission |
| `src/mge_gateway` | FastAPI gateway: REST and WebSocket over the ROS graph |
| `src/mge_bringup` | Launch files and agent configuration |
| `tests` | Unit, contract and end-to-end tests |
| `data/sample/replay` | Sample replay package recorded from the mock vertical |
| `docker/Dockerfile` | Development image (ROS 2 Jazzy plus web dependencies) |
| `docs/ICD.md` | Frames, units, channels, enumerations, open points |
| `docs/integration_log.md` | Integration evidence and blockers |
| `docs/AI_USAGE.md` | Where and how AI tools were used |

## Requirements

Docker, or a native ROS 2 Jazzy install with `colcon`, `python3-fastapi`,
`python3-uvicorn`, `python3-websockets` and `python3-httpx`. Gazebo Harmonic
is needed only for simulation work.

With Docker, build the development image once and run every command through
`scripts/dev.sh`, which mounts the repository in the container:

```bash
docker build -t mge-dev docker/
```

`--build-arg BASE=<image>` selects another ROS 2 Jazzy base image.

## Build and test

```bash
scripts/dev.sh colcon build --symlink-install
scripts/dev.sh python3 -m pytest tests
```

## Run the mock vertical

```bash
scripts/dev.sh ros2 launch mge_bringup vertical_mock.launch.py run_id:=demo-001
```

In a second terminal:

```bash
curl http://127.0.0.1:8000/api/manifest
curl -X POST http://127.0.0.1:8000/api/mission/goal \
  -H 'Content-Type: application/json' \
  -d '{"request_id": "req-1", "primary_agent_id": "human_1",
       "base": {"x": 0, "y": 0}, "goal": {"x": 300, "y": 400},
       "time_budget_s": 14400, "energy_budget_wh": 1000, "oxygen_budget_l": 1000}'
curl http://127.0.0.1:8000/api/run/demo-001/snapshot
```

Interactive API documentation is at `http://127.0.0.1:8000/docs`. The web
contract is described in `docs/ICD.md`, section 5.

## Record and check a replay

Add `record:=true` to write a replay package to `evidence/<run_id>` (or to
`record_dir:=<dir>`). A package is a set of static files that can be read
without ROS or the gateway; see `docs/ICD.md`, section 6.

```bash
scripts/dev.sh ros2 launch mge_bringup vertical_mock.launch.py run_id:=demo-002 record:=true
scripts/dev.sh ros2 run mge_gateway check_replay evidence/demo-002
```

`scripts/dev.sh python3 scripts/record_sample_replay.py <run_id>` records the
scripted sample run found in `data/sample/replay`.

With a native install, drop `scripts/dev.sh` and source
`/opt/ros/jazzy/setup.bash` and `install/setup.bash` first.

Agents are listed in `src/mge_bringup/config/agents.yaml`; adding an entry
adds an agent without changing any contract. Pass another file with
`agents_file:=/path/to/agents.yaml`.

## AI tools

AI tools were used to write code and documentation in this repository. See
`docs/AI_USAGE.md`.
