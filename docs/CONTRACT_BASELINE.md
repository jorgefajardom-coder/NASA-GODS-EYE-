# Contract reconciliation baseline 1.0.0-rc.2

Status: **published in main through PR28; not frozen, no release or scientific
approval**. Reviewed source `7f0ebaaefa90b7ae48505f8e06d22f2660e5d491` was
merged as `9198b3d8b3257dfd452d240ee9708cb038c3bb42`. The original audit input
`6bcf208868e37b7e15e9189fac11de96e7414eff` and source-lock remote inventory
remain historical snapshots. The published F/E software and runtime-v1 evidence
do not replace cross-owner semantic/parameter review or full mission acceptance.
See [current closure and PDF disposition](delivery_closure_plan.md).

This prerelease identifies the reconciliation record. ROS package/message/service
versions and gateway/replay JSON `1.0.0` remain unchanged. The
[machine-readable source lock](contract_baseline.json) records fresh audited remote
refs and exact six-message/two-service hashes. Its `historical_baselines` retains
the complete original rc.1 audit object; historical branch/status claims there
are snapshots of that audit, not the present publication state.

## Authority and compatibility

| Contract | Current version/source | Scope and owner gate |
|---|---|---|
| ROS fields/types/constants | ICD-ROS2-V1; mge_interfaces package 1.0.0 | Jesus; unchanged canonical `.msg`/`.srv` files |
| Gateway/replay | 1.0.0 | Jesus; manifest/timeline/snapshot plus optional public raster attachment |
| Public rasters | mge-public-rasters-1.0.0 | Prior and exact recorded-version belief/sigma/observed layers; no evaluator data |
| Viewer target | mge-web-0.1-draft | Jorge; strict canonical-package conversion is implemented on main |
| Dataset delivery | dataset.schema.json 1.0.0 contract; public jezero_mvp loader | Daniel; delivered public data/provenance remain distinct from profile/scientific approval |
| Exploration policy | mge-exploration-policy-1.0.0, illustrative candidate | Fresh F/E consumer proved in runtime-v1; owner semantic/parameter review remains pending |
| Science costs | proposed mge-science-1.0.0 | David/Diego/Jesus; incompatible search projection remains blocked |
| Launch approval receipt | legacy baseline_version 1.0.0-rc.1 | Existing profile-launch receipt parser is unchanged; rc.2 is not an approval receipt |
| Platform | Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic; web/.nvmrc | Software validation and physical/Gazebo mission acceptance are separate |

ROS remains the field/type authority. Preserve map ENU SI coordinates, southwest
origin, rows north, columns east, `row*cols+col` and Three.js `(east, up, -north)`.
Canonical route statuses are unchanged. Typed nonhuman O2/NoData/unavailable
non-FEASIBLE NaNs become JSON null; arbitrary NaN and all infinities are rejected.

## Published behavior and candidate changes

1. **Published owner implementations.** Main contains real data/mapping, planner,
   mission authority, gateway/recorder and the web consumer. Their production
   availability does not approve model agreement or execution evidence. Keep
   services exclusive and preserve the existing owner histories.
2. **Published recorded terrain and replay.** The recorder writes
   `public_rasters.json`; the web loader reads it and the closing snapshot,
   validates identities/counts/routes/versions/history and renders recorded
   Jezero terrain. PR19/PR21 supersede the old claims that only flat packages
   can open. Missing attachments remain unavailable. A flat synthetic fallback
   remains explicitly illustrative. See [replay](REPLAY_CONTRACT.md).
3. **Published continuous recovery.** Ground starts are continuous only with
   explicit opt-in. Validated connectors preserve actual XYZ, swept geometry,
   directed limits and costs; goals/return targets stay centred. Kinematic MOCK
   recovery waits for fresh stationary stop feedback and plans from actual
   remaining allocations with unchanged reserves. This has a narrower recorded
   recovery scope, documented in [the recovery handoff](mission_replay_recovery.md).
4. **Published F: causal observations.** A new observation must use the current
   base map and a timestamp no earlier than the last accepted observation
   globally. Already-applied IDs remain no-ops. Wrong run/frame/stamp, stale/future
   base, old clock or invalid footprint is rejected atomically. Missing or
   UNKNOWN obstacle evidence cannot clear a confirmed obstacle; explicit current,
   nonolder FREE evidence may supersede it. Reobserve delayed footprints rather
   than relabel old data. See [ICD observation rules](ICD.md).
5. **Published experimental E / D-EST-01.** Legacy startup remains `observed_only` when no
   exploration policy file is selected. Explicit
   `config/exploration_policy.illustrative.json` selects `estimated_or_observed`
   under schema `mge-exploration-policy-1.0.0`; per-kind illustrative max sigma is
   3 m. Finite valid estimates can become candidate-admissible without being
   observed. NoData, confirmed obstacles and independent planner profile limits
   remain enforced. Policy identity/hash travel in TerrainMeta.sources. A planner
   profile capped at 1 m sigma may still reject the unchanged 2.5 m prior.
