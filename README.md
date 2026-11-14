# MARS GODS EYE

NASA Space Apps 2026 / Interplanetary Survival Guide: Martian Map.
Team: **Houston, We Have a Bug!**

**Status: scaffold plus a mock integration vertical.** No validated mission,
NASA terrain, working planner, Gazebo world or published demo is included yet.
What runs end to end today is the integration plumbing: a goal sent over HTTP
reaches a mission node, a route comes back over REST and WebSocket, and the run
can be recorded as a replay package. The terrain, planner and mission in that
path are labelled MOCK stand-ins (a flat grid and straight-line routes), so it
is not mission evidence. The data, mapping, planning and mission packages are
still scaffolds, and the web viewer is empty by design.

Team deadline: **2026-11-15 23:59 America/Bogota (UTC-05:00)**.
Confirm any earlier local judging cutoff separately.

## Start here

- [Team branches and first tasks](docs/team.md)
- [Proposed shared interface contract](docs/ICD.md), pending team confirmation
- [Requirements and acceptance](docs/requirements.md)
- [Scientific decisions](docs/science_decisions.md)
- [Competition checklist](docs/competition.md)
- [Required AI declaration](docs/AI_USAGE.md) and [metadata](docs/ai_usage.json)
- [Integration status](docs/integration_log.md) and [verification](docs/verification.md)

## Layout and owners

| Path | Owner | Purpose |
| --- | --- | --- |
| `src/mge_interfaces` | Jesus + consumers | ROS messages and services |
| `src/mge_data`, `src/mge_mapping`, `data` | Daniel | Provenance, terrain and belief updates |
| `src/mge_planning` | Diego | Pure planning core and ROS service adapter |
| `src/mge_mission`, `config` | David; integration by Jesus | Mission authority, resources and tasks |
| `src/mge_sim`, `src/mge_gateway`, `src/mge_bringup` | Jesus | Simulation adapter, API and launch |
| `web` | Jorge | React / TypeScript / Three.js viewer and future replay |
| `tests`, `evidence`, `docs` | Everyone | Verification, immutable runs and contracts |

The evaluator reference is isolated in `data/reference` and must never be
distributed to the planner, mission manager or public mission viewer.

## Checks without ROS

Use Python 3.12. Activate a virtual environment, then from the repository root:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
python scripts/check_repository.py
```

Use Node as pinned in `web/.nvmrc`:

```sh
cd web
npm ci
npm test
npm run build
npm run preview
```

See [web/README.md](web/README.md). A static build does not imply a loaded replay
or connected ROS system. Do not expose ROS DDS to the browser.

## ROS target: Ubuntu 24.04 / ROS 2 Jazzy

Gazebo Harmonic is the intended simulator, installed separately. Native Windows
is not the declared ROS integration target; use prepared Linux/WSL.

```sh
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 interface show mge_interfaces/msg/TerrainMeta
ros2 interface show mge_interfaces/srv/PlanRoute
ros2 launch mge_bringup demo.launch.py
```

`demo.launch.py` starts placeholder processes, not an E2E mission. Read package READMEs.
The dedicated CI job compiles ROS; Windows Python checks cannot replace that.

## Collaboration and licensing

Read [AGENTS.md](AGENTS.md). Work on your assigned branch; open small PRs to
`main`. Jesus reviews integration, David scientific assumptions. Update the ICD,
producers, consumers and contract tests together when fields/frames/units change.
Use English Conventional Commits and English PR descriptions.

The integrated interfaces/simulation/bringup packages retain their existing MIT
metadata. New packages use `LicenseRef-UNSPECIFIED` and `team@example.invalid`
as explicit placeholders to replace before distribution. The team still needs
to choose and supply the overall project license; dataset licenses are separate.

## Docker alternative for ROS

`scripts/dev.sh` runs any command in a ROS 2 Jazzy container with the
repository mounted. Build the image once; `--build-arg BASE=<image>` selects
another Jazzy base image.

```sh
docker build -t mge-dev docker/
scripts/dev.sh colcon build --symlink-install
scripts/dev.sh python3 -m pytest tests/contract tests/unit tests/integration
```

## Mock integration vertical

After building and sourcing the workspace (or through `scripts/dev.sh`):

```sh
ros2 launch mge_bringup vertical_mock.launch.py run_id:=demo-001
```

This starts the gateway with MOCK agents, terrain, planner and mission from
`mge_sim`. In a second terminal:

```sh
curl http://127.0.0.1:8000/api/manifest
curl -X POST http://127.0.0.1:8000/api/mission/goal \
  -H 'Content-Type: application/json' \
  -d '{"request_id": "req-1", "primary_agent_id": "human_1",
       "base": {"x": 0, "y": 0}, "goal": {"x": 300, "y": 400},
       "time_budget_s": 14400, "energy_budget_wh": 1000, "oxygen_budget_l": 1000}'
curl http://127.0.0.1:8000/api/run/demo-001/snapshot
```

Interactive API documentation is at `http://127.0.0.1:8000/docs`; the web
contract is in [docs/ICD.md](docs/ICD.md), section 6. Agent positions and
budgets come from `src/mge_bringup/config/agents.yaml` and are explicitly
illustrative. Routes are straight lines that ignore terrain. Nothing here is a
moving mission or a NASA measurement.

`smoke.launch.py` starts only the static MOCK agent publisher, and
`demo.launch.py` starts the scaffold processes of every package; with the
latter the gateway reports `NOT_READY`, because no mission state is published.
Neither launch establishes E2E acceptance.

## Replay package

Add `record:=true` to write a replay package to `evidence/<run_id>` (or to
`record_dir:=<dir>`). A package is a set of static files that can be read
without ROS or the gateway; see [docs/ICD.md](docs/ICD.md), section 7.

```sh
ros2 launch mge_bringup vertical_mock.launch.py run_id:=demo-002 record:=true
ros2 run mge_gateway check_replay evidence/demo-002
```

`data/sample/replay/mock-vertical-001` is a sample recorded from the mock
vertical with `scripts/record_sample_replay.py`. It holds MOCK data only.
