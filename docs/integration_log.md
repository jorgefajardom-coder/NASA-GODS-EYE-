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

## Web viewer (feat/ux, PR #5)

| Commit / run | Owner / review | Observed result | Next dependency |
| --- | --- | --- | --- |
| fc03df6 | Jorge; Jesus integration review | Mission viewer replaces the web scaffold; scaffold stale-route guard and envelope types kept in the viewer | Review of PR #5 |
| 89216fc | Jorge; Jesus | Viewer plays the gateway package `mock-vertical-001` (copied unchanged from feat/integration d28f3e2) and ends in READY, map v2, route r2 | Rasters inside replay packages; live gateway connection |
| 1e37fd3 | Jorge | `main` (planner PR #2) merged into feat/ux; only the AI disclosure register conflicted, both entries kept | Consume planner routes in the viewer |

Local evidence: 64 web tests, `npm run build` and `scripts/check_repository.py` pass;
`python -m pytest` was not run on this host (pytest not installed). The terrain is a
provisional CTX crop pending Daniel's processed package.

Continue on feat/planner; see planner_handoff.md. The generated benchmark is
computational acceptance evidence, not mission safety or scientific validation.

## Contract reconciliation cut, 2026-11-14

- Baseline candidate: 1.0.0-rc.1, ROS package/schema unchanged at1.0.0/ICD-ROS2-V1;
  canonical gateway replay1.0.0. Commit041a636 introduced adapters/contracts;
  source f2af4b23b57e0ef28c245cca0ad64a886ded039e reconciles concurrent main004b3b2.
- Main PR #2 was merged externally by Jesus during this task. Only that already
  reviewed main was incorporated; no other owner PR was merged here. Initial
  audit main f75c54e is retained in the source lock.
- Source commit uses the existing David Yanguas Git identity. Integration
  approval remains Jesus; scientific/model acceptance remains David with Diego;
  commit identity does not assert those approvals.
- Latest audited heads and owners are in contract_baseline.json/matrix.
  feat/ux now continues Jorge's original feature/web-replay-viewer via PR #5;
  source alignment awaits Jorge/Jesus, no branch was overwritten.
- run_id contract-baseline-20261114: native Python263 passed/four ROS module
  skips; Ubuntu24.04/Jazzy8 packages/all8interfaces and129 tests passed; web
  npm ci/test/build passed (4 tests); repository and whitespace checks passed.
- Exact commands/source hashes/JUnit/stdout: evidence/contract-baseline-20261114.
  Generated-interface and actual PlanRoute tests run on Jazzy; MOCK-only guards
  do not establish full mission acceptance.
- Blockers: real public canonical dataset, numerical resource-model agreement,
  public evaluator leakage in web demo, gateway MOCK/LIVE provenance, existing
  TS replay strict validation, stop acknowledgement and owner-reported
  callback/search-limit performance. No operational feasibility is approved.
- Target publication is a reviewed reconciliation PR to main. Main was
  re-fetched before publishing; its observed SHA is004b3b2. The candidate remains
  unmerged and must not be reported as a published main baseline.

## PR #3 review corrections, 2026-11-14

- Owner-authorized corrections on `feat/integration`: `f46b3fc` rejects invalid
  numeric HTTP goal inputs; `ddc6f36` makes their HTTP 422 error details JSON-safe;
  `a8482c8` preserves valid late replay events with sequence-ordered snapshots.
- Reconciliation base is published main `b76c44f6f2386a810b4abc255d8f7945b81fb7a6`,
  after PRs #7/#4 merged externally. Their approved contracts/disclosures remain;
  no other open owner branch is merged or copied. ROS and JSON wire versions
  remain unchanged. The strict offline oracle now shares the late-event policy.
- Local combined tree: 354 Python tests pass, seven ROS modules skip on Windows;
  repository/whitespace checks and web tests (4)/build pass. ROS build/interface
  and consumer tests must pass on the final CI head before the requested merge.
  Exact commands, source references and remaining gates: [Jesus handoff](handoffs/jesus.md#pr-3-correction-and-reconciliation-cut).
- No new NASA observation, scientific model approval or validated LIVE mission
  is claimed. Internal hours remain outside Git.

## Real terrain providers against the planner, 2026-11-14

- Cut: PR #8 (`feat/data`, Daniel) with main `8afc7bf` merged in; integration
  review and corrections by Jesus.
- Finding: `data_node` and `mapping_node` both published TerrainMeta for map
  version 1 with different stamps, metadata went out after its layers, nothing
  was repeated, and an invalid observation raised inside the callback. The
  planner rejects same-version metadata with another stamp, so it would never
  have held a usable map.
- Correction: `mapping_node` is the only metadata publisher and sends the batch
  metadata-first under one stamp per map version, repeated every
  `repeat_period_s`; `data_node` publishes the prior only; invalid observations
  are logged and dropped; both nodes exit if the terrain cannot be loaded.
- Evidence: `tests/integration/test_terrain_batch.py` in the `mge-dev` Jazzy
  container. Before any observation every mask cell is unknown and the planner
  answers without a route. After one SIMULATED observation that repeats the
  prior heights of a 16 x 16 cell block, `mge_planning` returns a FEASIBLE rover
  route inside that block (illustrative profiles). This is plumbing on the
  public Jezero package, not a validated route or a mission run.
- Open for David: slope limits in `mapping_node` are placeholders; the 20 m CTX
  product is resampled to a 4 m grid. Next: a vertical launch on this terrain
  needs agent positions on its cell centres and the real mission provider.

## Typed serialization and source provenance, 2026-11-14

- Base: main `8afc7bf` (PR #3 merged). Owner: Jesus, on `feat/integration`.
- Gateway and recorder reject non-finite values outside the typed NaN cases of
  ICD section 5 instead of nulling them; `mock_planner` no longer emits NaN
  clearance on FEASIBLE routes. Manifests carry `source_mode`
  (MOCK/SIMULATION/UNKNOWN, never LIVE). Wire versions unchanged.
- Jazzy container `mge-dev`: 8 packages built; 426 tests passed, 20 of them ROS
  integration; repository check passed. Web suite not run (no web change).
- Next dependency: Jorge reads `source_mode` in the viewer; public raster
  recording; real mission provider. No mission run or scientific result here.
