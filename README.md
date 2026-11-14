# MARS GODS EYE

NASA Space Apps 2026 / Interplanetary Survival Guide: Martian Map.
Team: **Houston, We Have a Bug!**

**Status: real planner, data/mapping and gateway available; mission integration candidate.**
This branch preserves the existing real mission authority, resource models,
recorder and tests from feat/mission. The default synthetic vertical keeps
MOCK terrain/agents/mission; select mission:=real with explicit configuration
and a clock to substitute one authority, never run both mission providers.
The integrated web viewer plays saved runs offline in REPLAY mode: an
illustrative demo on a provisional CTX crop and the gateway's recorded MOCK run,
labelled with each run's `source_mode` (`REPLAY · SIMULATION`, `REPLAY · MOCK`).
It reads a package's public raster attachment (`files.public_rasters`) when
present, shows live Earth and Mars clocks, and offers agent and base cameras and
an agent HUD with oxygen, energy, time, route, atmosphere and dose gauges.
It is not connected to a live gateway. Science-model agreement, actual execution
and Gazebo acceptance remain pending; software availability is not mission evidence.

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
- [Planner handoff for Diego](docs/planner_handoff.md) and [temporary data provenance](docs/planner_provenance.md)

## Web viewer: what is real and where it comes from

Nothing in the viewer is presented as a measurement unless it comes from the
source named here; everything else is labelled in the interface as simulated,
illustrative, synthetic or AI-generated.

