# Jorge - preserve and adapt the existing 3D viewer

Active branch: **`feature/web-replay-viewer`**. Audited head: `73f22dba432ed69c351699c1d712f5d515df4c78` (HiRISE extraction script). Relevant viewer contract/replay increment: `9fa29dd` and `7396d54`; latest terrain smoothing is `ef84483`. Existing handoff is `web/README.md` on that branch, plus `docs/AI_DISCLOSURE.md` and `THIRD_PARTY_NOTICES.md`. `feat/ux` equals audited main and must not replace this implementation.

Read [AGENTS.md](../../AGENTS.md), [ICD](../ICD.md), [contract baseline](../CONTRACT_BASELINE.md) and [integration matrix](../INTEGRATION_MATRIX.md) before editing. Canonical ROS fields/types live in `src/mge_interfaces/msg` and `srv`; preserve them and adapt representations explicitly.

## Owned implementation and contracts

Preserve `web/src/components/`, existing scene/assets, astronaut, agents, terrain layers, route overlay, event inspector, timeline and visual experience. Own `web/src/data/replayAdapter.ts`, `web/src/types/`, display helpers/tests, `web/public/replay/`, asset notices and web data extraction scripts.

Consume canonical gateway/replay JSON `schema_version: 1.0.0` through the [deterministic replay adapter](../REPLAY_CONTRACT.md). Keep the existing `mge-web-0.1-draft` fixture format as an illustrative source until conversion is tested. Preserve ROS wire field names, route statuses/reasons and IDs. Convert ENU `(x,y,z)` to Three `(x,z,-y)` only at display. Display replay as REPLAY and retain MOCK source provenance; show NOT_READY/ERROR and never infer LIVE from a running gateway. No command is accepted from offline replay.

Only MissionManager authorizes the route. Do not calculate a replacement route, infer a task completion from animation, or turn UNKNOWN into a feasible state. The fixture generator's route search remains illustrative, outside operational mission/planner authority; label and preserve it accordingly.

## Dependencies, mocks and immediate blocker

Jesus supplies recorded canonical state/events and the adapter; Daniel supplies public prior/belief/sigma/observed layers and three georeferenced control points.

Gateway sample replay has no rasters: conversion must report that omission, never borrow rasters from a different dataset/run/map.

The current web terrain (~2 km / 20 m) differs from the planner provisional crop (~128 m / 4 m).

**Do not publish the current evaluator fixture.** `RasterSet.reference` and the bundled `rasters.json.reference` are downloadable, and `?evaluator=1` exposes them. A default-hidden layer is not isolation. Preserve the authored fixture in the work branch, quarantine it from public exports, change the public loader/type to accept no reference, and verify that neither reference values nor a separate reference file exists in the public build. Evaluator tooling stays isolated. Keep public assets/provenance and existing third-party licenses intact.

## Synchronize without losing existing work

After saving/reviewing local edits, use the existing worktree for this branch:

```sh
git status --short
git fetch origin --prune
git switch feature/web-replay-viewer
git pull --ff-only origin feature/web-replay-viewer
git log -1 --format=fuller origin/main
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- web docs/AI_DISCLOSURE.md THIRD_PARTY_NOTICES.md
git merge origin/main
```

If the branch is not local, use `git switch --track -c feature/web-replay-viewer origin/feature/web-replay-viewer` instead of switch/pull. Do not switch it if another worktree already has it checked out. Merge main only while on your owned branch. Stop to reconcile any shared-contract conflict with Jesus and the producer/consumer owners; preserve both implementations and never force-push. This reconciliation becomes the main contract only after its PR is merged. Before that, review it as a proposal and do not claim it is published in main.

## Tests and consumer evidence

First run from `web`: `npm ci` then `npm test`. Keep `coords.test.ts`, `replay.test.ts`, `management.test.ts`, `terrainSmooth.test.ts` and `astronaut.test.ts`; they preserve the current implementation. Run root `python -m pytest tests/contract/test_replay_conversion.py` after the baseline lands, followed by `npm run build`. Add a viewer test that loads the actual converted gateway package with Daniel's matching public raster sidecar; missing layers, stale versions and non-feasible states must fail/display clearly.

Serve the production build with backend stopped. Record the tested URL, run/dataset/map IDs, source MOCK/REPLAY labels, three control-point matches, timeline seek/event ordering, reasons, all invalid statuses and reference-free network/build asset inspection. Test a private browser and retain screenshots with required generated-asset watermarks. Existing legacy offline checks do not prove canonical replay compatibility.

## Acceptance and next delivery

Deliver an incremental PR from `feature/web-replay-viewer`, preserving the scene and all existing tests. Acceptance requires canonical conversion consumed by the existing viewer, explicit unavailable/error/source modes, no local planner, reference-free public output and three Daniel control points. First deliver the public raster type/loader correction and canonical fixture consumer; then record backend-off replay evidence. LIVE controls stay unavailable until Jesus supplies a reviewed real connection and MissionManager authorization flow.

## PR and handoff evidence

Include the tested source SHA, baseline/schema versions, dataset/run/map IDs, model/configuration hashes where relevant, exact commands/outcomes and links to immutable evidence. Name any MOCK provider and all skipped checks, with reasons. Run `python -m pytest`, `python scripts/check_repository.py`, and the frontend `npm ci`, `npm test`, `npm run build` where available, using `web/.nvmrc`. On Ubuntu 24.04/Jazzy, build with `colcon build --symlink-install`, source `install/setup.bash`, inspect the six messages/two services and run the ROS contract/integration tests. A Windows skip is not a passing ROS test.

Review `git status`, `git diff` and `git diff --check`. Keep commits atomic and English Conventional Commits; preserve Git identity, third-party rights and mandatory AI usage text/metadata/watermarks. Update `docs/AI_USAGE.md`, `docs/ai_usage.json` and your handoff. Do not upload secrets or evaluator data.
Jesus reviews integration; David approves scientific assumptions/success.
Software tests, replay and synthetic fixtures do not establish a validated
LIVE mission. No push, merge or release is implied by this handoff alone.
