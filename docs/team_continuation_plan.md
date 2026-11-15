# Team continuation plan — 14 November 2026

See the [science extension tree](science_extension_tree.md) for proposed
post-base capabilities and verified prerequisites. It does not reopen scope.
New unlisted ideas may be assessed in an isolated local branch for discussion
on 15 November 2026 (America/Bogota), under the D-DEL-03 clarification; no
extension push, merge, deployment or acceptance is authorized by that assessment.

**Superseding delivery cut:** [current conclusions, PDF disposition and tasks](delivery_closure_plan.md)
and accepted [D-DEL-03](decisions/2026-11-14-delivery-freeze.md) now govern priority.
PR28 at main9198b3d publishes the basic estimated-map/observation/replay cut.
Larger maps, new scenes/agents and H-DAN-01 are paused until after submission;
the CONT-* checklist below is retained as the earlier engineering plan, not
permission to continue extensions during the freeze. New patch/campaign research
is summarized without adopting local draft coordinates or resource budgets.
Submission target remains 15 November 20:00 America/Bogota, with earlier closure
cuts and organizer review. Full mission acceptance remains open.

Owner-requested next assignments, based on the five integration cuts discussed
in the planning and Conciliación chats. This is a work plan, not completed
acceptance, scientific approval, an ICD freeze or permission to bypass reviews.
Use it with the [mission checklist](mission_checklist.md),
[ownership](team.md), [ICD](ICD.md), [contract baseline](CONTRACT_BASELINE.md),
[D-EST-01](decisions/2026-11-14-estimated-terrain-planning.md) and
[NASA traceability](nasa_traceability.md).

## Starting point and planning assumptions

- Planning source: main `5ab1387d1943d8bd1cc10f01c162e95634642349`.
  PR12 is integrated, including experimental continuous ground starts and the
  ROS-independent replanning policy; PR17 supplies the primary-agent MOCK
  executor, recorder corrections and separate map/service callback groups.
  Before publication this documentation is reconciled with published main
  `9589507397ca8161e51c928efc81831469aa637f`, which adds PR18's integration-test
  ROS-domain isolation. No open owner PR or pending local replay work is imported.
- **Jorge Fajardo's latest publication is assumed usable for these new
  assignments, as explicitly requested by the owner.** Its verification and
  publication reconciliation continue in Conciliación. Do not assign him to
  rebuild the loader/demo or repeat that review as this plan's next task.
  This assumption does not claim that the future integrated mission has run.
- Main's executor follows the primary agent; states for three agents do not
  yet establish three executed roles. PR12 does not wire the policy into
  MissionManager, implement D-EST-01, approve cost models or enable continuous
  starts by default. These are the next integration deliveries below.
- Daniel is **already investigating larger-map import and analysis**. Continue
  that study now; keep the reproducible 128 m Jezero case as the control.
- ROS stays ICD-ROS2-V1/package 1.0.0; canonical JSON/replay stays 1.0.0,
  public rasters `mge-public-rasters-1.0.0`, baseline review 1.0.0-rc.1,
  not frozen. This documentation changes no runtime contract or approval.
- P0 covers mission closure and the owner's new coordination/research
  deliverables. P1 covers experimental expansion after feasibility review.
  Preparation may run in parallel; an extension does not close steps 4/5.
  Detailed expected/desired hours remain in Git-ignored `.local/planning/`.

## Shared target and integration order

Target one explicitly labelled MOCK kinematic mission on public Jezero data:
estimated-prior route proposal → executed drone survey → rover inspection →
local contradiction → invalidation and acknowledged stop → new authorized
route from current pose/resources → human primary work at B → return to A →
closed evidence packages → offline replay and video of **that same run**.
David reviews the causal scenario and next-segment inspection policy before
execution; an initial estimate is not certified passage.

