# Contract baseline 1.0.0-rc.1

Status: **review candidate on `codex/contract-reconciliation`; not published in
main, not frozen, no release**. Main reference at audit:
`004b3b2c59a27794a1e49a61f48d0569bad020b2` (2026-11-14, America/Bogota).
Initial audit main was f75c54e; main advanced concurrently when Jesus merged PR #2.
The exact reconciliation commit is the head of its PR, not the reference-main
SHA. [Machine-readable source lock](contract_baseline.json) records all eight
remote heads and SHA-256 fingerprints of the six messages/two services.
This prerelease identifier versions a new reconciliation record; it does not
bump existing package, ROS, gateway or viewer releases.

GitHub reported main unprotected and no rulesets at audit. Concurrent owner
branches, unresolved science and review gates justify a PR instead of direct
main updates. A merged PR is needed before describing this as the baseline in
main. PR #2 was merged externally into main; this branch incorporates that main
without merging PR #3/#4/#5 or any other owner branch. Main must be
fetched/rechecked immediately before publication; see the integration log.

## Authority and versions

| Contract | Version/source | Owner and compatibility |
| --- | --- | --- |
| ROS wire | ICD-ROS2-V1, mge_interfaces package 1.0.0; unchanged .msg/.srv | Jesus; producers and consumers retain main fields/types/constants |
| JSON/replay | 1.0.0; manifest.json/timeline.jsonl/snapshot.json | Jesus; canonical recorder/bridge on latest audited integration branch |
| Viewer adapter target | mge-web-0.1-draft; four legacy JSON objects | Jorge; actual TS gateway consumer on advanced feat/ux retained; strict conformance pending |
| Public dataset delivery | dataset.schema.json 1.0.0, new candidate | Daniel; legacy provenance template retained, no approved dataset yet |
| Science costs | proposed mge-science-1.0.0 | David; search projection pending_model_agreement |
| Planner search | FAST/SAFE MotionProfile implementation now in main | Diego; EFFICIENT unsupported; not science-equivalent |
| Platform | Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic; Node web/.nvmrc | Jesus platform, Jorge browser; Gazebo execution pending |

ROS is the sole field/type authority. JSON is an adapter representation; no ROS
schema_version field is invented. ENU map uses SI, southwest grid origin, rows
north, columns east, index row*cols+col. Three.js is (east, up, -north).
Canonical statuses remain FEASIBLE/UNKNOWN/NO_PATH/INSUFFICIENT_BUDGET/STALE_MAP/ERROR.
Identifiers bind run/request/event/observation/route and map version. Nonhuman
oxygen ROS NaN explicitly becomes JSON null. TerrainMeta NoData NaN separately
becomes null by message context; typed non-FEASIBLE RouteDecision unavailable NaNs become null; arbitrary
non-finite values and all infinities are rejected.

## Reconciled decisions and dependencies

1. Preserve owner modules. Incorporate the externally updated main planner
   unchanged; do not import replacement modules or merge unreviewed owner PRs.
2. Use gateway replay 1.0.0. The strict offline oracle/export adapter preserves source
   stamps, relative replay offsets, IDs, ENU geometry and costs. Existing recorder
   lacks rasters, so strict playback remains NOT_READY. Jorge now has a TS
   gateway consumer; harden it rather than replacing it. Its flat reconstruction
   is an explicit illustrative MOCK fallback, never recorded terrain.
3. Keep the planner/web crops distinct. Daniel must deliver one public dataset
   with masks/uncertainty/kind traversability, provenance/hashes and three controls.
4. Keep science audit and search models separately identified. Scientific
   operational feasibility is blocked until independent numerical itinerary
   agreement is approved. A parameter projection does not resolve the equations.
5. Reject continuous non-cell-centre positions explicitly. A future connector
   needs swept-geometry checks and accounted resources; none is silently added.
6. MissionManager alone authorizes the route and tasks, reserves return, discards
   stale candidates and signals stop/replan on map change. Executor stop feedback
   and real current-pose integration remain pending.
7. Separate MOCK/integration/simulation/live provider profiles. Live is unavailable.
   A contract double has deterministic inputs/outputs and no scientific claims.
8. Remove evaluator truth from planner/public packages. Jorge's audited public
   fixture currently violates this; preserving branch work does not approve its
   publication. All-null legacy padding carries no evaluator values.

