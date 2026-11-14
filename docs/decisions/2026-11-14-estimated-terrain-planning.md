# D-EST-01 — Plan over the orbital estimate and revise with observations

Recorded: 14 November 2026. Decision authority: project owner, explicitly
confirmed in the planning chat and previously in the Daniel scope discussion.
Status: **accepted scope decision; coordinated implementation and integrated
acceptance pending**. This record does not freeze the ICD or approve scientific
coefficients, physical safety or operational mission feasibility.

## Decision and superseded restriction

Every cell in the area of interest with a valid orbital prior starts as
**estimated**, carrying source identity, native resolution and uncertainty.
The planner **may propose routes through those estimated cells without a prior
local observation of every cell**. Remove observation as a blanket prerequisite
for planning. Such a route is a revisable hypothesis of passage under the
declared illustrative assumptions, not proof that the whole corridor is safe.

This supersedes earlier planning instructions that made all unobserved cells
ineligible merely because `observed_mask` was false. It also supersedes describing
the complete valid orbital prior as an initially unknown map. It does not erase
the provenance distinction between estimated and locally observed terrain.

Observations refine only their footprints. If they reveal an obstacle, excessive
slope, unsuitable terrain or another contradiction, invalidate the affected
candidate/active route and stop or hold affected execution as appropriate to
the simulator's stop/check policy. Replan from the actual current position and
remaining resources; if no admissible alternative is found, expose a reasoned
block/return/abort rather than assert passage. Do not continue using the obsolete
route or claim physical stop acknowledgement from an empty path alone.

## Boundaries that remain

- NoData/invalid/out-of-area cells are separate from a valid estimate. Missing
  heights are not fabricated or silently made free; confirmed obstacles stay
  forbidden until a justified, traceable update supersedes them.
- Keep uncertainty, source/observation IDs, simulated/observational provenance,
  run/dataset/map version and stale/duplicate-observation handling explicit.
  A local observation does not make a cell exact or universally safe.
- `UNKNOWN` as an inconclusive planner result remains valid. It is not the same
  concept as the initial knowledge category of a cell with an orbital prior.
- Planner proposes; MissionManager authorizes. Agent limits, applicable costs,
  return/reserves and stop/inspection policies still apply. Their illustrative
  assumptions must be visible; no approval flag substitutes for evidence.
- The numeric wire codes, producers and consumers are not silently redefined
  by this prose. Reconcile their semantics, tests and any needed versioning
  together before calling this behavior implemented or the contract frozen.

## Implementation allocation and acceptance

| Owner | Required follow-through | Evidence to close |
| --- | --- | --- |
| Daniel | Represent estimated/observed/NoData, uncertainty and confirmed obstacles without blanket rejection of a valid prior. Preserve coherent versioned batches and footprint updates. | Initial finite prior is estimated, not marked observed; NoData stays distinct; stale/duplicate inputs cannot undo a new obstacle. |
| Diego | Permit hypothetical FAST/SAFE search over estimated terrain under the explicit exploration policy. Include continuous-pose connectors and their costs where required. | Initial route before local observations; independent constraints/cost checks; a later contradiction changes the route or yields a reasoned failure. |
| David | Specify illustrative agent capabilities, applicable resource assumptions and the next-segment inspection/stop/return criteria with Jesus. | No false scientific approval; explicit behavior when the next segment cannot be justified or a contradiction arrives. |
| Jesus | Bind observation, invalidation, execution hold/stop acknowledgement and replanning through the real consumers. | One run preserves authority/current pose/resources; stale results cannot reactivate the invalidated route. |
| Jorge | Display estimated versus observed terrain, uncertainty and route revision reasons from the same data. | Backend-off replay shows the initial hypothesis, the observation and the resulting change without labelling estimates as verified truth. |

Regression acceptance must include: an initial hypothetical route using valid
unobserved prior cells; a local simulated contradiction and alternative route;
all alternatives blocked; NoData refusal; stale/duplicate observations; and
preserved return/reserves/current-pose checks. Test inputs stay explicitly
SIMULATED. Neither a passing search test nor animation closes execution evidence.

## Preserve the integration milestones

The previously identified **step 4** (one integrated run with continuous
execution, differentiated human/drone/rover roles, observation, stop/invalidation
and replan) and **step 5** (backend-off replay and an actual web-viewer video of
that same run) remain **open**. Their earlier checklist acceptance obligations
are not waived by module progress or this scope decision. Modules may advance
independently using conforming fixtures while dependencies are resolved.

Daniel's varied-scene trials and possible larger map are extensions, not a new
mandatory baseline or evidence of acceptance. Retain the reproducible 128 m
Jezero baseline and compare any extension with distinct dataset/run/configuration
IDs, hashes and declared dimensions/resolution. Check memory, batch latency,
search limits and viewer/replay load before increasing the integration target.
The informed random-detail hypothesis [H-DAN-01](../research_hypotheses.md)
remains P1, time permitting; generated detail stays hypothetical and seed-traced.

No generator, scene benchmark, exploration implementation or completed mission
is claimed by this decision record.
