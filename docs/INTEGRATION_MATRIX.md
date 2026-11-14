# Integration matrix and acceptance gates

Audit date: 2026-11-14 (America/Bogota). Reference main:
`f75c54e929576c6780d559c9daa24d06ccf0a0b8`.

The new reconciliation is a separate review cut; the [baseline](CONTRACT_BASELINE.md) identifies its publication state. Branch implementations listed here are preserved in their owning branches; this matrix does not claim they have been merged or jointly validated.

`REAL` means an actual software implementation exists at the cited revision, not scientific or operational acceptance. `MOCK` means deterministic stand-in. `PENDIENTE` means no completed producer or acceptance evidence. `BLOQUEADO` means a specific compatibility/approval condition prevents operational integration. Every R01-R18 system acceptance remains pending. Test files establish testable claims; historical reported runs are not fresh results for this reconciliation.

## Observed configuration and available work

| Front / owner | Observed remote revision | Available implementation and handoff | Reconciliation state |
| --- | --- | --- | --- |
| Integration / Jesus | `feat/integration` `d28f3e23f268d50c6c55f2b1f85a1cadbe9281ed` | ROS-backed gateway, store, recorder, MOCK vertical; PR #3 | REAL gateway/recorder, MOCK producers; real provider integration PENDIENTE |
| Planning / Diego | `feat/planner` `34c515b6b86f73336844e8b3614c70b144574ec3` | FAST/SAFE joint outbound/service/return search, ROS server, immutable batches; `docs/planner_handoff.md`; PR #2 | REAL algorithm/service; scientific model agreement BLOQUEADO |
| Mission / David | `feat/mission` `cf292107277e1aaf130d6c0ecd33904a22638f4f` | Mission authority, models, tasks, ROS adapter; `docs/mission_handoff.md` | REAL core/service; execution and scientific approvals BLOQUEADO |
| Viewer / Jorge | `feature/web-replay-viewer` `73f22dba432ed69c351699c1d712f5d515df4c78` | 3D scene, assets, agents, layers, timeline, offline fixture; `web/README.md` | REAL viewer, illustrative replay; public export BLOQUEADO by bundled evaluator reference |
| Data / Daniel | `feat/data` `f75c54e929576c6780d559c9daa24d06ccf0a0b8` | No commits beyond main; manifest and mapping scaffolds | Canonical data/fusion publisher PENDIENTE |
| Former UX | `feat/ux` `f75c54e929576c6780d559c9daa24d06ccf0a0b8` | No commits beyond main | Superseded as active work front by actual web branch; preserved |
| Transversal plan | `codex/docs-probable-mission-plan` `03d94c7c75eb453b63defaae75d7b52858b0c326` | Checklist, NASA traceability, source notes; PR #4 | REAL documentation proposal; no module implementation |

