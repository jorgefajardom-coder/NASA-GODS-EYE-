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
