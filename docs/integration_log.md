# Integration log

| Cut | Owner | State | Next handoff | Evidence |
| --- | --- | --- | --- | --- |
| Initial scaffold, 2026-11-14 | Jesus + team | Structure only | Confirm ICD; crop; profiles; first vertical | verification.md; no mission run |
| ICD-ROS2-V1 draft, 2026-11-14 | Jesus | `mge_interfaces` 1.0.0; 3 packages build; `ros2 interface show` for the 8 definitions; 10 contract tests pass; `smoke.launch.py` publishes 3 MOCK agent states | Team freeze of ICD-V1 | Run locally in a ROS 2 Jazzy container; CI run on `dev/jesus` |
| Mock vertical, 2026-11-14 | Jesus | `vertical_mock.launch.py`: goal -> route -> REST/WebSocket through `mge_gateway`. Terrain, planner and mission are MOCK stand-ins in `mge_sim`: routes are straight lines and prove nothing about terrain; the mission stops at `READY` | Jorge consumes the web contract; Diego, David and Daniel replace the mocks with `mge_planning`, `mge_mission`, `mge_data`/`mge_mapping` | `tests/integration/test_vertical_mock.py` (idempotent request, duplicate observation, map v2 replan, insufficient budget, unknown agent), run locally in the `mge-dev` container |
| Replay package, 2026-11-14 | Jesus | `replay_recorder` writes `manifest.json`, `timeline.jsonl`, `snapshot.json`; `check_replay` validates offline. I-06 is covered at file level only: no web client plays a package yet. No raster in the package. Timestamps are system clock: no Gazebo `/clock` yet | Jorge builds the replay view on the sample package; Daniel's rasters define how terrain is packaged | `tests/integration/test_replay_package.py`; sample `data/sample/replay/mock-vertical-001` recorded by `scripts/record_sample_replay.py` (MOCK data only) |
| Scaffold merge, 2026-11-14 | Jesus | `dev/jesus` merged into `feat/integration` on top of the shared scaffold. The placeholder gateway is replaced by the ROS-backed one; it keeps the unavailable envelope until a run is active. JSON `schema_version` is `1.0.0` | Review and merge to `main` | See the pull request for the commands and results of this cut |
| Planner in the vertical, 2026-11-14 | Jesus | `vertical_mock.launch.py planner:=real` runs `mge_planning` behind the MOCK mission and gateway. `mock_terrain` now publishes the coherent batch (meta, belief, sigma, three masks, one stamp per map version) and agents sit on cell centres. A 250 m FAST route returns in about 1 s; replan on map v2 works. Terrain is still a synthetic flat grid, so this is plumbing, not a route on Mars terrain. **Findings for the planner owner:** (1) with the batch repeated at 1 Hz the planner node takes about 0.4 s per layer callback (about 1 ms in isolation) and stops answering PlanRoute for grids of 60 x 60 and up; the mock repeats every 5 s to avoid it. (2) A request whose budget is clearly short (150 Wh available, 100 Wh reserve, about 105 Wh needed) answers `UNKNOWN/SEARCH_LIMIT` after the time limit, not `INSUFFICIENT_BUDGET`. (3) A 500 m request on the 200 x 200 grid hits `SEARCH_LIMIT` at the default 2 s | Planner owner reviews the three findings; mission owner replaces `mock_mission` | `tests/integration/test_vertical_planner.py`, run locally in the `mge-dev` container |

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

## Planner P0 takeover

| Commit / run | Owner / review | Observed result | Next dependency |
| --- | --- | --- | --- |
| a6204dd | Diego front; Jesus integration review | FAST/SAFE kernel, resource-constrained joint return and acceptance cases published | Guarded ROS adapter |
| 6e4984d | Diego front; David science review | PlanRoute server, immutable public batches, fresh CTX prior and isolated local HiRISE reference | Jazzy CI, producer batch protocol, approved profiles |
| planner-p0-20261114 | Team takeover | Nine new illustrative benchmark queries match independent Dijkstra; real unverified CTX yields UNKNOWN; 154 local tests pass, two ROS modules skip | Full mission/consumer acceptance on Daniel and David inputs |

Continue on feat/planner; see planner_handoff.md. The generated benchmark is
computational acceptance evidence, not mission safety or scientific validation.