PRs [#2](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/pull/2), [#3](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/pull/3) and [#4](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/pull/4) were OPEN, not merged at audit. `dev/jesus` was removed remotely; its integration work is retained by `feat/integration`. Do not recreate it as the active front.

## R-F-L-P allocation and contracts

P denotes package/deployment, rather than a claim that the physical hardware or Gazebo vehicle has been verified. Canonical field names/types remain in `src/mge_interfaces/msg` and `srv`; [ICD](ICD.md) controls semantics.

| Function / logical module | Requirements | Physical/software allocation, owner | Inputs -> outputs / consumer | State and evidence | Approval |
| --- | --- | --- | --- | --- | --- |
| F01 DataProvider | R03,R04,R05,R17 | `mge_data`, terrain config, data package; Daniel | Licensed public orbital products, CRS/datum/NoData -> TerrainMeta, immutable prior, manifest/control points; Mapping/Gateway | PENDIENTE canonical package. Main `tests/contracts/test_data_manifest.py` checks scaffold metadata only. Planner provisional crop and web crop differ. | Daniel data provenance; David scientific scale; Jesus batch binding |
| F02 BeliefMap | R04,R05,R06,R07,R09,R13 | `mge_mapping`; Daniel | TerrainMeta/prior and TerrainObservation -> coherent belief/sigma/kind masks with one map revision; Planner/Mission/Gateway | PENDIENTE actual fusion/publisher. Main `fuse_observation` raises NotImplementedError; `tests/mapping/test_observation.py` validates inputs only. | Daniel; Jesus atomic snapshot; David uncertainty |
| F03 RoutePlanner | R07,R08,R09,R10,R18 | `mge_planning`; Diego | Complete public map batch, profile, PlanRoute -> candidate RouteDecision only; MissionManager | REAL at planner SHA. `tests/planning/test_routes.py`, `test_adapter.py`, `test_kernel_guards.py`, `tests/contract/test_planner_service.py`; resources BLOQUEADO pending model agreement. | Diego algorithm; David resources; Jesus ROS |
| F04 MissionManager | R01,R05,R09,R10,R11,R12,R13,R16,R18 | `mge_mission`, science profiles/config; David | Goal, current poses/map, candidate decisions, explicit execution evidence -> single authorized MissionState/events/active Path; Gateway/Executor | REAL at mission SHA. `tests/mission/test_manager.py`, `test_models.py`, `test_adapter.py`, `tests/contract/test_mission_service.py`. Full execution/discovery input binding BLOQUEADO. | David science; Jesus integration |
| F05 SimulationAdapter | R02,R05,R06,R09,R13 | `mge_sim`, Gazebo bridge; Jesus with Daniel | Public agent configuration, evaluator-only controlled simulation -> AgentState/SIMULATED TerrainObservation; Mission/Mapping | MOCK at integration SHA; `tests/integration/test_vertical_mock.py`. Gazebo motion, sensor footprint and stop acknowledgement PENDIENTE. | Jesus execution; Daniel observation; David scenario |
| F06 WebGateway | R13,R15,R17,R18 | `mge_gateway`; Jesus | Authoritative ROS state/events/meta -> JSON 1.0.0 and canonical recorder package; Web | REAL at integration SHA; `tests/contracts/test_gateway.py`, `tests/unit/test_store.py`, `test_replay.py`, `tests/integration/test_replay_package.py`. No raster recording yet. | Jesus; Jorge consumer |
| F06 MissionView | R04,R14,R15,R17,R18 | `web/`; Jorge | Canonical replay through deterministic adapter, public rasters and authoritative route -> display only | REAL legacy viewer at web SHA; `web/tests/{coords,replay,management,terrainSmooth,astronaut}.test.ts`. Source MOCK label and public reference removal BLOQUEADO; canonical end-to-end browser consumer PENDIENTE. | Jorge visual; Jesus payloads; Daniel raster provenance |
| F07 TestHarness | R01-R18 | `tests/`, CI, `evidence/`; all owners, Jesus integration | Fixed sources/configuration/scenarios -> immutable commands, results/hashes/rejections | REAL contract scaffolds and branch tests; combined real stack and scientific acceptance PENDIENTE. See baseline validation record. | Jesus software; David system/science; owners module checks |

## Requirement evidence ledger

| Requirement | Function / responsible | Available evidence at audited revision | Missing system acceptance / state |
| --- | --- | --- | --- |
| R01 primary and return | F04,F07 / David | Mission `test_manager.py`, `test_success_criterion.py` | Actual start-goal-return/execution evidence PENDIENTE |
| R02 three agents/scalable IDs | F05,F07 / Jesus | Integration `test_vertical_mock.py`, agent configuration | MOCK graph only; real simulated startup and six-agent config proof PENDIENTE |
| R03 MRO and MGS/MOLA | F01,F07 / Daniel | Planner provenance and fresh CTX crop; web CTX provisional extraction | Canonical licensed products and justified scientific scale PENDIENTE |
| R04 shared ENU/NoData | F01,F02,F06,F07 / Daniel,Jorge | Planner adapter/geometry tests; web `coords.test.ts` | Same dataset/three georeferenced control points BLOQUEADO |
| R05 prior/belief/reference | F01,F02,F04,F05,F07 / David,Jesus | Planner public-only API; baseline rejection guards | Web public `rasters.json.reference` and evaluator toggle violate distribution isolation; public fixture BLOQUEADO |
| R06 footprint observations | F02,F05,F07 / Daniel | Main observation input tests; integration MOCK revision flow | Real footprint/sigma/atomic revision producer PENDIENTE |
| R07 traversability | F02,F03,F07 / Diego | Planner corners, barriers, unknown/profile gates in `test_routes.py` | REAL algorithm; canonical masks and scenario acceptance PENDIENTE |
| R08 routes/costs | F03,F07 / Diego | Planner independent Dijkstra minigrids, FAST/SAFE and bounded search tests | REAL algorithm; operational cost authority BLOQUEADO |
| R09 current pose/replan | F02-F05,F07 / Diego,Jesus | Planner stale guards; mission route invalidation/empty path tests | NON_CELL_CENTER explicit rejection; real execution stop acknowledgement PENDIENTE |
| R10 resources/reserves | F03,F04,F07 / David,Diego | Planner budgets and mission itinerary audit | Distance vs activity/grade formula equivalence BLOQUEADO; budgets remain experimental |
| R11 precedence | F04,F07 / David | Mission optional-task/precedence tests | REAL core; ROS discovery/work evidence input PENDIENTE |
| R12 optional preserves return | F03,F04,F07 / David,Diego | Mission accepted/rejected controlled optional task cases | Model agreement and complete executed consumer case BLOQUEADO |
| R13 authority/IDs | F02,F04-F07 / Jesus | Mission idempotency, gateway store dedup/order and MOCK ROS tests | REAL branch boundaries; cross-branch real stack and conflict semantics PENDIENTE |
| R14 understandable display | F06,F07 / Jorge | Legacy viewer management/replay tests and branch README browser report | Canonical payload error cases, data-owner controls and outside-viewer review PENDIENTE |
| R15 offline replay | F06,F07 / Jesus,Jorge | Gateway file-level package test; web legacy offline report | Canonical gateway-to-existing-viewer round trip with public rasters PENDIENTE |
| R16 A/B/C benchmark | F04,F07 / David,Jesus | Mission `docs/science_benchmark.md` protocol; planner seeded search checks | Controlled search benchmark is not mission A/B/C; frozen protocol and runs PENDIENTE |
| R17 compliance | F01,F06,F07 / everyone | Existing AI disclosures and third-party notices | Public reference audit, English submission and official eligibility review PENDIENTE |
| R18 invalid states | F03,F04,F06,F07 / everyone | Six canonical route status constants; branch rejection tests | REAL software cases; all states through canonical viewer and real stack PENDIENTE |

## Divergences and required adaptation

| Shared boundary | Producer -> consumer | Divergence | Required action / decision owner |
| --- | --- | --- | --- |
| Replay | Gateway recorder -> existing viewer | JSON 1.0.0 uses timeline.jsonl/snapshot; legacy web uses mge-web-0.1-draft timeline.json/routes.json/rasters.json | Use [replay contract](REPLAY_CONTRACT.md), keep source fixtures, map deterministically, refuse missing public rasters; Jesus/Jorge |
| Provenance/modes | MOCK ROS -> Gateway/Web | Current sample recorded_from LIVE denotes transport, while sources are MOCK; a replay can originate from a mock | Preserve REPLAY display plus explicit MOCK source; clock=system is not mission simulation; Jesus/Jorge |
| Dataset | Provisional planner crop -> web terrain | ~128 m / 4 m near 18.45N,77.45E vs ~2 km / 20 m near 18.53545N,77.42382E | Never combine by version alone. Daniel selects dataset/CRS/datum/grid and 3 controls, both consume matching IDs/hashes |
| Raster transaction | Mapping -> Planner | Native images lack run/version; cross-topic delivery can reorder | Unique stamp for run/version, metadata then repeated complete same-stamp batch, strict immutable association; Daniel/Jesus/Diego |
| Cost formulation | Planner -> Mission | Planner distance/slope rates differ from mission activity/grade and directed climb; projection status pending_model_agreement | David owns operational audit model; Diego retains search. Record model ID/config hash, compare complete itineraries including service/return, no approval by parameter conversion |
| Position | Continuous AgentState -> cell graph | Planner requires XY centres within 1e-6 m | Pass unchanged; reject NON_CELL_CENTER. Any connector needs collision/uncertainty checks and explicit charged costs before new approval; Diego/Jesus/David |
| Route/stop | Mission -> Executor | Empty route ID/path invalidates logically, no physical acknowledgement implemented | One authorized route; clear old command on map change; executor confirms stop separately; Jesus |
| Task evidence | Sim/discovery -> Mission | Typed Python evidence exists, no agreed operational ROS transport | Bind explicit observations/completions; planner and gateway must not invent scientific/task policy; David/Jesus |
| Service providers | MOCK vs real modules | Existing vertical launches mock planner/mission together | Distinct mock/integration/live-simulation profiles; one provider per canonical service, deterministic contract replacement test; Jesus |
| Evaluator reference | Web fixture -> public export | Legacy raster type requires reference, bundled and revealable via query | Quarantine fixture from public distribution; remove reference values/files from public build and adapt type/loader. A hidden toggle cannot secure a downloadable resource; Jorge/Daniel |

## Additive baseline verification scope

After the reconciliation lands, run `python -m pytest tests/contract/test_baseline_guards.py tests/contract/test_replay_conversion.py tests/contract/test_dataset.py tests/integration/test_provider_substitution.py`.
These are contract guards/controlled substitution tests, not replacement
implementations for the owning modules and not full mission acceptance.
The dataset schema checks package shape and isolation, not geodetic/scientific
correctness. Replay conversion checks deterministic recorded payloads, not a
complete rendered viewer with unavailable rasters. See the baseline validation
record for commands actually executed on this cut and target-platform omissions.

## Review and integration order

1. Review/land the additive reconciliation baseline; do not claim it is main
   until the PR is merged. Preserve all owning branch implementations.
2. Jesus reconciles PR #3 against the baseline: typed serialization, MOCK source,
   profile exclusivity, replay consumer, without adopting mock scientific logic.
3. Daniel delivers the public coherent dataset; Jorge adapts the existing viewer
   and removes reference from public artifacts. Crop selection remains explicit.
4. David and Diego approve full-itinerary numerical model agreement, then Jesus
   substitutes the real PlanRoute and MissionManager providers. PR #2 and the
   mission work retain their implementations; evaluate them independently.
5. Run stop/invalidation, idempotency, return/reserve and backend-off replay with
   the exact combined SHAs/configuration; David approves system acceptance.
6. Reconcile PR #4 documentation after these decisions so it reports evidence,
   not planned completion. No automatic merges of these PRs are authorized here.