| Cut | Lead / contributors | Exit evidence and dependencies |
| --- | --- | --- |
| C1 — scenario and boundaries | David + Jesús; all owners review | Agreed costs, evidence/command boundaries, estimated-cell policy and drone scope. Builds on PR12/17; keep one mission authority and existing APIs. |
| C2 — parallel consumer deliveries | Daniel + Diego; David + Jesús; Jorge | Tested estimated-route/observation boundary; task/executor bindings; scientific-patch dossier and larger-map feasibility in parallel; reproducible site deployment prepared. Uses C1 decisions, with labelled fixtures while dependencies are unavailable. |
| C3 — three-role nominal run | Jesús; David accepts, Daniel/Diego support | Same-run survey/inspection/work/return, stop acknowledgement, authorized replan and resource accounting. Requires the P0 runtime boundaries from C2; does not wait for a larger map or random generator. |
| C4 — negatives and recorder closure | David + Jesús; Diego/Daniel | Adverse cases below, closed gateway and scientific evidence, retained failures. Requires C3 wiring; negative fixtures can be developed during C2. |
| C5 — public replay, video and shared access | Jorge + Jesús; team consumes | C3/C4 package validated and replayed without backends, matching IDs/hashes and source labels; two members reproduce access. Site deployment work starts during C2 rather than waiting for C4. |

Keep C3/C4 (step 4 and AC-05/06) and C5 (step 5 and AC-08) open until their
evidence exists. The five cuts are dependency order, not elapsed-time promises.

## David — mission authority and scientific acceptance

- [ ] **CONT-DAV-01 / P0 / C1:** agree one executable experimental scenario
  with Diego and Jesús: roles, A/B, task precedence/duration, remaining
  resources, reserves, current ground pose/datum and next-segment
  inspection/stop/return rules. Specify drone height, survey footprint and
  illustrative consumption explicitly; ground-surface z is not flight altitude.
  **Accept:** reviewed configuration/model hashes and numerical itinerary
  comparisons for flat/uphill/downhill, motion, waiting, service and return.
  Charge each activity once; preserve MODEL_NOT_AGREED/MODEL_MISMATCH until
  the required agreement is evidenced. Existing scenario-value approval is
  retained and does not substitute for coefficient/model approval.
- [ ] **CONT-DAV-02 / P0 / C2-C4:** bind mission phases and task/evidence
  decisions with Jesús using the existing discovery, assignment, start,
  completion and evidence APIs. **Depends:** CONT-DAV-01 and CONT-JES-01.
  **Accept:** completed work and traversal require received evidence;
  optional tasks obey survey → inspection → sampling and primary/return
  priority. Return, resources and outcome predicates agree with recorded
  execution; a correct rejection does not set mission success.
- [ ] **CONT-DAV-03 / P0 / patch selection:** review Jorge's NASA-criteria
  dossier and Daniel's coverage/feasibility report. **Depends:** CONT-JOR-01
  and CONT-DAN-01. **Accept:** a reasoned selected/deferred patch list with
  scientific rationale, usable source products, uncertainty and access/resource
  limits; no unsupported science score or threshold called a NASA standard.
  Keep the existing baseline running while this review proceeds.
- [ ] **CONT-DAV-04 / P1:** fix scenario families, seeds, comparison metrics,
  tolerances and expansion stop conditions before collecting experiments.
  **Accept:** paired conditions for any A/B/C comparison; publish N, failures,
  correct blocks and mission successes separately. Review H-DAN-01 assumption
  bounds before generating details. Scientific approval remains David's role.

## Daniel — public terrain, observations and larger-map feasibility

- [ ] **CONT-DAN-01 / P0 / already in progress:** finish the larger-map
  import/analysis feasibility report, coordinating candidate coverage with
  Jorge's dossier. Compare the 128 m control and tentative 256/512 m extents
  at constant grid resolution where source coverage permits. **Accept:**
  product/extent/CRS/datum, native and computational resolutions, NoData
  coverage, import commands and hashes; memory and coherent-batch latency.
  Diego measures planning and Jorge replay load on the same candidates.
  Publish a supported size recommendation, limits and a fallback to the
  control; do not silently replace the baseline or fabricate missing coverage.
