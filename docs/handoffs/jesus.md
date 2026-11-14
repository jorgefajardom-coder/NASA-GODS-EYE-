# Jesus - integrate providers through the canonical interfaces

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
