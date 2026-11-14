# MARS GODS EYE

NASA Space Apps 2026 / Interplanetary Survival Guide: Martian Map.
Team: **Houston, We Have a Bug!**

**Status: base scaffold.** No validated mission, NASA terrain, working planner,
Gazebo world, live ROS-to-web flow or published demo is included yet. The empty
viewer and unavailable API responses are intentional, not mission evidence.

Team deadline: **2026-11-15 23:59 America/Bogota (UTC-05:00)**.
Confirm any earlier local judging cutoff separately.

## Start here

- [Team branches and first tasks](docs/team.md)
- [Probable roadmap and owner checklists](docs/mission_checklist.md)
- [NASA resource-to-result traceability](docs/nasa_traceability.md)
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

Launch starts placeholder processes, not an E2E mission. Read package READMEs.
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

## Existing integration smoke test

The team work on dev/jesus is included with its original history and canonical
ROS definitions. After colcon build/source on Jazzy, run:

```sh
ros2 launch mge_bringup smoke.launch.py
```

This publishes static MOCK agent states with explicitly illustrative positions
and budgets from src/mge_bringup/config/agents.yaml. It is not a moving mission
or a NASA measurement. `demo.launch.py` starts the other scaffold processes;
neither launch establishes E2E acceptance. See docs/ICD.md for the wire mapping.