- [ ] **CONT-DAN-02 / P0 / C1-C3:** implement D-EST-01 jointly with Diego:
  valid prior starts estimated with `observed=false`; preserve uncertainty,
  NoData and confirmed obstacles. Bind simulated survey observations to the
  executed footprint with Jesús. **Accept:** hypothetical route before local
  observation; one version increment per accepted observation; changes only
  inside the footprint; coherent stamps/layers; duplicates and stale/foreign
  observations cannot undo newer evidence or turn NoData into free terrain.
- [ ] **CONT-DAN-03 / P0 baseline controls, P1 expanded dataset:** validate
  the current Jezero control evidence and supply any missing controls for C2/C3
  without waiting for new-patch research. After CONT-DAV-03, package the selected
  feasible new patch with its own controls. Give Diego/Jorge three independently
  checked non-collinear controls, including an asymmetric point, for each grid.
  **Accept:** reproducible import/resampling, versioned public metadata,
  unit/datum checks and control residuals within an agreed tolerance; evaluator
  reference remains private. The current manifest already identifies CTX,
  HiRISE reference and MGS/MOLA products: verify their contribution rather
  than assigning their import again as if absent.
- [ ] **CONT-DAN-04 / P1:** retain [H-DAN-01](research_hypotheses.md) as the
  optional informed synthetic-detail experiment, after David's bounds review.
  **Accept:** same family/seed/configuration reproduces array hashes; declared
  structural differences affect connectivity/costs or yield an honest unchanged
  decision. Separate terrain/sensor/policy random streams and retain all runs.
  Only simulated sensor footprints reveal the private generated world. Finer
  sampling is not improved native observational resolution.

## Diego — authorized recovery and scalable planning

- [ ] **CONT-DIE-01 / P0 / C1-C3:** wire the existing ReplanPolicy to
  authoritative phase, cursor/progress, coherent 3-D current pose, remaining
  resources and unfinished service with David/Jesús. Enable continuous starts
  only through an explicitly reviewed experimental configuration.
  **Accept:** mid-segment stop → valid connector with cost → detour or
  contingency RETURN candidate from the actual stopped pose. Preserve return
  context, reserves, bounded retries and stale-result rejection; adoption and
  motion require a new MissionManager authorization. No pose snapping,
  telemetry-height projection or resource reset.
- [ ] **CONT-DIE-02 / P0 / C2:** consume the agreed estimated-cell policy
  with Daniel and close the numerical model comparison with David.
  **Accept:** initial estimated route, contradictory footprint, all-alternatives
  blocked, NoData refusal and return-budget rejection; UNKNOWN remains valid.
  Run the existing D-07, continuous-start and policy regressions plus actual
  mission/service consumer cases. A new core test alone does not close C3.
- [ ] **CONT-DIE-03 / P1 / supports CONT-DAN-01:** benchmark unchanged
  scenarios over larger extents before recommending a new integration size.
  **Accept:** input/config hashes, cell counts, memory, ingestion and
  PlanRoute/replan p50/p95 latency, SEARCH_LIMIT/UNKNOWN rates and correctness
  checks. Agree limits before evaluation; retain failures instead of hiding
  scaling problems by increasing deadlines or changing the scenario.

## Jesús — three-role execution, recording and deployment integration

- [ ] **CONT-JES-01 / P0 / C1-C3:** reconcile per-agent commands and
  discovery/task/traversal evidence with David; preserve MissionManager as
  the single authority. Extend execution beyond the current primary follower
  to drone survey, rover inspection and human work/return. Reuse
  `discover_task`, `assign_optional_task`, `start_task`, `complete_task` and
  `record_evidence`; do not duplicate mission logic in gateway/executor.
  **Accept:** each command/result binds run/agent/task/route/map context;
  sensor observations follow executed footprints; three identifiable role
  contributions are evidenced, rather than three published markers.
