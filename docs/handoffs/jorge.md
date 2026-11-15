# Jorge - preserve and adapt the existing 3D viewer

## Audit reconciliation rc.2 — current candidate over main6bcf208

Read the [current gap/evidence matrix](../audit_reconciliation.md) first.
PR19/21/27 are in main; `feat/ux@58227de` adds log-only continuation beyond the
audited merge. Preserve the existing viewer. Review the featured recorder run
`recorded-recovery-001`, exact public rasters, absolute-height camera, source/grid
labels and strict optional-layer binding. Keep the 2 km generated demo separate.
Orbital slope preview creates no observation or map change; do not narrate it
as a sensor. The recorded case is human MOCK stop/replan/return, robots idle,
READY rather than scientific COMPLETE. Next deliverable: production-viewer
backend-off seek/IDs/resources/camera check and video of that exact run, with
source/hash references. Historical absent-raster/isolation statements below do
not describe the already integrated strict loader. Three-role acceptance remains
open with Jesus/David; do not fill it with scripted completion events.

## Current continuation — 14 November 2026, main 5ab1387

The owner assumes Fajardo's latest publication is usable; its verification is
handled in Conciliación. Follow [CONT-JOR-01..04](../team_continuation_plan.md#jorge-fajardo--science-patch-dossier-and-shared-site-access):
research primary NASA criteria for scientific POIs/patch selection with David
and Daniel; deliver shared reproducible site deployment with Jesús; then replay
and film the future integrated run on the accepted viewer. Do not redo the
published loader/demo as a new assignment. Preserve organizer reminders and
source labels. The inventories below are historical, not the current task list.

Latest verified implementation: **`feat/ux`**, head
`d649e2e5632dddcf242f403abe0013be29d2f907`, with existing viewer plus gateway
replay adapter (`89216fc`), pose/camera updates and main merge (`1e37fd3`).
Branch documentation identifies PR #5. The objective requested PR source
`feature/web-replay-viewer`; that branch remains at
`73f22dba432ed69c351699c1d712f5d515df4c78` and is a verified ancestor of current
`feat/ux`. Preserve both. Jorge/Jesus must confirm source alignment; do not force
branch changes, discard latest work, or replace it with the former scaffold.
PR #5 was verified OPEN against main `004b3b2`, with head `d649e2e`.
Its body reports 58 web tests; newer branch documentation reports 64. Keep
both as contributor reports at their cited revisions, not freshly rerun results.
The PR body also identifies an optional AI coauthor trailer in historical
commit `73f22db`. Flag it for the owner's policy/history decision; add no such
trailers and never rewrite history without explicit authorization.

Current handoff: `web/README.md`, AI declarations and third-party notices on
`feat/ux`. The initial no-advance UX observation has been superseded.

Read [AGENTS.md](../../AGENTS.md), [ICD](../ICD.md), [contract baseline](../CONTRACT_BASELINE.md) and [integration matrix](../INTEGRATION_MATRIX.md) before editing. Canonical ROS fields/types live in `src/mge_interfaces/msg` and `srv`; preserve them and adapt representations explicitly.

## Owned implementation and contracts

Preserve `web/src/components/`, existing scene/assets, astronaut, agents, terrain layers, route overlay, event inspector, timeline and visual experience. Own `web/src/data/replayAdapter.ts`, existing `web/src/data/gatewayReplay.ts`, `web/src/types/`, display helpers/tests, `web/public/replay/`, asset notices and web data extraction scripts.

Preserve the existing canonical package adapter/run selector added in `89216fc`;
reconcile it with the baseline validator rather than creating another viewer
conversion. Consume canonical gateway/replay JSON `schema_version: 1.0.0` through the [deterministic replay adapter](../REPLAY_CONTRACT.md). Keep the existing `mge-web-0.1-draft` fixture format as an illustrative source until conversion is tested. Preserve ROS wire field names, route statuses/reasons and IDs. Convert ENU `(x,y,z)` to Three `(x,z,-y)` only at display. Display replay as REPLAY and retain MOCK source provenance; show NOT_READY/ERROR and never infer LIVE from a running gateway. No command is accepted from offline replay.

Only MissionManager authorizes the route. Do not calculate a replacement route, infer a task completion from animation, or turn UNKNOWN into a feasible state. The fixture generator's route search remains illustrative, outside operational mission/planner authority; label and preserve it accordingly.

## Dependencies, mocks and immediate blocker

Jesus supplies recorded canonical state/events and the adapter; Daniel supplies public prior/belief/sigma/observed layers and three georeferenced control points.

The current gateway sample has no rasters. The new viewer adapter reconstructs a zero flat grid by dataset/source-text matching, with null sigma/reference; that is illustrative MOCK display, not recorded terrain evidence. Retain this work while tightening schema/run/version validation and explicit synthetic-source checks. Operational terrain requires matching public layer files; never borrow rasters from another dataset/run/map.

The current web terrain (~2 km / 20 m) differs from the planner provisional crop (~128 m / 4 m).

**Do not publish the current evaluator fixture.** `RasterSet.reference` and the bundled `rasters.json.reference` are downloadable, and `?evaluator=1` exposes them. A default-hidden layer is not isolation. Preserve the authored fixture in the work branch, quarantine it from public exports, change the public loader/type to accept no reference, and verify that neither reference values nor a separate reference file exists in the public build. Evaluator tooling stays isolated. Keep public assets/provenance and existing third-party licenses intact.

## Synchronize without losing existing work

After saving/reviewing local edits, confirm the PR-source choice with Jorge/Jesus, then use the existing worktree for
the verified latest branch (shown below). Do not move another active worktree:

```sh
git status --short
git fetch origin --prune
git switch feat/ux
git pull --ff-only origin feat/ux
git log -1 --format=fuller origin/main
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- web docs/AI_DISCLOSURE.md THIRD_PARTY_NOTICES.md
git merge origin/main
```

If the branch is not local, use `git switch --track -c feat/ux origin/feat/ux` instead of switch/pull. Do not switch it if another worktree already has it checked out. Merge main only while on your owned branch. Stop to reconcile any shared-contract conflict with Jesus and the producer/consumer owners; preserve both implementations and never force-push. This reconciliation becomes the main contract only after its PR is merged. Before that, review it as a proposal and do not claim it is published in main.

## Tests and consumer evidence

First run from `web`: `npm ci` then `npm test`. Keep `coords.test.ts`, `replay.test.ts`, `management.test.ts`, `terrainSmooth.test.ts` `gatewayReplay.test.ts`, `smoothing.test.ts` and `astronaut.test.ts`; they preserve the current implementation. Run root `python -m pytest tests/contract/test_replay_conversion.py` after the baseline lands, followed by `npm run build`. Keep the existing actual gateway-sample consumer test; add a strict canonical
package test with Daniel's matching public raster sidecar; missing layers, stale versions and non-feasible states must fail/display clearly.

Serve the production build with backend stopped. Record the tested URL, run/dataset/map IDs, source MOCK/REPLAY labels, three control-point matches, timeline seek/event ordering, reasons, all invalid statuses and reference-free network/build asset inspection. Test a private browser and retain screenshots with required generated-asset watermarks. The new MOCK gateway replay checks establish a limited canonical consumer; they do not prove arbitrary package/schema validation or scientific raster compatibility.

## Acceptance and next delivery

Confirm whether the existing feat/ux PR #5 remains the review source or Jorge
aligns the preserved historical branch as requested; publish an incremental PR
without rewriting history, preserving the scene and all existing tests. Acceptance requires canonical conversion consumed by the existing viewer, explicit unavailable/error/source modes, no local planner, reference-free public output and three Daniel control points. First deliver the public raster type/loader correction and canonical fixture consumer; then record backend-off replay evidence. LIVE controls stay unavailable until Jesus supplies a reviewed real connection and MissionManager authorization flow.

## PR and handoff evidence

Include the tested source SHA, baseline/schema versions, dataset/run/map IDs, model/configuration hashes where relevant, exact commands/outcomes and links to immutable evidence. Name any MOCK provider and all skipped checks, with reasons. Run `python -m pytest`, `python scripts/check_repository.py`, and the frontend `npm ci`, `npm test`, `npm run build` where available, using `web/.nvmrc`. On Ubuntu 24.04/Jazzy, build with `colcon build --symlink-install`, source `install/setup.bash`, inspect the six messages/two services and run the ROS contract/integration tests. A Windows skip is not a passing ROS test.

Review `git status`, `git diff` and `git diff --check`. Keep commits atomic and English Conventional Commits; preserve Git identity, third-party rights and mandatory AI usage text/metadata/watermarks. Update `docs/AI_USAGE.md`, `docs/ai_usage.json` and your handoff. Do not upload secrets or evaluator data.
Jesus reviews integration; David approves scientific assumptions/success.
Software tests, replay and synthetic fixtures do not establish a validated
LIVE mission. No push, merge or release is implied by this handoff alone.

## Status update from feat/ux (14 November 2026)

- Evaluator reference isolated (`908edae`): `RasterSet.reference` is optional, the public
  `rasters.json` has none, the generator writes it to the Git-ignored
  `data/reference/<run_id>/`, and only the dev server's evaluator view loads it. A
  production build contains no reference values or file
  (`web/tests/referenceIsolation.test.ts`, plus a `dist/` scan). The values remain in
  earlier Git history of `rasters.json`; removing them needs an owner decision on
  rewriting history.
- Demo terrain draped with the real CTX orthomosaic from Mars Trek (`f80b020`, same
  `soc_008` production as the DTM); provenance in `THIRD_PARTY_NOTICES.md`.
- Astronaut posture, pause pose, marker masts and camera easing fixed; 71 Vitest tests and
  `npm run build` pass on Windows. `python -m pytest` and ROS checks were not run here.
- Still open from this handoff: strict canonical package validation with Daniel's raster
  sidecar, `displayState` labels in the status block, three control points, and
  backend-off evidence.
