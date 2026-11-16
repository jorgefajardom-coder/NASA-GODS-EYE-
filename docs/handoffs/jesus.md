# Jesus - integrate providers through the canonical interfaces

## PR49 experimental Gazebo correction cut — 15 November 2026

Owner-requested corrections are prepared over PR49 source
`53cef780a35af6027f8af9aa3688d291a8977996`; inspected main is
`f5116685077d6c95f96bfab3a6b31d6a71ea6e5d`. The initial diagnosis and native
validation over `afb25b9` are historical; the correction was reconciled with
Jorge's concurrent world/model/datum work and the published PR50 migration.
This cut changes no ROS message/service,
unit, enum, canonical JSON/replay 1.0.0 or `mge-public-rasters-1.0.0` version.
Interface package remains 2.0.0 and baseline review 2.0.0-rc.1, not frozen.
The nine definitions include RegisterPlanningContext. Keep the author's history and use
the reviewed PR path. No owner-PR merge or deployment is authorized by this cut.

- **Inputs/outputs:** source-stamped Gazebo odometry, authoritative MissionState
  and matching Path produce measured AgentState and brake/follow commands.
  The existing public stamped batch confirms SIMULATED sensor footprints;
  metadata advancement alone confirms nothing. Recorder masks retain exact
  version/stamp and validated grid geometry. No evaluator reference is consumed.
- **Changes:** current finite XYZ and immutable route context, full measured
  orientation/twist, a steady-clock watchdog and a measured stop window replace
  stale-data reuse and frozen poses. Scene reports are serialized, rejected or
  expired acquisitions remain unconfirmed, and new reports require fresh pose
  acquisition. Pure helpers remain testable without ROS. The opt-in
  `gazebo_mock.launch.py` binds one physical rover, kinematic companions, an
  advancing bridged clock and the existing MOCK mission, without sending goals.
  The MOCK caller uses legacy planning only with explicit
  `allow_legacy_cost_model:=true`; this does not impersonate the scientific
  registered-context producer accepted in D-COST-03. Jorge's datum comparison
  remains diagnostic; authoritative height is not projected onto the DEM.
- **Reproduction:** use the [scenario guide](../../scripts/live_scenarios/README.md)
  with ROS 2 Jazzy/Ubuntu 24.04 and Gazebo Harmonic. Run `python -m pytest`,
  `python scripts/check_repository.py`, web `npm test`/`npm run build`,
  `colcon build --symlink-install`, all nine `ros2 interface show` commands,
  ROS contract/consumer tests and the explicit Gazebo runtime smoke. Final
  command outcomes, source/configuration hashes and limits are retained in the
  correction evidence; successful builds alone do not close mission acceptance.
- **Outcomes:** native Python 1,478 passed / 32 skipped; web 421 passed /
  1 skipped and build passed. Jazzy built eight packages and inspected six
  messages plus three services. Contract/adaptor checks passed 274 cases;
  the final sensor overlay passed four cases; integration passed 52 cases.
  The actual Gazebo wrapper had one clock publisher and one state publisher
  per agent, no fabricated pause telemetry, resumed measured telemetry and
  a valid closed recorder package. No goal was sent by that smoke. The later
  historical scenario CLI adaptation was statically checked, not executed as
  a complete sortie. See [validation](../../evidence/pr49-gazebo-corrections-20261115/validation.json),
  [source lock](../../evidence/pr49-gazebo-corrections-20261115/source-lock.json)
  and [runtime observations](../../evidence/pr49-gazebo-corrections-20261115/wrapper-smoke.json).
- **Limits/next:** the connected web panel remains read-only status; obstacle
  geometry is consumed from a recorded package. Scene lookup is not Gazebo
  camera/LiDAR perception. Historical drone sightings keep their acquisition
  context; landing samples only the current footprint. Full drone survey,
  scientific coefficient approval, three-role mission completion and the exact-run
  stop/replan/reauthorize/closed-replay chain still require owner-reviewed evidence.
  Jesus reviews integration; David reviews physical/scientific thresholds,
  resources and success criteria. No validated LIVE or submission readiness is claimed.
  RouteDecision reserve fields are estimated residuals, not the requested
  minimum reserves. Runtime enforcement of requested mission reserves requires
  the proper mission/context consumer; the driver does not redefine those fields.
