# Audit reconciliation — contract candidate 1.0.0-rc.2

Reference: published main `6bcf208868e37b7e15e9189fac11de96e7414eff`, fetched
14 November 2026. Working branch: `codex/audit-contract-reconciliation`.
This is a review candidate, not a frozen contract or a release. The audit's
scientific-purpose priority 1 / objection A is excluded: the owner is handling
target selection in another chat. Existing A/B coordinates, approved scenario
values, durations and science approvals are preserved.

## Scope and evidence matrix

| Audit item | Actual boundary / gap | Reconciliation and evidence | Remaining acceptance |
|---|---|---|---|
| B: one execution | Web demo script is illustrative; it cannot prove mission decisions. | Intact recorder package from real data/mapping/planner plus MOCK mission/kinematic human execution, with file hashes/source lock and [completed Chrome QA](../evidence/audit-reconciliation-20261115/runtime-v1/browser.json). | Proven narrower human recovery; private-browser/public-deployment acceptance and three-role scientific execution remain separate. |
| C: scan | The display reads orbital slope, creates no TerrainObservation and changes no map/version. | Rename controls to orbital slope preview and explain display-only behavior before activation. Labels derive native/grid spacing from the loaded scenario. | No sensor or task-execution claim; a future sensor needs a traced observation producer. |
| D: resources | Legacy PlanRoute loses activity identity; scientific and search equations disagree. | [Fresh exact-source comparison and context proposal](audit_cost_execution_gaps.md): one agreement, six disagreements; authorization BLOCKED. Preserve the published cost packet and existing audit API. | David/Diego/Jesus select shared kernel or proven conservative bound, bind request context and execute full itinerary/interval checks. |
| E: estimated prior | Default mapping requires local coverage; default 1 m threshold also excludes the 2.5 m prior. | Explicit illustrative exploration policy permits candidate search over valid estimates under declared sigma/slope bounds. Coverage and sigma remain unchanged; policy ID/hash travels with map metadata. Independent planner profiles still apply. | Review candidate semantics/limits and actual hold/inspection policy; no blanket FREE or scientific approval. |
| F: delayed observation | Reproduced recent obstacle followed by older FREE observation erasing danger. | Current-base and global nonolder observation clock, atomic rejection, duplicate-ID no-op, strict frame/clock adapter, missing/UNKNOWN obstacle evidence preserves danger. | Delayed disjoint footprints are conservatively rejected too; concurrent/per-cell fusion is future work. |
| §5: scenario identity | 128 m scientific crop and 2 km illustrative scene differ in origin, grid and datum. | Recorded raster geometry/IDs are preserved. Camera frames actual absolute heights; optional overlays require scenario compatibility. Native 20 m is distinct from 4 m computation. | No precise geologic contact attribution at 128 m scale from unregistered SIM3464; contextual atmosphere is not telemetry. |
| §6: stale documentation | Data/mapping READMEs still described working modules as empty; MOLA register said pending. | Update status from current loader, manifests, off-diagonal controls and separate MGS product; distinguish current evidence from historical inventories. | Import is not scientific mission acceptance; source roles/limits remain visible. |
| Priority 5: opportunistic science | Mission core supports task policy, but node/executor lack public discovery/work/progress bindings. | Preserve authority and existing EvidenceRecorder; specify one immutable planning/execution context and journal linkage, without inventing fixture task success. | Actual accepted and rejected optional work through real MissionNode, interval costs and capability/precedence/return tests. |
| Priority 6: judge entry | Broad viewer features can hide the evidenced decision change. | Featured recorded recovery, separate illustrative demo, direct entry and honest READY/MOCK labels. | Official submission page, 30 s/seven-slide artifact and organizer endorsement are delivery work, not closed by this engineering PR. |

## Compatibility and authority

ROS `.msg`/`.srv` remain ICD-ROS2-V1/package 1.0.0; gateway/replay remain 1.0.0;
public rasters remain `mge-public-rasters-1.0.0`. The reconciliation record is
rc.2. The additive configuration schema is `mge-exploration-policy-1.0.0`;
no field, enum, unit, frame, grid order or optional-oxygen convention is changed.
Planner candidates do not authorize motion; MissionManager owns that decision.
The stricter freshness policy intentionally rejects previously accepted stale
observations and is recorded as a behavior change for producer review.

