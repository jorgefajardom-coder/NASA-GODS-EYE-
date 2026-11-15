# Daniel - deliver the canonical public dataset and coherent belief

Future guide: [science extension tree](../science_extension_tree.md). Daniel
leads A1 context, B1/H-DAN-01 seeded worlds and F1 sensor hypotheses once their
gates are accepted and scope is reopened. The delivery freeze remains active.
New unlisted ideas may be assessed in an isolated local branch for discussion
on 15-Nov-2026 (Bogota), without extension publication/integration or lost delivery work.

## Delivery priority after PR28 — owner-confirmed 14 November 2026

Follow [PDF tasks DA-1..4](../delivery_closure_plan.md) and
[D-DEL-03](../decisions/2026-11-14-delivery-freeze.md). Pause larger-map/scene
and H-DAN-01 work until after submission; preserve completed studies. Current
work is existing-crop coverage/ENU checks, source-traced rover-image curation
where supportable, and the final NASA contribution table. MOLA ingestion and
F/E protection are already published; do not redo them as missing features.
New science shortlist/maps remain proposals. No recentering or A/B change
without explicit owner decision and validation. Remind the organizer gate.

## Audit reconciliation rc.2 — current candidate over main6bcf208

Read the [current gap/evidence matrix](../audit_reconciliation.md) before the
historical inventories below. `feat/data@6cb1290` is already in main: data
loading, observation fusion, public batches and MGS/MOLA ingestion are implemented.
Review current-base/nonolder observation rejection and preservation of obstacle
evidence. Review the explicit estimated-prior policy jointly with Diego/Jesus;
coverage and sigma must not be fabricated to obtain a path. Next deliverable:
producer acceptance of the policy ID/hash, immutable batch semantics and the
prior-only → one-cell contradiction → actual consumer case. Scientific limits
still need David. Retain 128 m controls; larger-map work remains optional.

The older scaffold/absent-ingestion statements below describe their dated cut,
not current main. Sync your owned branch with reviewed main, preserving local
work; this candidate becomes main only after its PR review/merge.

## Current continuation — 14 November 2026, main 5ab1387