- [ ] **CONT-JES-02 / P0 / C3-C4:** connect invalidation, simulator
  stop feedback, replan and reauthorization with Diego. **Accept:** old route
  clears; affected agent reports HALTED, zero velocity and a stable pose;
  only the new authorized route resumes movement. Check stale replies,
  duplicate/conflicting IDs, resource depletion and backwards-clock reset.
  A cleared path alone is not a stop acknowledgement.
- [ ] **CONT-JES-03 / P0 / C4-C5:** close and validate both evidence outputs
  with the same run identity: gateway `manifest/timeline/snapshot/public_rasters`
  for the viewer, and mission `EvidenceRecorder` execution/traversal/outcome
  records for audit. **Accept:** explicit traversal closure and outcome
  predicates, matching IDs/events/costs, complete per-version public rasters,
  hashes and no writes after sealing. These are complementary packages, not
  interchangeable formats. Supply Jorge the exact approved gateway package.
- [ ] **CONT-JES-04 / P0 / starts C2:** co-own CONT-JOR-02 deployment:
  document static replay hosting separately from the ROS/gateway development
  environment, validate fresh setup and public assets, and provide a previous
  working revision/rollback. **Accept:** the team's two-machine checks pass;
  unavailable LIVE controls remain unavailable. Record the revision, URL and
  configuration without publishing credentials or private contact details.
- [ ] **CONT-JES-05 / P0 / delivery:** lead JES-07/AC-10 organizer contact
  when the reviewable submission is ready; David is backup. Reserve at least
  four hours before intended submission, or longer if requested. Record
  notification/package revision, explicit endorsement and closed corrections.
  Silence is pending, not approval; confirm the actual local deadline.

## Jorge Fajardo — science-patch dossier and shared site access

- [ ] **CONT-JOR-01 / P0 / new research assignment:** investigate the
  technical criteria NASA missions use to identify scientific POIs and select
  study/sampling areas, then recommend candidate patches with David/Daniel.
  **Deliver:** a source-linked dossier and candidate matrix: scientific
  objective → published criterion → observed supporting product → uncertainty
  → technical coverage/accessibility → recommendation. Use primary NASA/JPL
  material and identified NASA/USGS maps/products; record page/section, date,
  mission/instrument context and exact product IDs. Distinguish landing-site,
  local science-target and sampling criteria when the sources do. Mark team
  interpretations/weights separately; this plan asserts no universal NASA
  formula. **Accept:** David can audit the rationale and approve selection;
  Daniel can locate and import the underlying data. This research informs new
  patches without blocking closure of the existing mission control case.
- [ ] **CONT-JOR-02 / P0 / new deployment assignment, with Jesús:** make the
  usable published viewer reproducible for the team. **Deliver:** deployment
  guide from clean clone, pinned Node from `web/.nvmrc`, `npm ci`, `npm test`,
  `npm run build`, local preview/static-server instructions, public URL,
  deployed source revision and package/config hashes. **Accept:** two members
  on separate machines open the same replay in a clean browser with ROS and
  gateway off; assets and paths work at the actual hosting subpath; no dependency
  on the author's localhost, private disks or evaluator data. Verify load/seek,
  console/network, source labels and licences; record rollback/fallback steps.
  Static deployment does not host ROS or establish a LIVE mission connection.
- [ ] **CONT-JOR-03 / P0 / C5:** use the accepted viewer for the next
  integrated three-role package from CONT-JES-03; replay and record that exact
  run. **Accept:** run/dataset/map/route/event IDs, snapshot closure, resources
  and outcomes match the package; seek before/after observation, stop, replan,
  work and return preserves causal visibility. Show estimated versus observed
  terrain and reasons without future discoveries or active obsolete routes.
  Retain video revision/package hashes and required disclosures/watermarks.
  This is acceptance of a new run, not a request to redo the published demo.