`exploration_policy_file` is an explicit launch/mapping input. Empty retains the
legacy observed-only behavior for existing callers. The illustrative example
uses sigma ≤3 m without reducing the source 2.5 m uncertainty. The planner's
1 m scientific-profile limit still rejects it. Policy identity is stored in
TerrainMeta.sources and therefore in every recorded metadata cut; one policy
is immutable for the run. A new policy requires a new run/configuration.
Observation freshness retains exact ROS integer nanoseconds, including at large
wall-clock epochs; descriptive float seconds never decide ordering. Seconds-only
legacy Python calls quantize to nearest nanosecond with checked consistency.
Zero occupancy under that policy means admissible for a hypothetical proposal;
observed coverage, NoData and confirmed obstacle evidence remain distinct.

No model/profile/science approval Boolean is enabled by this reconciliation.
Scientific profiles, cost agreement, execution evidence and success criteria
remain separate gates. The current MOCK recovery ends READY; it does not
establish COMPLETE, three-role execution, Gazebo physics or validated LIVE.

## Integration order and individual cuts

| Owner / active front | Next concrete deliverable | Dependency and closure test |
|---|---|---|
| Daniel — feat/data | Review fresh observation rejection and estimated-map policy; retain public prior/sigma/coverage and exact controls. | Mapping and actual PlanRoute consumer: prior-only proposal, contradiction, no alternative, NoData, stale/duplicate and stricter-profile rejection. |
| Diego — feat/planner | Resolve the actual scientific backend and explicit service/wait/model context with David; retain search/connector implementation. | Revalidate heuristic/dominance and all cost vectors, current-pose/remaining resources/return, insufficient budgets and model mismatch. |
| David — feat/mission | Review cost/context/interval contract and derive completion from evidence; coordinate purpose work separately. | Do not alter scenario approvals to unblock tests; verify work at 0/119/120 s, interruptions, task precedence, optional acceptance/rejection and return closure. |
| Jesus — feat/integration | Review map semantics, stop acknowledgement and recorder cut; bind context, public discovery/progress and existing scientific journal. | Real MissionNode + planner + role executor after model/context agreement; source/config hashes, exact package, stale response refusal and no provider collision. |
| Jorge — feat/ux | Review same-run camera/layers/labels and the featured recorder package; keep demo separate. | Production build served statically with ROS/gateway off; seek before/after contradiction, preserve IDs/resources, no evaluator asset or borrowed overlay. |

Mapping freshness and display corrections can be reviewed in parallel. Land the
candidate policy only after producer/consumer semantic review. Model kernel and
request context precede service/progress accounting and optional robot execution;
then record one actual three-role run and replay/video that same run. Existing
step 4 and step 5 remain open. Larger maps, extra scenes and policy comparisons
are secondary; no comparison claim is made without identical initial conditions.

## Reproduction and validation

Validation records are in `evidence/audit-reconciliation-20261115/`.
`cost/` is the newly executed comparison against exact main6bcf208, separate
from the reconciliation source. [Runtime-v1](../evidence/audit-reconciliation-20261115/runtime-v1/README.md)
records 1054 Windows passes, 1086 Jazzy module passes, 48 integration passes,
one fresh recording and 202 web passes/build, with source/package hashes and
completed ordinary-Chrome backend-off QA. Omissions and narrower MOCK scope
are explicit. D-COST-02's new backend/context is the subsequent implementation
cut, not claimed by those legacy-cost runtime results.
Required checks: `python -m pytest`, `python scripts/check_repository.py`,
`npm test`, `npm run build`, Jazzy build/interface inspection and actual ROS
consumer. A green unit test is not a replacement for the same-run browser check.

Owner review: Jesus integration; Daniel mapping/data; Diego planner; Jorge
viewer; David scientific assumptions and success. Publish through a reviewed
PR to main, rechecking main before push. Do not merge an owner's PR as part of
this cut, send team messages or publish a submission without authorization.
