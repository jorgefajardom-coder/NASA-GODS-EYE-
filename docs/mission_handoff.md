# Mission implementation handoff

Owner: David. Integration reviewer: Jesus. Work branch: `feat/mission`.

This record describes implementation boundaries, not a verified end-to-end
mission. Scientific coefficients remain proposed until David approves them.

## Integration dependencies

- Use the same scientific model and profile configuration in planner and mission.
  The planner's original distance-based model is an approximation of the new
  activity/grade model. A configuration projection does not make them equivalent.
- Existing ROS messages do not carry a model hash. Numerical cost agreement is
  necessary but cannot prove configuration identity; retain the model/configuration
  identity in the run record and review deployment configuration together.
- The planner currently requires XY positions at grid cell centres. Pass observed
  poses unchanged and propagate `NON_CELL_CENTER`; never silently snap a pose.
- Confirm the metadata/layer batch association with data and integration owners.
  A topic name does not establish a run, map version or complete snapshot.
- An empty active path and an empty authoritative route ID invalidate a command.
  Jesus must verify that the execution consumer observes this signal before any
  stop acknowledgement is claimed.
- Discovery, task completion and ground-traversal evidence have typed Python
  boundaries but no agreed operational ROS input yet. Do not synthesize them.
- The first active-path publisher controls only the primary human. Robot optional
  assignments are decisions awaiting an execution binding, not moving robots.

## Verification record

Record commands, actual outcomes, configuration identifiers and limitations after
the checks run. A unit test or static build is not ROS or scientific acceptance.

No live mission, Gazebo execution, physical safety, accepted benchmark or
competition submission is established by this handoff.

## Delivered and checked

The pure core provides immutable profiles/mission/task/evidence values,
activity/grade costs, idempotent goals, ordered events, remaining-allocation
checks, explicit return priority and optional inspection/sampling decisions.
Human sampling follows primary B and completed inspection at the same site.
New routes invalidate old return/traversal/budget evidence. Missing execution
evidence cannot be replaced by a FEASIBLE candidate.

The ROS adapter serves the existing goal contract and calls a controlled planner
successfully on Jazzy. No message/service definition was changed. Explicit
configuration, profile approval, actual simulation time and model agreement gate
route publication. Current default templates remain unavailable intentionally.

Software checks: 226 Windows Python cases, 162 Jazzy mission/contract cases,
eight compiled ROS packages/eight inspected interfaces, two frontend cases and
the frontend build. See [verification](verification.md) and the retained
[validation record](../evidence/mission-validation-20261114-v2/validation.json).

Next integration handoff: Diego adopts or explicitly reconciles the science
model; Daniel supplies the public, coherently versioned scenario; Jesus binds
execution/discovery/evidence inputs and verifies empty-path invalidation; David
reviews coefficients, budgets and tolerances before operational approval. Keep
the benchmark protocol fixed before collecting comparison results.

## Independent continuation after the first publication

The mission adapter now accepts the published planner's unavailable failure
metrics and map-batch response timestamps without activating failed routes.
The [published-source conformance report](planner_model_conformance.md) records
one agreement and six disagreements across seven synthetic cases. The human
slope case underestimates energy under the declared science model; a projected
profile is not a proven conservative bound. Do not loosen tolerances or approve
model agreement to hide these differences.

The [benchmark evidence auditor](benchmark_evidence.md) is executable and its
templates remain drafts. It preserves failed/unknown attempts, validates hashed
exports and first-attempt pairing, and reports missing data explicitly. No
integrated A/B/C run was supplied or generated.

The [follow-up validation](../evidence/mission-followup-validation-20261114/validation.json)
records 348 passing Windows cases and 294 passing Jazzy cases, eight compiled
packages/eight inspected definitions and exact hashes for the tested source.
Linux executes the symlink-isolation cases unavailable on Windows. The actual
published-planner probe is separate from the optional snapshot test in the
Linux build copy.

## Public evidence recording and coefficient sweep

The [recorder/exporter and sensitivity API](mission_recording.md) are available
without new ROS fields or planner changes. The recorder accepts typed public
execution observations, preserves raw causal records and exports hashed files
for the existing auditor. A final explicit traversal closure is required for
full verification; missing measurements remain unknown. Runtime wiring stays
with the integration front and no execution evidence is invented here.

The coefficient sweep uses illustrative directed routes/services/waits and
existing reserves, varying traced low/nominal/high values independently. Its
reports are model checks and cannot enter mission A/B/C results. The operational
scenario and scientific approval remain pending Daniel and David respectively.

## Published public scenario and persistent evidence

This branch reconciles published main `6ec9b84` while preserving the other
owners' implementations. Daniel's public sample is now available through his
loader; [scenario diagnostics](mission_scenario.md) validate it and export a
hash-bound candidate, without selecting or approving operational inputs.
Dataset validity does not make unobserved cells traversable or approve budgets.

The [optional recorder journal](mission_recording.md) adds fsync-before-memory
acceptance, same-run recovery, exclusive writer locking and a hashed journal
export. Corrupt/truncated journals fail without repair; a sealed partial export
cannot be silently retried as another outcome. In-memory use stays compatible.

Published dependency audit: planner `8259001` still uses the search cost model;
the refreshed seven-case comparison remains one agreement/six disagreements and
authorization BLOCKED. Integration `5294832` adds replay source provenance and
typed serialization, not operational discovery/completion/traversal inputs or
stop acknowledgement. Both promised connections remain pending their owners;
no substitute planner or execution mock was added for this cut.

Delivery coordination remains pending: Jesus leads organizer notification and
explicit endorsement, David is backup (JES-07/AC-10). This software handoff does
not claim readiness to submit or organizer approval.

## Direct integration reconciliation

The owner requested integrating the remaining `feat/mission` advances directly
if GitHub rules permit. At inspection, mission PR #10 was already merged;
the open conflicting PR #12 belongs to the planner and is not part of this
operation. Main `4b72d30` includes the real mission-provider handoff, complete
viewer and Jezero integration cut. Reconciliation retains our newer journal,
recovery and scenario tools alongside those published modules and interfaces.
Only documentation and the mission validation helper required conflict resolution.

GitHub reported main unprotected with no applicable branch rules or rulesets.
The direct integration is specific owner authorization, not a relaxation of
normal team review requirements. Model agreement, operational evidence inputs,
stop acknowledgement and scientific approval remain separate pending gates.
