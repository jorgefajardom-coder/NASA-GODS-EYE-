# Probable roadmap: minimum mission checklist

Baseline selected by the project owner on 14 November 2026. This is the team's
working plan, not acceptance evidence, approval of scientific coefficients, or
confirmation that the draft ICD is frozen. Follow [ownership](team.md),
[requirements](requirements.md), [the ICD](ICD.md), and
[NASA resource traceability](nasa_traceability.md).

## Scope and definition of success

Demonstrate one simulated Jezero mission: human_1 leaves base A, reaches primary
goal B, performs the primary work and returns to A. drone_1 surveys and rover_1
inspects through explicit simulated execution/evidence inputs. A later footprint
observation blocks the active corridor before traversal; MissionManager
invalidates it and replans from the current pose. An optional task is rejected
when it would compromise the primary goal, return or reserves.

Use ROS 2 Jazzy on Ubuntu 24.04 with a simple kinematic simulation adapter as the
probable integration scope; Gazebo Harmonic is the target for any Gazebo work.
Detailed dynamics and camera reconstruction are outside this minimum. The public
demonstration is a recorded static replay. Test all three agents' actual role
bindings: publishing three MOCK states or making assignments does not prove
survey, inspection or execution.

Mission success requires primary completion, return within the pre-agreed
tolerance, verified ground traversal under the declared model, and no applicable
time/energy/oxygen budget violation. Return reserves remain separate. A correct
BLOCKED/ABORTED result can pass a rejection test while mission_success is false.
No physical Mars mobility, suit, flight or EVA safety certification is implied.

Coordinates, tolerances, resource budgets, coefficient approvals and the exact
crop must be settled before scientific acceptance. Illustrative runs require an
explicit opt-in and keep their labels. UNKNOWN orbital terrain is never silently
promoted to a verified corridor. Human optional sampling follows primary B;
survey/discovery precedes inspection, which precedes sampling.

## Priorities and evidence states

- P0: necessary to demonstrate, explain or submit the minimum mission honestly.
- P1: comparison or extension attempted only when the P0 path remains on time.
- A checked box closes only the named deliverable at its recorded revision.
  It does not close a whole R01-R18 requirement or downstream acceptance.
- Distinguish implemented, module-tested, consumer-tested and integrated-accepted.
  Put command, commit, configuration, input hashes, expected/observed outcome,
  limitations and reviewer next to the evidence. Never mark a forecast as actual.

## Starting evidence snapshot

Snapshot reviewed on 14 November 2026; update by adding dated evidence rather
than rewriting historical runs.