Follow [CONT-DAN-01..04](../team_continuation_plan.md#daniel--public-terrain-observations-and-larger-map-feasibility):
continue the larger-map import/analysis study already underway; reconcile
D-EST-01 and executed observation footprints with Diego/Jesús; validate current
baseline controls now and the new patch's controls after David/Fajardo's selection.
H-DAN-01 remains optional and seed-traced. Preserve the 128 m control and
organizer gate. Historical inventories below are not a fresh dependency audit.

Active branch: **`feat/data`**. Audited head: `f75c54e929576c6780d559c9daa24d06ccf0a0b8`, equal to initial main; there are no data-front commits beyond it. It is now
behind refreshed main `004b3b2`, which includes the planner. No new Daniel
data/fusion delivery was found in the final refresh. Existing handoff material is `docs/data_sources.md`, `config/terrain.yml`, `src/mge_data/README.md` and `src/mge_mapping/README.md`. Manifest examples and Python input guards are scaffolds; `fuse_observation` is not implemented.

Read [AGENTS.md](../../AGENTS.md), [ICD](../ICD.md), [contract baseline](../CONTRACT_BASELINE.md) and [integration matrix](../INTEGRATION_MATRIX.md) before editing. Canonical ROS fields/types live in `src/mge_interfaces/msg` and `srv`; preserve them and adapt representations explicitly.

## Owned implementation and canonical delivery

Own `src/mge_data/`, `src/mge_mapping/`, `config/terrain.yml`, data manifests, provenance/licenses/hashes, public layers, masks, NoData and three control points. Use the baseline `data/dataset.schema.json` and ICD; do not invent a parallel raster format. Preserve source NASA/USGS provenance and applicable licenses. Deliver one explicit dataset_id/run_id/map_version with Mars CRS, planetary origin/local ENU, southwest grid origin, resolution, rows/cols, vertical datum and any local elevation offset. Supply immutable orbital prior, current estimated elevation/belief, sigma, NoData mask and per-kind traversability (-1 unknown, 0 admissible, 100 forbidden). Invalid/NoData/unknown is never free. Provide hashes of all distributed files, source product/version identifiers, processing parameters and three georeferenced control points with ENU/metres and declared tolerances. A provisional package is labelled provisional. Planner's ~128 m / 4 m near 18.45N,77.45E and web's ~2 km / 20 m near 18.53545N,77.42382E are different products. Select and document the canonical extent/resolution, then arrange both consumers against it; no implicit merge, resample, shift or equivalence claim is permitted.

Publish canonical TerrainMeta/prior, and coherent versioned belief/sigma/ traversability batches: same frame/stamp across a complete run/version batch, unique stamp per run/version, metadata association and repeated complete publishing to survive cross-topic DDS reordering. A changed geometry/layer needs a new version/stamp. Accept only valid current-base TerrainObservation footprints; deduplicate observation_id, increment once, update only footprint, and publish an atomic complete snapshot. Prior is immutable within a run.

The refreshed integration branch already publishes coherent synthetic batches
for the real planner; preserve this MOCK plumbing but deliver the actual public
data publisher in your owned packages. The refreshed `feat/ux` viewer consumes
gateway MOCK-flat replay; its flat reconstruction is not a substitute for your
recorded public rasters or georeferenced controls.

## Evaluator isolation and authorized test doubles

The reference DEM and unrevealed future tasks stay in evaluator-only storage/ processes. Never pass reference to planner, gateway or public replay/web files. Jorge's existing `rasters.json.reference` is downloadable despite its evaluator toggle; coordinate removal from distribution and a reference-free loader. Preserve the authored illustrative fixture in its work area, not public output. Deterministic synthetic public terrain/observations are allowed to test consumer interfaces and must say MOCK/SIMULATED. They are not NASA measurements or a processed scientific data delivery. Jesús supplies launch integration; Diego and Jorge are the required real consumers; David approves uncertainty/scale assumptions. Do not implement another planner, mission authority or viewer.

## Synchronize without losing existing work

After saving/reviewing local edits, use the existing worktree for this branch:

```sh
git status --short
git fetch origin --prune
git switch feat/data
git pull --ff-only origin feat/data
git log -1 --format=fuller origin/main
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- src/mge_data src/mge_mapping config/terrain.yml data docs/data_sources.md
git merge origin/main
```

If the branch is not local, use `git switch --track -c feat/data origin/feat/data` instead of switch/pull. Do not switch it if another worktree already has it checked out. Merge main only while on your owned branch. Stop to reconcile any shared-contract conflict with Jesus and the producer/consumer owners; preserve both implementations and never force-push. This reconciliation becomes the main contract only after its PR is merged. Before that, review it as a proposal and do not claim it is published in main.

## Tests and consumer proof

First run `python -m pytest tests/contracts/test_data_manifest.py tests/mapping/test_observation.py`. After baseline merge run `python -m pytest tests/contract/test_dataset.py tests/contract/test_baseline_guards.py`. Extend real fusion tests for equal array lengths, bounds/NoData, sigma, duplicates/conflicts, stale runs/base versions, single revision per observation, footprint-only changes and rejection atomicity. Test north-up source conversion into row-0-south once, row-major ordering and three georeferenced controls.

Build/source Jazzy and publish a complete repeated batch to Diego's real PlanRoute consumer; deliberately interleave an old sigma/new mask and verify no candidate from mixed layers. Load the same public dataset in Jorge's viewer and verify the three controls and vertical offset. Record exact hashes/IDs and inspect all public outputs to prove reference/future knowledge is absent.

## Acceptance and next delivery

The first deliverable is the actual public dataset package, validated manifest, source/license hashes and three controls; identify remaining provisional data. The second is an atomic belief/sigma/mask publisher and deterministic observation update with one revision per accepted footprint. Acceptance requires both real consumers to agree on dataset/geometry/version, unknown handling, no leaked reference and David's explicit scientific approval. A valid JSON schema alone is not scientific data acceptance.

## PR and handoff evidence

Include the tested source SHA, baseline/schema versions, dataset/run/map IDs, model/configuration hashes where relevant, exact commands/outcomes and links to immutable evidence. Name any MOCK provider and all skipped checks, with reasons. Run `python -m pytest`, `python scripts/check_repository.py`, and the frontend `npm ci`, `npm test`, `npm run build` where available, using `web/.nvmrc`. On Ubuntu 24.04/Jazzy, build with `colcon build --symlink-install`, source `install/setup.bash`, inspect the six messages/two services and run the ROS contract/integration tests. A Windows skip is not a passing ROS test.

Review `git status`, `git diff` and `git diff --check`. Keep commits atomic and English Conventional Commits; preserve Git identity, third-party rights and mandatory AI usage text/metadata/watermarks. Update `docs/AI_USAGE.md`, `docs/ai_usage.json` and your handoff. Do not upload secrets or evaluator data.
Jesus reviews integration; David approves scientific assumptions/success.
Software tests, replay and synthetic fixtures do not establish a validated
LIVE mission. No push, merge or release is implied by this handoff alone.