Detailed ownership/requirements/functions and actual branch evidence are in
[INTEGRATION_MATRIX.md](INTEGRATION_MATRIX.md). The [ICD](ICD.md) defines semantics;
[replay](REPLAY_CONTRACT.md), [datasets](DATASET_CONTRACT.md),
[guard limits](CONTRACT_GUARDS.md) and [launch](LAUNCH_PROFILES.md) specify adapters.
The VDI/VDE 2206 R-F-L-P allocation is a traceability method here, not a claim
of standards certification: requirements map to functions, logical modules and
software/platform allocations; verification checks implementation contracts,
while David's system/science acceptance validates intended mission outcomes.

## Twelve verification obligations

| # | Obligation | Executable evidence in this cut | Real acceptance still pending |
| --- | --- | --- | --- |
| 1 | ROS message/service compilation | scripts/validate_contract_baseline.sh, tests/contract/test_interfaces.py | Combined real producer build after owner PR integration |
| 2 | Constants/types/enums | test_interfaces.py, test_baseline_guards.py, test_configuration.py | Every future producer/consumer maintains exact types |
| 3 | Coordinates/cell order | test_baseline_guards.py; web frames/provenance tests | Daniel's three independent geographic control residuals |
| 4 | ROS -> JSON NaN/null | test_generated_conversion.py and test_baseline_guards.py | PR #3 serializer adopts equivalent strict cases |
| 5 | Stale map | test_baseline_guards.py and test_replay_conversion.py | Real MissionManager/planner concurrent response case |
| 6 | Duplicates/idempotency | test_baseline_guards.py; replay duplicate rejection | Integrated service cache side effects/restarts |
| 7 | Raster/map identity | test_dataset.py, test_baseline_guards.py, test_replay_conversion.py | Real atomic DDS producer and recorder raster capture |
| 8 | Return/reserves/infeasibility | test_baseline_guards.py | Full independent science audit and real route/reserve run |
| 9 | Invalidation/logical stop | test_baseline_guards.py | Mission ROS empty Path plus executor acknowledgement |
| 10 | Offline record/replay | test_replay_conversion.py, immutable source fixture | Jorge browser consumption with public same-grid rasters |
| 11 | Replace MOCK producer | tests/integration/test_provider_substitution.py | Real planner seam now runs in baseline; real MissionManager/provider replacement remains pending |
| 12 | Evaluator isolation | test_dataset.py, test_baseline_guards.py, test_replay_conversion.py | Audit final web build/filesystem mounts, fix branch public reference |

All file names in the table without a prefix are under tests/contract. Tests
of doubles and guard helpers exercise the contract; they do not certify that
unmerged real components use those helpers. All R01-R18 mission acceptances
remain pending or blocked. Exact fresh results, source hashes and unavailable
checks are recorded in [verification](verification.md) and the integration log.

## Owner gates and next integration cut

Jesus reviews interfaces, adapters, QoS/clock/provider exclusivity and wiring.
David approves scientific coefficients, oxygen convention, success/return criteria
and model error bounds with Diego. Daniel approves data/provenance/control points;
Jorge confirms actual viewer conversion/labels. Event/reason vocabulary and
snapshot producer agreement still require recorded team confirmation before freeze.

Recommended order: review/merge this contract PR; reconcile #3 gateway against
it and preserve the already merged #2 planner; integrate mission only after numerical
model audit; deliver Daniel's coherent provisional public dataset; harden Jorge's existing
feat/ux gateway adapter and remove public evaluator arrays; then run one real map ->
planner -> MissionManager -> gateway -> replay consumer cut. Reconcile #4 docs
in a small reviewed change, not an automatic bulk merge. This order describes
dependencies; it authorizes no automatic merges.

Handoffs: [Jorge](handoffs/jorge.md), [Jesus](handoffs/jesus.md),
[Diego](handoffs/diego.md), [Daniel](handoffs/daniel.md), [David](handoffs/david.md).
Each begins by fetching and merging reviewed origin/main on the owner's own
branch, with a clean tree; never overwrite concurrent work or force-push.

## Final refreshed branch state

The original feature/web-replay-viewer head73f22db is an ancestor of the actual
advanced continuation feat/ux at d649e2e (PR #5). It is no longer the old scaffold.
Record both histories and have Jorge align the PR source without discarding
that continuation; this task changes neither owner branch. Integration45a4590
already offers planner:=real with a MOCK mission/terrain and coherent batches.
Their performance/search-limit findings and still-public evaluator fixture are
listed in the updated matrix. No R01-R18 acceptance is inferred from those advances.