6. **Exact recorded replay entry.** The published cut highlights
   `recorded-recovery-001`, preserving the underlying recorder run identity and
   package bytes. The scripted demo remains a separately labelled illustrative
   example. Final browser/bundle/record checks belong to runtime-v1 evidence;
   they do not establish scientific COMPLETE or three-role execution.
7. **Cost and execution gates.** Same-route/schedule agreement, typed context,
   service progress, role execution and opportunistic evidence remain open.
   [The cost/execution proposal](audit_cost_execution_gaps.md) records the required
   producer/consumer changes. The new exact-main seven-case cost comparison still
   has six disagreements and authorization BLOCKED. Do not enable flags to hide it.
8. **Evaluator isolation.** Reference arrays were removed from the public replay
   distribution on main. Keep evaluator-only material outside planner/runtime/
   public assets, with final-build/network checks at every export. Earlier rc.1
   findings about public reference values are historical and remain in Git history.

## Verification ledger

The [fresh runtime-v1 record](../evidence/audit-reconciliation-20261115/runtime-v1/README.md)
records exact F/E source/package hashes, Jazzy consumer results and ordinary
Chrome replay. The table distinguishes software evidence from remaining owner,
scientific and delivery acceptance; it does not freeze the contract.

| # | Obligation | Existing or candidate checks | Remaining acceptance |
|---|---|---|---|
| 1 | Six messages/two services compile | Runtime-v1 Jazzy build and all eight interface inspections passed | Future interface changes must rebuild/reinspect and preserve legacy compatibility |
| 2 | Types/constants/exclusive providers | tests/contract/test_configuration.py; test_mission_launch.py | Review semantic additions without changing numeric wire codes |
| 3 | Frames and cell order | test_baseline_guards.py; tests/contract/test_dataset.py; web coordinate tests | Same-run controls and final viewer geometry |
| 4 | Typed JSON/null conversion | test_generated_conversion.py; test_baseline_guards.py; gateway tests | Retain invalid-message rejection in real consumers |
| 5 | Current map/request/pose | mission-service, planner-concurrency and recovery tests | Candidate map/progress/context races |
| 6 | Idempotency and causality | tests/mapping/test_observation_causality.py; tests/contract/test_mapping_observation_adapter.py | Actual observation-to-planner consumer, atomic rejection |
| 7 | Map/raster association | tests/unit/test_public_rasters.py; integration terrain/replay tests | Candidate policy provenance and complete recorded versions |
| 8 | Costs/return/reserves | planning tests; scientific vectors and fresh conformance report | Numeric agreement and complete per-agent interval ledger |
| 9 | Invalidate/stop/replan/resume | tests/contract/test_mock_recovery.py; tests/integration/test_vertical_execution.py | Scientific manager/three-role and physical acceptance |
| 10 | Offline same-run replay | tests/contract/test_replay_conversion.py; web gateway integrity tests | Browser evidence for exact highlighted recorder package |
| 11 | Provider replacement | tests/integration/test_vertical_mission.py and terrain/planner verticals | Approved mission models, task/progress bindings and roles |
| 12 | Reference isolation | dataset/contract tests; web reference isolation test; final dist/network audit | Final exported candidate package audit |

Unprefixed Python test names in the table live under `tests/contract`.
The E candidate additionally needs `tests/mapping/test_estimated_planner.py` and
`tests/integration/test_estimated_exploration.py`: initial estimated route,
contradiction, stop/replan from actual pose, all alternatives blocked, NoData,
independent sigma limits and preserved return/reserves. These cases use explicitly
SIMULATED inputs and retain all scientific authorization gates.

## Review and integration order

Jesus reviews ROS/topic semantics, observation atomicity, policy provenance,
clock/provider exclusivity, execution feedback and exact recorder closure.
Daniel reviews public estimated/observed/NoData and obstacle rules. Diego reviews
search, limits/connectors and policy/profile interaction. David reviews
illustrative thresholds, costs, work/traversal evidence and scientific approvals.
Jorge reviews strict replay identity, geometry, labels and backend-off behavior.
All owners confirm the cross-module meaning before any semantic freeze.

Validate candidate F/E producers with the actual planner/recorder; verify exact
recorded-package web consumption; publish source/config hashes and outcomes;
then request review through the PR path. Cost-context and complete mission work
continue on the existing owner modules with explicit pending gates. Main must
be fetched and rechecked before publication. This record authorizes no automatic
owner-PR merges, package release or scientific flag change.

## Historical rc.1 context

The rc.1 source audit began at `f75c54e` and refreshed at `004b3b2` while the
planner PR2 landed. Its then-open owner branches, missing rasters, public
reference finding and unimplemented provider claims describe that older cut.
Subsequent published integrations supersede those implementation-status claims.
The complete original source-lock object is retained under rc.1 in
`contract_baseline.json`; source history preserves the earlier prose. The shared
semantics and models were never frozen or scientifically approved by that audit.