| Layer or element | Source | Status |
| --- | --- | --- |
| Elevation (Orbital map) | MRO/CTX DTM, Mars 2020 TRN mosaic, USGS Astrogeology ([DOI 10.5066/P906QQT8](https://doi.org/10.5066/P906QQT8)), 2 km crop at 20 m | Real, provisional crop |
| Contour lines | Derived from that elevation every 10 m | Derived from real data |
| Slope | Horn 3x3 on that elevation (as `gdaldem slope`), 20 m grid, about 60 m window | Derived from real data; lower bound, not a hazard map |
| Surroundings (optional) | Same CTX DTM over 20 km, box-averaged to 100 m, and the CTX orthomosaic at 40 m | Real, context only; not part of the mission map |
| Block walls | Display of the crop as a solid block | Plain rock tone, no subsurface claim |
| Surface image | MRO/CTX orthomosaic `JEZ_ctx_B_soc_008`, via [JPL Mars Trek](https://trek.nasa.gov/mars/), 6 m resampled to 5 m | Real, contrast-stretched for display |
| Ground layers (geology) | USGS SIM 3464, Sun and Stack (2020), [doi:10.3133/sim3464](https://doi.org/10.3133/sim3464) | Real map; boundaries 100-200 m approximate |
| Cut-away strata | Unit order from the SIM 3464 interpretations | Schematic: thicknesses and tones not measured |
| Atmos: Jezero weather | Perseverance MEDA daily summaries, NASA Mars weather feed | Real; outreach summary, not the PDS archive |
| Atmos: annual cycle | Curiosity REMS daily summaries at Gale crater | Real, another site; reference only |
| Atmos: radiation | MSL RAD surface averages, Hassler et al. (2014), [doi:10.1126/science.1244797](https://doi.org/10.1126/science.1244797) | Published values; Gale, unshielded estimate |
| HUD: crew dose | RAD surface average times the replay time | **Estimate**, not a dosimeter reading |
| HUD: pressure map | Latest MEDA pressure scaled with height over the area (barometric law, 11.1 km scale height) | **Estimate**, not a measured field |
| HUD: resource use | Drop between the two received samples around the replay time; route cost and reserve as published | Derived from the simulated run |
| Earth and Mars clocks | Device clock; NASA GISS Mars24 algorithm (Allison and McEwen 2000) | Real present time, not the run's time |
| Uncertainty (sigma) | Set by the demo fixture (1 m, 3 m on the surveyed crossing, 0.2 m once observed); the data package uses a constant 2.5 m | **Assumed, not measured** |
| Updated map (v2) | CTX prior plus a simulated drone observation over a scarp added to the hidden reference | **Synthetic** adverse case |
| Mission, agents, routes, budgets, events | `web/scripts/make-demo-fixture.mjs` | **Simulated**; POIs C and D fictitious; rover 1 m/s with pivot turns, drone 4 m/s at 40 m with spin-up, vertical climb and descent |
| Shadows, footprints, dust, rotor blur, wheel and steering motion | Derived in the viewer from the drawn poses | **Cosmetic display** only |
| Rover and drone models | NASA/JPL-Caltech Perseverance and Ingenuity 3D models | Real models, agency branding removed |
| Astronaut model | Sketchfab, LasquetiSpice, CC BY 4.0 | Third-party asset |
| Surface base | `base-marciana-v2`, generated with OpenAI Codex, prepared by `web/scripts/blender/prepare_base.py` | **AI-generated** 3D model |
| Evaluator reference | MRO/HiRISE DTM ([DOI 10.5066/P9REJ9JN](https://doi.org/10.5066/P9REJ9JN)) | Real; isolated, never in the public build |

Credits and licences are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md),
AI use in [docs/AI_USAGE.md](docs/AI_USAGE.md), and the viewer details in
[web/README.md](web/README.md).

## Layout and owners

| Path | Owner | Purpose |
| --- | --- | --- |
| `src/mge_interfaces` | Jesus + consumers | ROS messages and services |
| `src/mge_data`, `src/mge_mapping`, `data` | Daniel | Provenance, terrain and belief updates |
| `src/mge_planning` | Diego | Pure planning core and ROS service adapter |
| `src/mge_mission`, `config` | David; integration by Jesus | Mission authority, resources and tasks |
| `src/mge_sim`, `src/mge_gateway`, `src/mge_bringup` | Jesus | Simulation adapter, API and launch |
| `web` | Jorge | React / TypeScript / Three.js viewer with offline replay |
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
is not the declared ROS integration target; use prepared Linux/WSL (Ubuntu 24.04
on WSL 2 works with ROS 2 Jazzy desktop and Gazebo Harmonic 8). If `apt-get update`
fails because `packages.ros.org` no longer has a Release file, the machine still
uses the retired ROS apt source; install the current `ros2-apt-source` package as
described in the ROS 2 Jazzy installation guide before updating.

The integration tests also need `python3-fastapi`, `python3-uvicorn`,
`python3-websockets` and `python3-httpx` (apt); without them they are skipped,
not passed. Last local run on 2026-11-14 (WSL 2, Ubuntu 24.04, ROS 2 Jazzy):
8 packages built, `tests/contract tests/unit tests/contracts/test_gateway.py`
284 passed, `tests/integration` 34 passed, none skipped. This checks the MOCK
and real-terrain verticals and the replay recorder; it is not a validated mission.

```sh
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 interface show mge_interfaces/msg/TerrainMeta
ros2 interface show mge_interfaces/srv/PlanRoute
ros2 launch mge_bringup demo.launch.py
```

`demo.launch.py` starts package entrypoints with incomplete default mission
configuration, not an accepted E2E mission. Read package READMEs.
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
       "base": {"x": 2.5, "y": 2.5}, "goal": {"x": 152.5, "y": 202.5},
       "time_budget_s": 14400, "energy_budget_wh": 1000, "oxygen_budget_l": 1000}'
curl http://127.0.0.1:8000/api/run/demo-001/snapshot
```

Interactive API documentation is at `http://127.0.0.1:8000/docs`; the web
contract is in [docs/ICD.md](docs/ICD.md), section 6. Agent positions and
budgets come from `src/mge_bringup/config/agents.yaml` and are explicitly
illustrative. Routes are straight lines that ignore terrain. Nothing here is a
moving mission or a NASA measurement.

Add `planner:=real profiles_file:=$PWD/config/planner_profiles.illustrative.json`
to route through `mge_planning` instead of the mock planner. Terrain and mission
stay MOCK, positions must be cell centres of the 5 m grid (for example
`2.5, 2.5`), and the profiles are illustrative.

Add `terrain:=real` as well (it requires `planner:=real`) to replace the mock
terrain by `mge_data` and `mge_mapping` on the public Jezero package: a 32 x 32
grid of 4 m cells centred on the map origin, so cell centres are `-62 + 4 k`.
Agents then default to `src/mge_bringup/config/agents_jezero.yaml`. Every cell
starts unobserved, so a first route request is `UNKNOWN`; a SIMULATED
observation creates the next map version and the mission replans. Mission and
agents stay MOCK and the run is declared MOCK.

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

## Mission module checks

The proposed profiles are available for formula inspection and sensitivity
checks. They are not silently promoted to operational approval. The ROS node
requires explicit configuration, simulation time and model agreement; see
[the mission package](src/mge_mission/README.md) for startup and boundaries.

To record standalone, synthetic formula estimates in a new evidence directory:

```sh
python scripts/check_mission_models.py --run-id my-model-check --output-dir evidence/my-model-check
```

Existing evidence files are not overwritten. MODEL_CHECK outputs do not establish
actual agent traversal, completed tasks, mission success or an A/B/C result.

See [real mission provider handoff](docs/mission_integration_handoff.md) for exclusive
launch selection, clock/configuration requirements and unchanged scientific gates.