- **Delivery coordination:** JES-07/AC-10 organizer notification and explicit
  endorsement of the final submission revision remain required while evidence
  is missing. Jesus coordinates, David backs up; preserve at least four hours of
  review margin or the organizer's longer requested lead time. Do not infer approval.

Future guide: [science extension tree](../science_extension_tree.md). Jesus
leads G2, C2/C3 and F2/F3 proposals and reviews integration evidence. Maintain
D-DEL-03 and verified parent gates. New unlisted ideas may be assessed in an
isolated local branch for discussion on 15-Nov-2026 (Bogota), without publishing
an extension, deployment or displacement of delivery work.

## Delivery priority after PR28 — owner-confirmed 14 November 2026

Follow [PDF tasks JE-1..5](../delivery_closure_plan.md) and accepted
[D-DEL-03](../decisions/2026-11-14-delivery-freeze.md). Basic reconciliation
is published at main9198b3d; semantic/scientific freeze and three-role acceptance
remain open. Confirm organizer availability/cutoff by 08:00, select run/fallback
with David by 10:00, freeze features at 12:00 and send the reviewable package
at 14:00 for intended submission at 20:00 on 15 Nov, all Bogota time. Preserve
at least four hours' review margin, explicit endorsement and platform receipt.
Initial organizer contact need not wait for a package. Publish tested fixes and
honest artifacts, not the pending local cost backend or new expansion scope.

## Audit reconciliation rc.2 — current candidate over main6bcf208

Read the [current gap/evidence matrix](../audit_reconciliation.md) and
[cost/context/interval proposal](../audit_cost_execution_gaps.md) first.
PR19/21 are integrated; preserve their recorder, strict viewer and acknowledged
continuous recovery. Next deliverable: review current-base/nonolder observation
filtering and versioned estimated-map policy with Daniel/Diego, then bind explicit
activity/wait/model context and accepted execution evidence to real MissionNode.
Reuse the scientific EvidenceRecorder; do not create a second mission authority
or journal. Three role commands, service/wait debit and optional public discovery
remain open. The featured MOCK human recovery is a same-run software cut only.
Historical scaffold/raster/stop gaps below retain their original dates; consult
the current evidence before repeating work. Organizer endorsement is still a
delivery/readiness gate under AGENTS.md section 15, not closed by this cut.

## Current continuation — 14 November 2026, main 5ab1387

