# Jesus - integrate providers through the canonical interfaces

Active branch: **`feat/integration`**. Audited head: `d28f3e23f268d50c6c55f2b1f85a1cadbe9281ed`; PR #3 is open, not merged. Recorder increment: `74ed6f3`; replay documentation: `02f4155`. Existing handoffs: `src/mge_gateway/README.md`, `src/mge_sim/README.md`, `docs/ICD.md`, `docs/integration_log.md` and PR #3. The removed `dev/jesus` remote branch is not a new front; its work is preserved here.

Read [AGENTS.md](../../AGENTS.md), [ICD](../ICD.md), [contract baseline](../CONTRACT_BASELINE.md) and [integration matrix](../INTEGRATION_MATRIX.md) before editing. Canonical ROS fields/types live in `src/mge_interfaces/msg` and `srv`; preserve them and adapt representations explicitly.

## Owned implementation and contracts

Own `src/mge_interfaces/`, `src/mge_gateway/`, `src/mge_bringup/`, `src/mge_sim/`, ROS integration adapters, `docs/ICD.md`, CI and integration checks. Preserve the ROS-backed gateway/store/recorder and existing MOCK vertical. Do not copy planner or mission algorithms into the gateway or mocks. Gateway consumes authoritative MissionState/MissionEvent/TerrainMeta and emits JSON 1.0.0 with explicit oxygen NaN -> null conversion; other nonfinite values must be rejected. Recorder emits canonical manifest.json/timeline.jsonl/ snapshot.json and public layer associations as specified in [REPLAY_CONTRACT](../REPLAY_CONTRACT.md). Gateway has no independent mission state machine. It may cache/replay authoritative state, not authorize routes. Preserve IDs, map version and event seq; identical requests are idempotent, conflicting reuse is rejected rather than silently treated as a new command. PlanRoute serves candidates only. MissionManager alone publishes `/mge/planner/active_path`, authorizes route ID and handles return policy. On a changed map, an old route ID/path must be invalidated before new motion; empty Path/route ID is a logical stop command, not a physical acknowledgement.

## Dependencies and provider replacement

Use Diego's actual `feat/planner` server and David's `feat/mission` manager when their integration gates pass; preserve those implementations. Daniel owns coherent public map batches. Each native image/mask batch needs the same frame/stamp and unambiguous run/dataset/version metadata; repeat complete batches for DDS ordering and reject stamp reuse or mixed layers. Expose separate `mock`, `integration`, and `live/simulation` launch profiles. There must be exactly one server for each canonical service. Replace mock planner/mission through configuration, never launch both with the same service name. A live/simulation request without real providers/data/model approval must be NOT_READY, not fallback to mocks. Keep scenario seeds, inputs and outputs deterministic, with visible MOCK provenance and SIMULATED observations. The current sample `recorded_from: LIVE` describes transport but its sources are MOCK; preserve source classification explicitly in export/display. Scientific model agreement, continuous pose rejection and real execution input bindings remain gates. Do not change .msg/.srv fields just to suit a consumer.

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

Build/source Jazzy and run `python3 -m pytest tests/contract tests/integration`. Inspect all eight generated interfaces; retain graph/service provider counts. Record one fixed request through the same MissionManager consumer with a conforming MOCK planner, then the real PlanRoute server. Compare schema/status/ IDs and authority behavior, not invented identical route numerics. Repeat with real MissionManager replacing mock mission. Exercise stale result, duplicate request/event, conflicting ID reuse, map change, empty-path invalidation and executor acknowledgement separately. Run offline recorder validation and pass its converted replay to Jorge's actual viewer with matching public layers.

## Acceptance and next delivery

First reconcile PR #3 with the baseline and preserve its tested gateway; implement explicit source MOCK labeling, exclusive launch providers, public raster recording/association and replacement consumer checks. Then integrate real planner/mission after David/Diego model agreement and Daniel data delivery. Acceptance requires one mission authority, one provider/service, fail-closed unavailable modes, no hidden reference, and immutable exact-source evidence. Do not merge PRs #2/#3/#4 or the web branch automatically.

## PR and handoff evidence

Include the tested source SHA, baseline/schema versions, dataset/run/map IDs, model/configuration hashes where relevant, exact commands/outcomes and links to immutable evidence. Name any MOCK provider and all skipped checks, with reasons. Run `python -m pytest`, `python scripts/check_repository.py`, and the frontend `npm ci`, `npm test`, `npm run build` where available, using `web/.nvmrc`. On Ubuntu 24.04/Jazzy, build with `colcon build --symlink-install`, source `install/setup.bash`, inspect the six messages/two services and run the ROS contract/integration tests. A Windows skip is not a passing ROS test.

Review `git status`, `git diff` and `git diff --check`. Keep commits atomic and English Conventional Commits; preserve Git identity, third-party rights and mandatory AI usage text/metadata/watermarks. Update `docs/AI_USAGE.md`, `docs/ai_usage.json` and your handoff. Do not upload secrets or evaluator data.
Jesus reviews integration; David approves scientific assumptions/success.
Software tests, replay and synthetic fixtures do not establish a validated
LIVE mission. No push, merge or release is implied by this handoff alone.
