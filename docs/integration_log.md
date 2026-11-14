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

## Vertical on the public Jezero terrain, 2026-11-14

- Base: `feat/integration` with main `7ec1a06` merged in (`0d1a27a`). Owner:
  Jesus.
- `vertical_mock.launch.py terrain:=real` replaces `mock_terrain` by
  `mge_data` + `mge_mapping`; it refuses to start without `planner:=real`, since
  a straight-line mock planner would hide unknown cells. Agents default to the
  placeholder `agents_jezero.yaml` on cell centres of the 4 m grid. Mission and
  agents stay MOCK and the gateway still declares `source_mode: MOCK`.
- Evidence: `tests/integration/test_vertical_terrain.py` in the `mge-dev` Jazzy
  container. One metadata publisher; a human goal on unobserved terrain ends
  `BLOCKED` with `UNKNOWN/UNVERIFIED_CORRIDOR` and no route; a SIMULATED
  observation that repeats the prior heights of a 16 x 16 block yields map
  version 2 and the MOCK mission replans to a `FEASIBLE` route inside the block
  (illustrative profiles); the recorded package passes `check_package`. Full
  suite: 447 passed (three consecutive runs); repository check passed.
- This is the map -> route -> view plumbing on public Jezero data, not a
  validated route or mission run. Next: the real `mge_mission` provider (PR #10)
  in this path, public raster recording, and survey observations from a
  simulated sensor instead of a test publisher.

## Real MissionManager handoff, 2026-11-14

OwnerDavid; integration/reviewJesus. Source255be89 preserves mission8f69f62 and
refreshes through main6ec9b84 after the externally merged data/endorsement cuts.
No original owner branch is overwritten. The PR supplies the existing real
mission module and exclusive mission:=mock|real selection, configuration/clock
preflight and real-consumer regressions. It does not remove the contractual mock
or redefine messages/services, approve models or synthesize completed missions.

Actual checks: Python636passed/15native skips; Jazzy8packages/8definitions,
556selected tests passed/one optional snapshot skip; ten focused selector/HTTP
consumer tests passed; web4tests/build and repository/diff checks passed.
Evidence: evidence/mission-service-handoff-20261114. Use the
[handoff](mission_integration_handoff.md) to replace mock_mission, never run it
alongside mission_node. Current test outcome remains MODEL_NOT_AGREED/BLOCKED;
science-model reconciliation and actual execution remain separate owner gates.

## Mission handoff sync after web merge

Incorporated main7ec1a06 into codex/mission-service-handoff after the owner merged
web PR #5. Resolved only README and AI metadata conflicts, retaining real mission
selection, existing viewer implementation, mandatory declarations and licences.
The moved provenance test is recorded at web/tests/provenance.test.ts.

Checks: Python636passed/15platform-or-optional skips; web npm ci,84Vitest cases
and TypeScript/Vite build passed; repository and whitespace checks passed.
No ROS interface, mission source or launch selector changed. npm audit reports
four inherited development-tool dependency alerts (one moderate, one high and
two critical); dependency versions were preserved from main for this sync.
The existing mission-service source evidence remains attached to its original
commit; this paragraph records the subsequent web/main synchronization.

### CI follow-up for the main synchronization

CI run43626302116 initially failed the inherited observed-terrain route case
with UNKNOWN/SEARCH_LIMIT. One failed-job rerun repeated it and also timed out
waiting for the mission model gate. ROS source/profiles were unchanged by the
web merge. Preserve these failed attempts as evidence; do not weaken FEASIBLE
or MODEL_NOT_AGREED assertions.

The coherent-terrain functional fixture now explicitly permits ten seconds of
search, with the same label cap and unchanged production two-second default.
The mission fixture waits for a canonical zero-distance planner candidate to
prove that the matching public batch/profile is loaded before sending a single
mission request. This candidate is never authorized as a mission route. The
actual mission must still reject non-agreed models and conflicting IDs, with no
active route. This separates functional plumbing from CPU-load timing and
cross-topic DDS startup ordering; it makes no latency or mission acceptance claim.

After those fixture corrections, fresh local validation again built eight Jazzy
packages/inspected eight definitions and passed556selected ROS/mission/contract/
HTTP cases (one optional published-snapshot skip). Ten focused launch/consumer
cases passed; native Python636passed/15platform-or-optional skips. Repository
and whitespace checks passed. Frontend84tests/build remain passed from the
unchanged merged viewer. Production planner and mission sources are unchanged.

The next CI passed the terrain fixture but the authority smoke's200x200 grid
still did not produce a ready planner within its fixture deadline. Diagnostics
retained the IDLE mission snapshot with no submitted goal. The authority smoke
now uses a test-only scoped16x16 grid (5m cells, same explicit positions) while
loading the actual production LaunchDescription and actual providers. The
manifest dimensions are asserted. Production providers/defaults remain unchanged.
Fresh Jazzy validation again passed10focused cases and556selected cases (one
optional snapshot skip), with eight packages built/eight definitions inspected.

## PR11 reconciliation against the integrated mission

Review incorporated main73a06b2, preserving mission:=real and terrain:=real,
source_mode=MOCK while agents remain mocks, both preflight gates and all
mandatory disclosures. Fixed the new terrain test import for main's importlib
mode. Added combination/guard coverage; no science approval is inferred.

Validation: native Python675passed/16platform-or-optional skips; eight Jazzy
packages built/eight interfaces inspected;15focused launch/mission cases passed;
605selected ROS/mission/unit/HTTP/integration cases passed with one optional
published-snapshot skip. Repository and whitespace checks passed. The viewer
accepts additive manifest fields and fails closed for non-flat recorded terrain
without rasters; full real-terrain browser playback remains a separate handoff.

## Public raster recording, 2026-11-14

- Base: main `059f8ef` (PRs #10 and #11 merged). Owner: Jesus, on
  `feat/integration`; JES-04.
- Gap found: the raster attachment needs the observed cells of each map
  version, and no ROS topic carried them. Deriving them from sigma or the
  traversability masks would be inference (an observed cell stays unknown when
  NoData or uncertain), so the owner chose an additive topic.
- Change: `/mge/terrain/observed` (`mono8`) joins the stamped batch of
  `mapping_node` and `mock_terrain`; `mock_terrain` also publishes its flat
  prior. The recorder assembles prior plus belief/sigma/observed per version
  by stamp and writes `public_rasters.json`; `check_replay` and the oracle read
  it. No message or field changed; the planner does not subscribe to the topic.
- Evidence in the `mge-dev` Jazzy container: the Jezero vertical package holds
  versions 1 (nothing observed, belief equal to the prior) and 2 (exactly the
  observed 16 x 16 block) and the oracle converts it READY with an all-null
  reference; the MOCK vertical package also converts READY. Full suite: 805
  passed, 1 skipped; non-ROS suite on Python 3.12: 730 passed, 13 skipped;
  repository check passed.
- Open: Daniel reviews the `mapping_node` change and Jorge the consumer; the
  viewer must read `public_rasters.json` instead of rejecting non-flat terrain.
  `test_terrain_batch.py::test_planner_routes_inside_the_observed_block` fails
  intermittently with `UNKNOWN/SEARCH_LIMIT` after its 10 s search budget while
  the batch repeats at 1 Hz (planner finding 1, now on a 32 x 32 grid); passes
  in other runs. For Diego.

## MOCK kinematic execution and stop acknowledgement, 2026-11-14

- Base: main `7d9a3bf` (PR #14 merged, no conflict). Owner: Jesus, on
  `feat/integration`; JES-02, first part.
- `kinematic_executor` (`agents:=kinematic`) replaces `mock_agents`. The primary
  agent follows the active path only when it matches the authorized route of
  MissionState and starts at the agent's XY; height comes from the path (belief
  z, as in David's approved Jezero base value). Speed and consumption are the
  constant rates of the route's own estimates. On a cleared or changed route
  or path it halts in place and publishes `HALTED` with zero velocity: the stop
  acknowledgement uses existing AgentState fields, no contract change.
- Evidence (`mge-dev` Jazzy, `test_vertical_execution.py`, Jezero terrain, real
  planner, MOCK mission): a 2-cell route is driven there and back on the
  polyline; energy and oxygen fall by the route estimates (rel 1e-3); a second
  route is invalidated by map version 3, the human halts at (-9.64, -9.64),
  off the cell centres, and stays put; the replan is `ERROR/NON_CELL_CENTER`.
  The launch contract test now also checks agent-provider exclusivity. Full
  suite: 844 passed, 1 skipped; non-ROS Python 3.12: 756 passed, 14 skipped.
- Open: replan from a halted off-centre pose needs PR #12 (continuous ground
  starts); the real mission needs model agreement before it publishes a path;
  robots, survey observations and Gazebo remain pending. ICD section 7 wording
  for the acknowledgement waits for PR #12, which edits the same section.

## CI failures on main and PR #17, 2026-11-14

Follow-up: the callback correction below supersedes the 5 s / 60 s mitigation.

- `test_terrain_batch.py::test_planner_routes_inside_the_observed_block`
  timed out waiting for the PlanRoute answer on main (`7d9a3bf`, `70cd2e5`)
  and on PR #17; not caused by either change and not reproduced locally. The
  test repeated the map batch at 1 Hz while the planner searched (finding 1);
  it now uses the node default of 5 s and waits up to 60 s for an answer with
  a 10 s search budget. The FEASIBLE assertion is unchanged. For Diego.
- Reproducing the CI order locally exposed two flakes of PR #13 in
  `test_replay_package.py`: the run could stop before the 200 x 200 raster
  attachment was written (the test now waits for it), and the strict oracle
  rejected a MissionState that lagged the recorded map in arrival order
  (`STALE_STATE`). The oracle now accepts lag and rejects a state ahead of
  the map; REPLAY_CONTRACT documents it.

## PR17 callback scheduling correction, 2026-11-14

Source: failed head `17eb644bc8dc069a785066165904e3f7d691314f`, reconciled
with the integration owner's `bec3873` and published main `70cd2e5`. ROS
ICD-ROS2-V1/package 1.0.0, JSON/replay 1.0.0 and baseline 1.0.0-rc.1 remain
unchanged. No open planner PR or pending local replay work was imported.

- Original failure: no PlanRoute answer within 20 s, not a returned
  SEARCH_LIMIT. The fixture runs data/mapping/planning without the executor.
  Nineteen local runs at 1 Hz passed (six on one CPU); the original complete
  integration suite passed 39 tests. CI discarded child logs, so its exact
  thread schedule cannot be reconstructed retrospectively.
- At 100 Hz, the failed source reproduced the same `req-observed` timeout
  (5 passed, 1 failed). Thread dumps showed four ingestion workers competing
  at SnapshotStore's lock; the second service callback never entered. This
  confirms a starvation mechanism, not that CI produced at 100 Hz or suffered
  a particular CPU fault. Reentrant ingestion can consume service capacity.
- Map callbacks now share one mutually exclusive group, separate from a
  mutually exclusive service group. Updates remain concurrent with search;
  the snapshot-token guard still discards stale results. No search math,
  resource model, observation policy or wire field changed.
- A controlled delayed-ingestion regression fails the original node's 3 s
  service deadline and passes the correction. A second test publishes a new
  map during paused search and requires STALE_MAP with no route. Both use
  actual ROS service/subscription/executor dispatch. Jezero now runs at both
  1 and 100 Hz with the original 20 s wait and FEASIBLE/in-footprint checks;
  all 14 focused cases passed in 13.04 s. Child logs use pytest files instead
  of undrained pipes and are printed on failure.
- The owner's already-pushed replay ordering/raster-wait changes remain.
  MOCK execution, science agreement, continuous starts (PR12), M04/M05 and
  organizer endorsement retain their existing pending status.
- Final local validation on Ubuntu 24.04 / ROS 2 Jazzy, isolated domain 198:
  `colcon build --symlink-install` built all 8 packages; `ros2 interface show`
  inspected all six custom messages and both services; `python -m pytest -q`
  passed 853 tests, with one skip for the unmaterialized independent planner
  snapshot (78.26 s). `python scripts/check_repository.py` passed. On Windows
  Python 3.12 the same suite passed 753 with 19 ROS/platform/snapshot skips;
  Node 24.18.0 `npm test` passed 84 and `npm run build` passed. A FastAPI/httpx
  deprecation warning is unrelated. CI of the final pushed head remains the
  merge gate; these local checks do not establish LIVE mission acceptance.

## Integration test isolation, 2026-11-14

- Base: main `5ab1387` (PRs #12 and #17 merged). Owner: Jesus.
- Finding: every integration module launched its graph in one ROS domain, so
  a module could start while DDS still listed the previous module's nodes;
  with fewer CPUs, launch tests of several owners failed in sequence but not
  alone. Fixtures also sent goals before the planner service existed
  (`PLANNER_UNAVAILABLE`) and before the mission held the map (`NO_MAP`).
- Change: `tests/integration/conftest.py` gives each module its own
  `ROS_DOMAIN_ID` (from 60; explicit domains such as 173 are kept) and a
  `planner_ready` fixture; the five launch fixtures of the integration owner
  wait for the planner service, the mission's map and, before observing,
  for version 1 rasters to be recorded.
- Evidence (`mge-dev`, CPUs pinned to two): before, almost every run of
  `tests/integration` failed somewhere; after, 47 passed in normal runs and
  most pinned runs. Still intermittent under two pinned CPUs: the fixture of
  `test_vertical_mission.py` (David) and `test_vertical_planner.py` on the
  200 x 200 MOCK grid (planner load; Diego). Not seen with all CPUs.