Follow [CONT-JES-01..05](../team_continuation_plan.md#jesús--three-role-execution-recording-and-deployment-integration):
bind three executed roles and typed evidence with David; connect confirmed
stop/replan/reauthorization with Diego; close linked scientific/gateway packages
for one run. Co-own reproducible site deployment with Fajardo. Coordinate
organizer notification/explicit endorsement under JES-07; David is backup.
Historical inventories below retain their original revision and limitations.

PR17 timeout follow-up: `docs/integration_log.md` records the failed source
`17eb644`, reconciliation with `bec3873` / main `70cd2e5`, reproduced worker
starvation, callback-group correction and before/after ROS regressions. Map
ingestion and search retain concurrent stale-map invalidation. The terrain
fixture tests 1 and 100 Hz under its original 20 s response deadline. No open
PR12 or pending local replay/viewer work is included. Next delivery remains
the real integrated execution/replan and same-run replay evidence; current
MOCK tests do not satisfy M04/M05 or scientific acceptance. Organizer
notification/endorsement (JES-07) remains undocumented.

Active branch: **`feat/integration`**. Audited head: `45a4590f8e8330a3896c170ec2c9ee272ae0b423` at the final refresh; initial head
was `d28f3e2`. PR #3 remains the integration review front. Main PR #2 merged
externally and is included in this branch. Recorder increment: `74ed6f3`; replay documentation: `02f4155`. Existing handoffs: `src/mge_gateway/README.md`, `src/mge_sim/README.md`, `docs/ICD.md`, `docs/integration_log.md` and PR #3. The removed `dev/jesus` remote branch is not a new front; its work is preserved here.

Read [AGENTS.md](../../AGENTS.md), [ICD](../ICD.md), [contract baseline](../CONTRACT_BASELINE.md) and [integration matrix](../INTEGRATION_MATRIX.md) before editing. Canonical ROS fields/types live in `src/mge_interfaces/msg` and `srv`; preserve them and adapt representations explicitly.

## Owned implementation and contracts

Own `src/mge_interfaces/`, `src/mge_gateway/`, `src/mge_bringup/`, `src/mge_sim/`, ROS integration adapters, `docs/ICD.md`, CI and integration checks. Preserve the ROS-backed gateway/store/recorder and existing MOCK vertical. Do not copy planner or mission algorithms into the gateway or mocks. Gateway consumes authoritative MissionState/MissionEvent/TerrainMeta and emits JSON 1.0.0 with explicit oxygen NaN -> null conversion; other nonfinite values must be rejected. Recorder emits canonical manifest.json/timeline.jsonl/ snapshot.json and public layer associations as specified in [REPLAY_CONTRACT](../REPLAY_CONTRACT.md). Gateway has no independent mission state machine. It may cache/replay authoritative state, not authorize routes. Preserve IDs, map version and event seq; identical requests are idempotent, conflicting reuse is rejected rather than silently treated as a new command. PlanRoute serves candidates only. MissionManager alone publishes `/mge/planner/active_path`, authorizes route ID and handles return policy. On a changed map, an old route ID/path must be invalidated before new motion; empty Path/route ID is a logical stop command, not a physical acknowledgement.

## Dependencies and provider replacement

The current `vertical_mock.launch.py` already selects `planner:=mock/real`
exclusively; `a65af30` and `4cf587a` add real PlanRoute plumbing/tests.
`1ba60a4` supplies coherent synthetic terrain and `d03e330` puts agents on
cell centres. Preserve these implementations. The actual planner is now main;
David's actual `feat/mission` manager still requires integration gates. Daniel owns coherent public map batches. Each native image/mask batch needs the same frame/stamp and unambiguous run/dataset/version metadata; repeat complete batches for DDS ordering and reject stamp reuse or mixed layers. Expose separate `mock`, `integration`, and `live/simulation` launch profiles. There must be exactly one server for each canonical service. Retain the implemented exclusive planner switch; extend configuration-based
replacement to the real mission/data producers, never launch two providers
with the same service name. A live/simulation request without real providers/data/model approval must be NOT_READY, not fallback to mocks. Keep scenario seeds, inputs and outputs deterministic, with visible MOCK provenance and SIMULATED observations. The current sample `recorded_from: LIVE` describes transport but its sources are MOCK; preserve source classification explicitly in export/display. Scientific model agreement, continuous pose rejection and real execution input bindings remain gates. Do not change .msg/.srv fields just to suit a consumer.

## Synchronize without losing existing work

After saving/reviewing local edits, use the existing worktree for this branch:

```sh
git status --short
git fetch origin --prune
git switch feat/integration
git pull --ff-only origin feat/integration
git log -1 --format=fuller origin/main
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- src/mge_interfaces src/mge_gateway src/mge_bringup src/mge_sim docs/ICD.md
git merge origin/main
```

If the branch is not local, use `git switch --track -c feat/integration origin/feat/integration` instead of switch/pull. Do not switch it if another worktree already has it checked out. Merge main only while on your owned branch. Stop to reconcile any shared-contract conflict with Jesus and the producer/consumer owners; preserve both implementations and never force-push. This reconciliation becomes the main contract only after its PR is merged. Before that, review it as a proposal and do not claim it is published in main.

## Tests and real consumer check

First run `python -m pytest tests/unit tests/contracts/test_gateway.py tests/integration` on the integration branch. After baseline merge, also run `python -m pytest tests/contract/test_baseline_guards.py tests/contract/test_replay_conversion.py tests/contract/test_dataset.py tests/integration/test_provider_substitution.py`.

Also retain `tests/integration/test_vertical_planner.py`, which now covers
actual PlanRoute behind MOCK terrain/mission. Its reported results are
contributor evidence, not a fresh run of this reconciliation. The latest log
reports repeated-layer callback stalls at 60 x 60 and larger, a short-budget
case ending UNKNOWN/SEARCH_LIMIT, and default search bounds on 500 m requests.
Investigate with Diego; preserve explicit UNKNOWN rather than infer infeasibility.

Build/source Jazzy and run `python3 -m pytest tests/contract tests/integration`. Inspect all eight generated interfaces; retain graph/service provider counts. Record one fixed request through the same MissionManager consumer with a conforming MOCK planner, then the real PlanRoute server. Compare schema/status/ IDs and authority behavior, not invented identical route numerics. Repeat with real MissionManager replacing mock mission. Exercise stale result, duplicate request/event, conflicting ID reuse, map change, empty-path invalidation and executor acknowledgement separately. Run offline recorder validation and pass its converted replay to Jorge's actual viewer with matching public layers.

## Acceptance and next delivery

First reconcile PR #3 with the baseline and preserve its tested gateway; preserve existing real-planner option and coherent synthetic publisher, then
complete source MOCK labeling, exclusive mission/data profiles, public raster
recording/association and real-manager consumer checks. Then integrate real planner/mission after David/Diego model agreement and Daniel data delivery. Acceptance requires one mission authority, one provider/service, fail-closed unavailable modes, no hidden reference, and immutable exact-source evidence. Do not merge PRs #2/#3/#4 or the web branch automatically.

## PR and handoff evidence

Include the tested source SHA, baseline/schema versions, dataset/run/map IDs, model/configuration hashes where relevant, exact commands/outcomes and links to immutable evidence. Name any MOCK provider and all skipped checks, with reasons. Run `python -m pytest`, `python scripts/check_repository.py`, and the frontend `npm ci`, `npm test`, `npm run build` where available, using `web/.nvmrc`. On Ubuntu 24.04/Jazzy, build with `colcon build --symlink-install`, source `install/setup.bash`, inspect the six messages/two services and run the ROS contract/integration tests. A Windows skip is not a passing ROS test.

Review `git status`, `git diff` and `git diff --check`. Keep commits atomic and English Conventional Commits; preserve Git identity, third-party rights and mandatory AI usage text/metadata/watermarks. Update `docs/AI_USAGE.md`, `docs/ai_usage.json` and your handoff. Do not upload secrets or evaluator data.
Jesus reviews integration; David approves scientific assumptions/success.
Software tests, replay and synthetic fixtures do not establish a validated
LIVE mission. No push, merge or release is implied by this handoff alone.

## PR #3 correction and reconciliation cut

The repository owner explicitly requested the two review fixes and conditional
merge of PR #3. Input fixes `f46b3fc` and `ddc6f36` reject non-finite goal/base
coordinates and invalid explicit float32 budgets/reserves with JSON-safe HTTP
422 before ROS forwarding. Replay fix `a8482c8` retains late events in receipt
order, compares snapshots in logical sequence order, and rejects conflicting or
invalid event sequences. Regression requests/events are illustrative test inputs.

This cut reconciles that tested head `ddc6f3665d96b93b9cca1bd6715d3df50da35136`
with published main `b76c44f6f2386a810b4abc255d8f7945b81fb7a6` (PRs #7 and #4
already merged). No open planner, mission, data or viewer branch is imported.
ROS remains ICD-ROS2-V1/package 1.0.0; canonical JSON/replay remains 1.0.0 and
baseline review remains 1.0.0-rc.1, not frozen. The strict replay oracle follows
the same late-event policy and is exercised through the actual ReplayWriter
and viewer conversion. Source/arrival timestamps, run identity, duplicate guards,
public-raster requirements and evaluator isolation checks are preserved.

Local validation: Python 3.12.14 `python -m pytest --basetemp
tmp/pr3-merge-pytest-20261114-01` passed 354 tests; seven ROS-dependent modules
skip on Windows. A fresh workspace temporary directory avoids the machine's
existing inaccessible pytest temp root. `python scripts/check_repository.py`,
`git diff --check`, web `npm test` (4 tests) and `npm run build` passed. Existing
Starlette deprecation and web bundle-size warnings remain. Ubuntu 24.04/Jazzy
build, generated-interface inspection and ROS integration execution are CI gates
on the final PR head before merge; consult PR #3's checks for that exact SHA.

Remaining real acceptance is unchanged: public rasters/dataset, source provenance,
strict output serializer adoption, scientific model agreement, real mission
provider/current-pose binding and stop acknowledgement. These fixes establish
input/replay regression behavior, not scientific or validated LIVE acceptance.

## Typed serialization and source provenance cut

Two of the remaining gateway gates are closed on `feat/integration`, on top of
main `8afc7bf` (PR #3 merged). ROS stays ICD-ROS2-V1/package 1.0.0 and JSON
stays 1.0.0; `source_mode` is an optional added field, not a version change.
That choice needs Jorge's confirmation as the consumer before it is called agreed.

- **Output serializer.** `store.state_json`, `event_json` and `meta_json`
  replace the broad NaN/infinity-to-null conversion in the gateway and the
  recorder. A message with a non-finite value outside the three typed cases is
  dropped whole and logged with its field path (ICD 6.1). `mock_planner` set
  `min_clearance_m = NaN` on FEASIBLE routes, which the contract forbids; it now
  reports `0.0`, the lower bound, since the mock evaluates no clearance.
- **Source provenance.** The gateway manifest and recorded manifests carry
  `source_mode`. `vertical_mock.launch.py` and the `mock`/`integration` profiles
  declare MOCK, `simulation` declares SIMULATION, and LIVE cannot be declared.

Validation in the `mge-dev` Jazzy container, on the working tree of this cut:
`colcon build --symlink-install` built 8 packages; `python3 -m pytest` passed
426 tests, including the 20 in `tests/integration` (mock vertical, real planner
vertical and replay package); `python3 scripts/check_repository.py` passed.
Web tests and build were not run: no file under `web/` changed.

Still open: public raster recording, the real `mge_mission` provider behind
the unchanged gateway consumer, stop acknowledgement, and viewer adoption of
`source_mode` (PR #5 prints `recorded_from` and a fixed MOCK disclaimer). These fixes are
serialization and labelling behavior, not scientific or LIVE acceptance.

## Jezero terrain vertical cut

Source: `feat/integration` after merging main `7ec1a06` (`0d1a27a`). Baselines
unchanged: ROS ICD-ROS2-V1/package 1.0.0, JSON/replay 1.0.0, baseline review
1.0.0-rc.1 (not frozen). Dataset `jezero_mvp` from `data/sample/manifest.json`.

- **Input/output.** `vertical_mock.launch.py terrain:=real planner:=real
  profiles_file:=<json>` runs `data_node` (prior) and `mapping_node` (the only
  TerrainMeta publisher) instead of `mock_terrain`, with the real planner, the
  MOCK mission/agents, the gateway and optionally the recorder. `terrain:=real`
  with the mock planner fails `NOT_READY: REAL_TERRAIN_REQUIRES_REAL_PLANNER`.
  Agents default to `src/mge_bringup/config/agents_jezero.yaml` (placeholders).
- **Outcome.** Unobserved terrain answers `UNKNOWN/UNVERIFIED_CORRIDOR` and the
  mission is `BLOCKED` without a route; a SIMULATED observation over a 16 x 16
  block yields map version 2 and a `FEASIBLE` route inside it through REST; the
  recorded package passes `check_package` with `source_mode: MOCK`.
  `terrain:=real planner:=mock` is refused before any node starts.
- **Commands.** In `mge-dev`: `colcon build --symlink-install`, then
  `python3 -m pytest` (447 passed in three consecutive runs, including
  `test_vertical_terrain.py`) and
  `python3 scripts/check_repository.py` (passed). Web on Node 24.18.0 after the
  main merge: `npm ci`, `npm test` (84 passed), `npm run build` (passed).
- **MOCK and gaps.** Mission and agents are MOCK; the observation comes from
  the test, not from a simulated sensor; profiles and slope limits are
  illustrative/placeholder pending David. Not run: Gazebo, real mission.
- **Blockers / next.** PR #10 (real `mge_mission`) also edits
  `vertical_mock.launch.py`; reconcile both selections when it is reviewed.
  Then public raster recording (JES-04) and survey observations from the
  simulated drone (JES-02). No mission or scientific acceptance is claimed.

## Public raster recording cut (JES-04)

Source: `feat/integration` on main `059f8ef`. Baselines: ROS ICD-ROS2-V1 /
package 1.0.0 with one proposed additive topic, JSON/replay 1.0.0 with one
optional file, raster attachment `mge-public-rasters-1.0.0`, baseline review
1.0.0-rc.1 (not frozen). Dataset `jezero_mvp`.

- **Input.** `/mge/terrain/prior` and the stamped batch: metadata, belief,
  sigma and the new `/mge/terrain/observed` (`mono8`, published by
  `mapping_node` and `mock_terrain`). Owner decision recorded: additive topic
  instead of inferring coverage from sigma or masks.
- **Output.** `<run_id>/public_rasters.json`, named by `files.public_rasters`;
  `read_public_rasters` and `check_replay` validate it; `to_viewer` turns the
  package READY. Version 0 needs no raster; extra keys only for recorded
  TerrainMeta versions; no nearest-version fallback.
- **Commands.** In `mge-dev`: `colcon build --symlink-install`,
  `python3 -m pytest` (805 passed, 1 skipped), `python3 scripts/check_repository.py`
  (passed). Python 3.12 without ROS: `python -m pytest` (730 passed, 13 skipped).
- **MOCK and gaps.** Mission and agents MOCK; observations come from tests.
  The viewer does not read the attachment yet. Not run: Gazebo, real mission
  with model agreement.
- **Blockers / next.** Daniel reviews the `mapping_node` publisher, Jorge the
  consumer (JOR-03). Intermittent planner `SEARCH_LIMIT` in
  `test_terrain_batch.py` goes to Diego. Next for Jesus: JES-02 kinematic
  execution and stop acknowledgement. Organizer endorsement (JES-07) remains
  undocumented.

## MOCK kinematic execution cut (JES-02, first part)

Source: `feat/integration` on main `7d9a3bf`. Baselines unchanged: ROS
ICD-ROS2-V1 / package 1.0.0, JSON/replay 1.0.0, baseline review 1.0.0-rc.1.

- **Input/output.** Input: MissionState (route ID, primary agent, active
  route and estimates) and `/mge/planner/active_path`. Output: AgentState for
  every agent; the primary one `MOVING` along the path, `IDLE` on arrival,
  `HALTED` with zero velocity after an invalidation (stop acknowledgement).
  Selected by `agents:=kinematic`; exclusive with `mock_agents`.
- **Commands.** In `mge-dev`: `colcon build --symlink-install`,
  `python3 -m pytest` (844 passed, 1 skipped), `python3 scripts/check_repository.py`
  (passed). Python 3.12 without ROS: 756 passed, 14 skipped.
- **MOCK and gaps.** Executor, mission and agents MOCK; motion is constant
  speed from route estimates. Not run: real mission path (needs model
  agreement), Gazebo, robots, survey observations from a simulated sensor.
- **Blockers / next.** PR #12 for replanning from a halted off-centre pose and
  for the ICD section 7 acknowledgement wording; real mission once David and
  Diego agree the model; M04/M05 runs with David. JES-07 organizer endorsement
  remains undocumented.