| Front | Available evidence | Still open |
| --- | --- | --- |
| Diego | FAST/SAFE kernel, guarded PlanRoute adapter, [handoff](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/34c515b6b86f73336844e8b3614c70b144574ec3/docs/planner_handoff.md), [new computational evidence](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/34c515b6b86f73336844e8b3614c70b144574ec3/evidence/planner-p0-20261114/README.md); [PR #2](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/pull/2). The [reviewed CI run](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/actions/runs/43611132353) has successful Python, web and ROS jobs. | Final terrain/profiles, resource-model agreement, producer protocol and complete mission. CI applies to its recorded revision, not all subsequent edits. |
| David | Parallel mission worktree contains proposed source-traced activity/grade models, authority/adapter work and 15 synthetic MODEL_CHECK estimates. Its latest progress report states 211 Windows tests passed with two ROS-only modules skipped; not rerun in this checkout. | Scientific coefficient approval, final mission configuration, route-cost agreement, execution evidence inputs and ROS/E2E acceptance. The mission front reports ROS validation underway on a Linux-path copy after a rosidl path issue. |
| Data | A [provisional CTX manifest](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/34c515b6b86f73336844e8b3614c70b144574ec3/data/planner_provisional/manifest.json) and a private HiRISE crop exist. CTX-only corridor check returns UNKNOWN as intended. | Daniel's final release, independent non-collinear controls, public observed masks and a meaningful separately identified MGS/MOLA contribution. |
| Integration / web | Existing contract guards and web build/tests. | Runtime state flow, execution bindings, recorder, offline replay and public browser acceptance. |

## Checklist by owner

### David: scientific configuration and mission authority

- [ ] **DAV-01 / P0 / M00, M02**: review parameter source/locator, unit,
  derivation, sensitivity and approval state; agree A/B, task durations,
  budgets and return tolerance after DAN-01/02. At M00 agree the region, mission
  intent and approval plan; final numeric scenario approval belongs to M02.
  **Acceptance:** AC-01 and AC-03;
  no implicit approval from an illustrative calculation.
- [ ] **DAV-02 / P0 / M02**: agree one cost contract with DIE-02: directed
  movement, activities, waiting, return and reserves, including human oxygen
  convention and model/configuration identity. **Acceptance:** the same path
  and activity schedule produce agreed costs in both modules within a tolerance
  declared before the check; discrepancy blocks authorization.
- [ ] **DAV-03 / P0 / M03-M05**: finish the single authority for current
  run/map/request, current remaining resources, pose and route invalidation.
  **Depends on:** JES-01 input contracts and the planner boundary in DIE-00.
  Deliver the authority API first; integrate it with JES-02/DIE-03 for
  **acceptance:** AC-04/05/06. A plan alone
  cannot prove motion, primary work, verified traversal or completion.
- [ ] **DAV-04 / P0 / M04-M05**: enforce task precedence and primary/return
  priority. **Depends on:** typed discovery/completion inputs from JES-02.
  **Acceptance:** AC-06; one optional task accepted and one rejected, with reasons.
- [ ] **DAV-05 / P1 / M10**: declare A/B/C policies, scenarios, N, seeds and
  metrics before execution. **Depends on:** accepted M04/M05.
  **Acceptance:** AC-09; keep failures and report exploratory limits.

### Daniel: source products, common grid and observations

- [ ] **DAN-01 / P0 / M01**: audit or replace the provisional CTX prior and
  isolated HiRISE reference; select a separate MGS/MOLA regional product and
  explain its contribution. **Depends on:** M00's preliminary region/mission
  intent; do not wait for final A/B approval, which consumes this data handoff.
  **Acceptance:** AC-01 and the NASA-CTX/HIR/MOLA records in nasa_traceability.md.
- [ ] **DAN-02 / P0 / M01**: deliver geometry, datum, NoData, uncertainty and
  at least three independently checked non-collinear controls, including an
  off-diagonal/asymmetric point. **Acceptance:** AC-02 with Diego and Jorge.
  The provisional manifest's three row=col controls lie on one diagonal and
  alone cannot detect an x/y transpose. A finite-pixel mask is not observed terrain.
- [ ] **DAN-03 / P0 / M03-M05**: apply simulated observations only within their
  footprints, with source kind, uncertainty, observation ID and one map-version
  increment per accepted observation. **Depends on:** the JES-01 evidence-input
  contract; prepare fixtures first, then integrate with JES-02's execution binding.
  **Acceptance:** AC-04/07, including duplicate and out-of-bounds observations.
- [ ] **DAN-04 / P0 / M03**: publish coherent metadata/belief/sigma/profile-mask
  batches with the agreed unique-stamp/retry protocol. **Depends on:** JES-01,
  DAV-02 and the producer protocol already documented by DIE-00. **Acceptance:**
  AC-04 with DIE-03; missing/mixed batches stay unavailable.
- [ ] **DAN-05 / P1 / optional research**: explore
  [H-DAN-01: informed synthetic terrain and seeded adaptation](research_hypotheses.md#h-dan-01-informed-synthetic-terrain-and-seeded-planner-adaptation)
  only if P0 handoffs and delivery remain protected. **Depends on:** stable
  DAN-01..04 and DAV-02; David reviews assumptions, Diego evaluates adaptation.
  **Acceptance:** the hypothesis's pilot checks, reproducible structural diversity
  and truthful synthetic labels; no result or implementation is claimed yet.

### Diego: final-input planner acceptance

- [x] **DIE-00 / P0 / component only**: implement FAST/SAFE, resource-aware
  outbound/return candidates and guarded ROS service. Evidence: a6204dd,
  6e4984d, planner-p0-20261114 and the CI run above. Scientific/E2E acceptance
  remains open; EFFICIENT and D* Lite are outside the minimum.
- [ ] **DIE-01 / P0 / M01-M02**: rerun the existing D-01..D-10 cases against
  reviewed data/profile adapters. **Depends on:** DAN-02, DAV-01/02.
  **Acceptance:** AC-02/03; independent reference cost, corners, barriers,
  unknowns, directed return and resource-feasible alternative paths.
- [ ] **DIE-02 / P0 / M02**: reconcile the planner's distance-based profile
  with David's activity/grade model before operational authorization. A profile
  file projection is not proof of equivalence. **Acceptance:** AC-03; preserve
  model/configuration hashes in deployment/run evidence without inventing ROS fields.
- [ ] **DIE-03 / P0 / M03-M05**: exercise real consumer requests using coherent
  public batches and the observed pose. **Depends on:** DAN-04 and JES-01's
  request/pose contract. Integrate this tested boundary with JES-02 for execution.
  **Acceptance:** AC-04/05; stale results cannot reactivate a path. Preserve the
  current NON_CELL_CENTER rejection; never silently snap continuous poses.
- [ ] **DIE-04 / P0 / M04**: record final-input handoff, limitations and the next
  dependency so Diego can resume from the latest verified state.

### Jesus: contracts, execution, recording and delivery

- [ ] **JES-01 / P0 / M00**: obtain owner agreement on the draft ICD, batch
  protocol, time, grid-centre poses, oxygen semantics and model identity in
  deployment evidence. **Acceptance:** recorded owner decisions; do not call the
  ICD frozen before agreement or change wire semantics without coordinated tests/version.
- [ ] **JES-02 / P0 / M03-M05**: bind three-agent kinematic execution, simulated
  survey/discovery, inspection/completion and traversal evidence. **Depends on:**
  DAV-03, DAN-03/04 and DIE-03. **Acceptance:** AC-04/05/06; execution consumes
  route invalidation and acknowledges the stop before traversing the blocked area.
  Robot assignments alone do not demonstrate robot execution.
- [ ] **JES-03 / P0 / M03**: connect authoritative mission state to typed gateway
  payloads, preserving IDs/units/time and JSON-safe oxygen values.
  **Acceptance:** ROS/API/viewer agree on the same run, map, route and reason.
- [ ] **JES-04 / P0 / M04-M06**: record immutable manifest/snapshot/timeline and
  public terrain assets; exclude the hidden evaluator reference.
  **Acceptance:** AC-07/08 and the resource-to-claim audit.
- [ ] **JES-05 / P0 / M04-M05**: run positive, blocked and insufficient-budget
  cases on the integrated revision with David. **Acceptance:** AC-05/06;
  retain failures and distinguish mission success from correct rejection.
- [ ] **JES-06 / P0 / M00, M07-M09**: confirm the official local deadline and
  submission rules, coordinate source/license/AI audit, public links and final
  submission. **Acceptance:** AC-10 and submission confirmation, not merely a push.
- [ ] **JES-07 / P0 / M07-M09**: notify the local organizer when the reviewable
  submission package is ready and obtain explicit endorsement before final
  submission. Jesus coordinates; David is backup; everyone checks the gate.
  **Depends on:** JES-06, reviewable links/revision and source/AI audit.
  **Acceptance:** notification timestamp, exact package revision/links,
  organizer's explicit endorsement and closure of requested corrections retained
  in delivery evidence. Silence is not endorsement. See the coordination margin below.

### Jorge: explainable view and backend-independent replay

- [ ] **JOR-01 / P0 / M01-M03**: render the common grid/control points and
  public prior/belief/observed layers with the ICD ENU-to-Three.js transform.
  **Depends on:** DAN-02. **Acceptance:** AC-02; preserve scientific scale.
- [ ] **JOR-02 / P0 / M03-M05**: show authoritative agents, route changes,
  reserves and explicit UNKNOWN/NO_PATH/INSUFFICIENT_BUDGET/STALE_MAP reasons.
  **Depends on:** JES-03. **Acceptance:** an outside observer identifies the
  objective, discovery, decision and result; no independent browser planning.
- [ ] **JOR-03 / P0 / M06**: load the recorded public replay with no runtime
  gateway, ROS or Gazebo dependency. **Depends on:** JES-04.
  **Acceptance:** AC-08 in a private browser, with no reference leakage.
- [ ] **JOR-04 / P0 / M07-M09**: include English explanatory labels, source
  access and applicable AI disclosures; prepare a recording of the same verified
  execution as fallback. **Acceptance:** AC-10, including visible watermarks
  wherever required generated media appear in captures/exports.

## Acceptance cases to implement and record

These AC identifiers specify required evidence; this document does not claim that
new automated tests or runs already exist. Existing module tests are reusable.

| Case | Requirement / owner | Concrete pass condition |
| --- | --- | --- |
| AC-01 provenance | R03/R17; Daniel, David | Exact inputs, product/version, terms, timestamps and hashes resolve through the processing chain. MRO/CTX and MRO/HiRISE are not counted as two missions; standalone MGS/MOLA use is evidenced separately. |
| AC-02 geometry | R04/R07; Daniel, Diego, Jorge | Non-collinear controls agree within a predeclared tolerance; asymmetric mask catches row/axis inversion; NoData/unknown never become free verified cells. |
| AC-03 resources/search | R08/R10/R12; Diego, David | Independent reference cost on minigrids; no blocked-corner cuts; directed uphill/downhill return; an affordable alternative survives rejection of the fastest path. Same declared model costs agree across modules; activities/waiting charged once; reserve not spent. |
| AC-04 coherent state | R06/R09/R13/R18; Jesus | Duplicate observation has no second effect; wrong run, mixed stamp/layers, missing profile and stale request/pose are rejected; metadata retries cannot mix snapshots. |
| AC-05 minimum positive | R01/R02/R09-R11; David, Jesus | Three role executions evidenced; new obstacle stops/invalidates the old command, then replans from current pose; B/work/return completed, zero unsafe ground steps under model, full executed ground verification and no budget/reserve violation. |
| AC-06 negative/task cases | R07/R10-R12/R18; David, Diego | Block all alternatives: reasoned block/abort. Budget cannot fund return: reject before motion. One optional POI accepted, another rejected; sampling before primary/inspection is deferred. Rejection passes do not set mission_success=true. |
| AC-07 reference isolation | R05/R06/R13; Daniel, Jesus | With identical public prior/observations, changing the held-out reference does not affect planner decisions. Runtime/public package has no reference raster/path access or hidden future-task list. Only explicitly simulated footprint evidence may update belief. |
| AC-08 public replay | R14/R15; Jorge, Jesus | Private-browser replay works with all backends off, matches recorded IDs/decisions/results and explains changes. Label REPLAY and simulation; preserve permitted source metadata and exclude hidden assets. |
| AC-09 comparison | R16; David | Protocol fixed first; identical scenarios/budgets/seeds for A/B/C; publish N, failures and success/return metrics. Computational planner benchmark alone does not close this case. |
| AC-10 submission | R17; everyone, Jesus coordinates | Public links and English material work; sources/licenses and required AI text/metadata/watermarks audited; official cutoff confirmed; local organizer notified with review margin and explicit endorsement recorded (JES-07); requested corrections closed; explicit submission completed and confirmation retained. |

## Milestones, dependencies and cuts (America/Bogota)

Public times are desired coordination cuts, not forecasts or evidence of work.
Detailed expected/desired dates, remaining effort ranges, thread observations and
actual completion timestamps stay in the local Git-ignored `.local/planning/`
register. It is internal local planning, not a competition artifact or shared clock.

| ID | Desired cut | Owner | Exit / dependencies |
| --- | --- | --- | --- |
| M00 | Sat 14 Nov 12:00 | David / Jesus | Scenario/approval plan, consumer semantics and official cutoff recorded. |
| M01 | Sat 14 Nov 14:00 | Daniel | Traceable terrain/context and independent controls; scenario agreement from M00. |
| M02 | Sat 14 Nov 14:00 | Diego; David reviews | Common accepted resource calculation and profile identity; reviewed M01 inputs for final-input acceptance. |
| M03 | Sat 14 Nov 16:00 | Jesus; Jorge consumes | First map -> route -> view flow and explicit execution bindings; M00-M02. |
| M04 | Sat 14 Nov 20:00 | Jesus / David | AC-05 recorded minimum mission; M03. |
| M05 | Sat 14 Nov 22:00 | David / Jesus | AC-04/06/07 adversarial and negative evidence; may develop fixtures before M04. |
| M06 | Sun 15 Nov 12:00 | Jorge / Jesus | AC-08 accepted public replay; M04/M05 evidence. Prepare UI/loader before those runs. |
| M07 | Sun 15 Nov 14:00 | Jesus; everyone reviews | Traceability, license, claims and AI audit; M01-M06. |
| M08 | Sun 15 Nov 16:00 | Jesus / David backup | Scope freeze; reviewable package notified to local organizer for endorsement (JES-07); corrective work and delivery only. |
| M09 | Sun 15 Nov 20:00 | Jesus | Desired completed submission; applicable official cutoff takes precedence. |
| M10 / P1 | Sun 15 Nov 10:00 | David | A/B/C pilot only after M04/M05 and only if M06-M09 remain protected. |

M00 agrees a preliminary region/mission intent. M01 then delivers final data;
M02 closes numeric scenario and shared-cost approval against those data. Model,
fixture and adapter preparation can overlap this sequence. DAV-02/DIE-02 are one
joint review, not two approvals waiting on each other. Controlled publisher/client
tests precede executor integration, avoiding circular implementation dependencies.

If Gazebo work delays M03, keep the probable kinematic scope. If no ROS mission
flow exists at the 20:00 cut, activate the critical pure-core execution/replay
path and keep ROS/execution requirements explicitly open. If a required NASA
input, cost agreement or mission proof is missing, report partial completion.
A recording can back up a demo but does not close a failed offline-replay case.

The team deadline is 15 November 2026 23:59; this is not verification of the
organizer's local cutoff. Advance all cuts if that cutoff is earlier.

### Local organizer coordination gate

Notify the local organizer as soon as the package is ready for review. Reserve
at least **four hours before the intended submission**, or the organizer's
requested lead time if longer. For the desired Sunday 15 November 20:00
submission, the notification target is **16:00 America/Bogota or earlier**.
Confirm organizer availability and any earlier local cutoff at M00/JES-06;
advance readiness/contact accordingly. This margin is a team planning assumption,
not a verified official deadline or a promise of organizer availability.

If readiness slips, contact promptly and flag the reduced review margin; do not
wait until the final upload. An unanswered request is still pending: Jesus, or
David as backup, follows up through the agreed channel and resolves the gate
with the organizer before final submission. Retain revision/links, notification,
endorsement and correction evidence; keep personal contact details private.

Every member's agent must remind its member at scope freeze/delivery handoff,
when reporting readiness, and before submission until JES-07 evidence is
recorded. These are contextual work reminders, not an unattended scheduled alert.

## Required validation and closeout

Run `python -m pytest` and `python scripts/check_repository.py` from the root;
run `npm test` and `npm run build` from web with its pinned Node version. On the
target Ubuntu/Jazzy workspace run `colcon build --symlink-install`, source
install/setup.bash, inspect all six messages/two services and run the actual
root/ROS contract suites, including `python3 -m pytest tests/contract`.
Report unavailable checks. Passing these checks does not replace AC-01..10.

Keep every run under a new `evidence/<run_id>/` with command/environment,
commit/dirty patch if relevant, schema/model/configuration versions, source and
derived hashes, seeds, expected/observed outcomes, failures and limitations.
Jesus reviews integration; David approves scientific assumptions/success
criteria. Update [AI text](AI_USAGE.md) and [AI metadata](ai_usage.json) as actual
generated artifacts change. Never overwrite past evidence or remove failed runs.
