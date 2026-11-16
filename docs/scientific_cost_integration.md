# Operational scientific route costs

Candidate over main `d13a4b3f1035260cebf9f065472c56cc53158401`.
This implements D-COST-02 in the real planner and mission service consumers.
Integration and scientific owners review this cut through its PR. Coefficient
approval and evidence of executed scientific work retain their own gates.

## Calculation and search

The default scientific PlanningNode calls
`mge_planning.resource_costs.scientific_plan_route`. The actual FAST/SAFE search
prices admitted directed edges and continuous-start connectors through
`estimate_segment`, and the explicit stationary goal schedule through
`estimate_activity`. Return is priced in its actual direction. Resource and
reserve comparisons grant no numerical credit; comparison tolerances remain
`rel=1e-5`, `abs=1e-3` for independent reconciliation.

The heuristic uses a model-specific admissible horizontal time bound. Geometry
caches distinguish cost backend identities. Before a FEASIBLE candidate leaves
the scientific facade, an independent sum of its returned paths and activities
must reproduce time, energy, applicable oxygen and remaining resources.
Human energy is metabolic Wh; robot energy is electrical Wh; robot O2 stays
absent. Ground-grid drone costs retain their existing flight-model limitations.

The low-level `core.plan_route` legacy cost option remains for historical
reproduction and explicitly selected compatibility callers. Production service
scientific mode does not silently fall back to that option.

## Immutable typed context

The existing six messages and two service definitions retain their bytes. The
additive `RegisterPlanningContext.srv` carries the request context under schema
`mge-planning-cost-context-1.0.0` before the unchanged PlanRoute request.

The registration key is `(run_id, request_id, agent_id, map_version)`.
Its content binds:

- A fingerprint of every PlanRoute request field, including actual XYZ, goal,
  return, mode, all remaining resources and separate reserves.
- Model ID, exact scientific-model source hash and profile-registry hash.
- Ordered, individually identified activity kinds and remaining durations.
  The current schedule is stationary at the goal; it can distinguish inspection,
  sampling and waiting, including different costs at equal duration.

PlanRoute float32 resource/duration fields are fingerprinted at their actual wire
precision. Geometry_msgs/Point XYZ remains float64. Nonhuman O2 NaN becomes null
in the canonical digest; arbitrary nonfinite values fail. The schedule total
must equal the actual encoded service duration. Completed work belongs to the
spent ledger and is excluded from the remaining schedule.

Registration is immutable and bounded: an identical retry receives the same
digest, a conflicting key is rejected, and capacity exhaustion fails closed.
The planner checks the current request and model/profile identities again when
resolving the context. MissionNode validates the registration acknowledgement
before dispatching PlanRoute and preserves its existing current-map, pose,
resource, timeout and response checks. A request ID carries identity only.

The registration service is `/mge/planner/register_context`; the planning service
remains `/mge/planner/plan_route`. The registration digest binds the existing
request identity; it does not grant profile approval or route authorization.

## Migration and version

The interface package is `2.0.0`, with candidate contract baseline
`2.0.0-rc.1`. Although existing IDL fields are unchanged, the default scientific
server requires registered context, which changes the prerequisites for old
callers. This is a major semantic migration, not a release or a contract freeze.
Replay, gateway and public-raster JSON schemas remain unchanged.

Configure the same full science profile registry for both real nodes.
Scientific geometry is derived from that registry; projected legacy cost rates
are not a substitute. Proposed profiles require the existing explicit
illustrative opt-in. Geometry, uncertainty limits and reserves are not relaxed.
Mission authority keeps `model_agreement_confirmed=False` by default, and
coefficient/mission acceptance is not inferred from successful comparison tests.

Historical MOCK launch/test consumers may explicitly select
`allow_legacy_cost_model=true`. That mode is labelled compatibility behavior and
does not establish scientific agreement. Real mission launches select the
scientific consumer and its registered-context producer together.

## Verification and retained history

The default conformance CLI now evaluates the same scientific facade used by the
ROS service. `--backend legacy` deliberately reproduces the old comparison.
The historical one-agreement/six-disagreement artifacts remain unchanged.
New comparisons must use a new output directory and exact source manifest.

```sh
python scripts/check_planner_conformance.py --planner-ref SOURCE_SHA --backend scientific --run-id NEW_RUN --output-dir NEW_OUTPUT
python scripts/check_planner_conformance.py --planner-ref SOURCE_SHA --backend legacy --run-id NEW_LEGACY_RUN --output-dir NEW_LEGACY_OUTPUT
```

The actual-search regression includes a slope itinerary reported by legacy as
1.338953692 Wh whose independent scientific cost is 1.390768345 Wh. Under a
1.36 Wh usable cap, scientific A* chooses a 1.344609791 Wh flat detour. This
is an 8 m one-way grid test; its geometry is distinct from the historical
independent-oracle example, and its totals are recorded separately.

Focused tests cover directional return, mixed service/wait schedules, partial
remaining work, connectors, strict boundary reserves, cache separation, robots'
oxygen, unresolved searches, conflicting contexts and changed request budgets.
The real ROS test covers registration followed by PlanRoute, equal-duration
inspection versus sampling, waiting charged once and the normal MissionNode
producer. The mission-authority test retains its model-approval block.

Exact validation commands, versions, hashes and outcomes accompany the final
handoff and evidence. These are software/model-consistency tests with declared
synthetic maps; they do not constitute physical mission execution or new Mars
observations.

The [executed verification record](../evidence/scientific-cost-integration-20261115/README.md)
pins implementation `3830b8b0fb2d6269ac3e73e8b8fd8de71c876334`.
The scientific comparison is 7/7, the deliberate legacy control remains 1/7,
and the same seven cases pass through actual ROS services. Regression results:
1,346 Python tests passed on Windows, 871 contract/mission/integration tests
passed on Ubuntu/Jazzy, and 412 frontend tests plus build passed. Skips, warnings,
environment setup and original output hashes are recorded separately.
