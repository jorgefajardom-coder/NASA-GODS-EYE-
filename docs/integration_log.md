# Integration log

| Cut | Owner | State | Next handoff | Evidence |
| --- | --- | --- | --- | --- |
| Initial scaffold, 2026-11-14 | Jesus + team | Structure only | Confirm ICD; crop; profiles; first vertical | verification.md; no mission run |
| ICD-ROS2-V1 draft, 2026-11-14 | Jesus | `mge_interfaces` 1.0.0; 3 packages build; `ros2 interface show` for the 8 definitions; 10 contract tests pass; `smoke.launch.py` publishes 3 MOCK agent states | Team freeze of ICD-V1 | Run locally in a ROS 2 Jazzy container; CI run on `dev/jesus` |
| Mock vertical, 2026-11-14 | Jesus | `vertical_mock.launch.py`: goal -> route -> REST/WebSocket through `mge_gateway`. Terrain, planner and mission are MOCK stand-ins in `mge_sim`: routes are straight lines and prove nothing about terrain; the mission stops at `READY` | Jorge consumes the web contract; Diego, David and Daniel replace the mocks with `mge_planning`, `mge_mission`, `mge_data`/`mge_mapping` | `tests/integration/test_vertical_mock.py` (idempotent request, duplicate observation, map v2 replan, insufficient budget, unknown agent), run locally in the `mge-dev` container |
| Replay package, 2026-11-14 | Jesus | `replay_recorder` writes `manifest.json`, `timeline.jsonl`, `snapshot.json`; `check_replay` validates offline. I-06 is covered at file level only: no web client plays a package yet. No raster in the package. Timestamps are system clock: no Gazebo `/clock` yet | Jorge builds the replay view on the sample package; Daniel's rasters define how terrain is packaged | `tests/integration/test_replay_package.py`; sample `data/sample/replay/mock-vertical-001` recorded by `scripts/record_sample_replay.py` (MOCK data only) |
| Scaffold merge, 2026-11-14 | Jesus | `dev/jesus` merged into `feat/integration` on top of the shared scaffold. The placeholder gateway is replaced by the ROS-backed one; it keeps the unavailable envelope until a run is active. JSON `schema_version` is `1.0.0` | Review and merge to `main` | See the pull request for the commands and results of this cut |

Add commit/schema version, owner, run_id, command, observed result and next
dependency per integration cut. Do not call a build a successful mission.

## Existing team contribution preserved

Merged source: `dev/jesus` at `00c8e44`. The branch's integration log reports
that Jesus built its three original ROS packages in a Jazzy container, inspected
eight interfaces, passed ten ROS contract tests and published three static MOCK
agent states. Those results are contributor-reported and were not rerun on this
native Windows host. The current combined workspace requires its own CI build.
The original commits and interface definitions are retained; no contract freeze
or physical mission validation is implied.