- [ ] **CONT-JOR-04 / P1 / supports CONT-DAN-01:** measure larger-map load,
  seek, memory and rendering responsiveness; adapt framing and agent selection
  as needed on the accepted viewer. **Accept:** agreed size/performance limits
  and controls remain readable; extra agents require actual command/execution
  support before being described as a coordinated fleet.

## Acceptance matrix and expansion gates

| Case / existing acceptance | Required evidence |
| --- | --- |
| Initial estimate / D-EST-01, AC-02/04 | Unobserved valid prior supports a hypothetical candidate; NoData, uncertainty and obstacles retain their distinct meaning. |
| Three roles / AC-05 | Executed survey, inspection, human primary work and return, with orders/states/evidence in one run. |
| Stop/recovery / AC-04/05 | Contradiction → invalidation → HALTED/zero speed/stable pose → new candidate from current resources/pose → authorization → resumed execution. |
| Costs and adverse cases / AC-03/06 | No double charge or replenishment; blocked alternatives; unaffordable return rejected before motion; optional accepted/rejected and premature sampling deferred. Correct rejection stays distinct from mission success. |
| Recording/isolation / AC-07 | Closed scientific and gateway packages linked by run, hashes and contexts; evaluator reference, full synthetic worlds and future discoveries inaccessible to planner/public assets. |
| Same-run web/deploy / AC-08 | Validated package replayed and filmed without backends; two-machine access, temporal consistency and exact public rasters. A script-generated COMPLETE is not backend execution evidence. |

Add a dedicated three-role E2E to the existing suites; do not mark it already
implemented. Reuse current mission/planning cases, including
`tests/planning/test_d07_twenty_metres.py`, `test_continuous_start.py`,
`test_replan_policy.py` and `test_pr12_review.py` under that directory, plus
the ROS contracts and `tests/integration/test_vertical_execution.py`.
The latter currently demonstrates the human executor, not full three-role closure.

Expansion order: controlled complexity on the control map → supported larger
area at constant resolution → seeded H-DAN-01 variations → more agents after
the existing three roles execute. Change one axis per pilot; choose quantitative
limits before running and retain unsuccessful runs. Larger maps and NASA-criteria
research proceed now; adoption of a new baseline requires the joint review.

## NASA lineage, validation and handoff

For every patch or world retain: NASA/USGS product and native resolution →
window/processing/CRS/datum/resampling and hashes → public layers and any
explicit assumptions/generator version/seeds → simulated footprint observation
→ decision/run → evidence and replay claim. The current sample's CTX prior is
20 m native on a 4 m computational grid; HiRISE reference stays isolated, and
MGS/MOLA's regional contribution must be explained rather than merely cited.
Rover-image analogs need image/camera/sol or acquisition identifiers and the
specific assumption informed. This plan selects no scientific target or source
threshold on NASA's behalf and generates no terrain or observations.

For each delivery, preserve source SHA, baseline versions, input/output and
model/config hashes, commands, actual outcomes, limitations, blockers and next
deliverable. Existing dated handoff inventories remain historical; do not treat
their old branch heads or pending items as a fresh audit.

Review any shared command/evidence/agent-routing contract change with its
producers, consumers, tests and applicable version together. Do not reinterpret
the single primary active path as a fleet command channel to fit one consumer.
Jesús reviews integration and David scientific assumptions before acceptance.

Required validation commands:

```sh
python -m pytest
python scripts/check_repository.py

# Ubuntu 24.04 / ROS 2 Jazzy
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
python -m pytest tests/contract tests/integration
# Inspect all six mge_interfaces messages and both services with ros2 interface show.

# From web, using web/.nvmrc
npm ci
npm test
npm run build
npm run preview
```

CI and builds are prerequisites, not mission acceptance. Keep MOCK/SIMULATED/
REPLAY labels, licences and mandatory AI-use metadata/watermarks. Every member's
agent must remind its member of JES-07 at scope freeze, readiness and before
submission while organizer notification/endorsement evidence is missing. Keep
contact details and detailed hour forecasts private; do not mark submission
complete before explicit endorsement and submission confirmation.
