# Local exact-cost experiment and proposed verification levels

Owner request, 15 November 2026: reconcile costs locally, investigate missing
values if necessary, run an interesting complete analytical experiment and
record a video for review before publication. The owner expressly accepted
SIMULATED scope and increased large-map search limits. No publication approval
has been given. This document proposes review criteria; it does not redefine
ROS enums, the four mission-success predicates or profile approvals.

## What is reconciled

Published main `64985e7b4b69ac9683661db4842885d5a8293695` supplies the real
`ScientificCosts` consumer and the unchanged planner search/geometry. Mission's
new local `scientific_plan` composes that consumer through the published
geometry-cache hook. It replaces admitted directed edge/connector cost tuples,
retains geometry and uses an admissible horizontal-time heuristic. At a fixed
goal, explicit ordered remaining activities are represented by exact total
duration and equivalent service rates for that one immutable request. This is
an in-process composition, not a replacement search or a ROS context channel.

The scientific source is still the single segment/activity API selected by
D-COST-02. Every returned FEASIBLE itinerary is checked independently with that
API and strict resource margins. The context binds run/request/agent/map,
source/model/profile/scenario hashes, directed itinerary, activity identities,
remaining resources and reserves. Identical retries are no-ops; changed content
under one key and stale identities are rejected. Numeric tolerance stays
relative1e-5 / absolute1e-3, with no reserve slack. Robot oxygen remains absent.

Thus the local fixed-schedule numerical disagreement is resolved for this
consumer configuration. **Production agreement remains pending:** Diego and
Jesus must review/adopt the cost composition and immutable activity/context
transport with real producer/consumer tests. Existing ROS PlanRoute cannot
identify inspect versus sample from duration alone. No production approval flag,
shared message, owner implementation or official profile was changed.

## Actual experiment and limitations

The definitive packet is
`evidence/mission-cost-experiment-20261115-local-v2`. V1 remains an earlier
diagnostic. V2 adds the initial full-return budget check after planning wait,
explicit public-map admission checks for every completed simulated step, and
hashes of the actual private-world subprocess code. It uses the same public
Bunsen512 query window and endpoint draw0 retained from the earlier audit.
Exact geological registration and the canonical regional package remain pending.

This is a single-human **analytical workflow**, not MissionManager/ROS execution.
It integrates only reached points returned by a separate private hypothetical
world process, charges directed movement/service/wait once and records typed
cost/traversal inputs with the existing EvidenceRecorder. Its journal recovers
under the same run ID. No physical/ROS success predicates are invented, and the
legacy benchmark export is not forced with a fictitious ROS termination state.

The observation stop is programmed from the initial corridor. A hypothetical
obstacle is deliberately placed ahead of that point; it is not a NASA feature
or a demonstration of autonomous hazard detection. The local ideal sensor
reveals only a12 m footprint after a120 s inspection. It assumes noiseless
height with declared sigma0.25 m; that is not measured sensor accuracy. The
public prior remains estimated, with native CTX20 m and computational4 m
distinct. Sigma3 and the grade-derived endpoint-height bound are explicit local
research geometry, separate from the unchanged proposed scientific profile.

The primary service at B is a120 s visual/check-in workload. It does not produce
a measured scientific work result. A600 s sampling alternative is evaluated
but not assigned: rover-inspection evidence is absent in this one-agent pilot
and the extra cost with return violates resources. No rover/drone role is
executed or inferred. Planning latency is charged as active waiting with a
declared analytical1:1 wall-time assumption; this is not a calibrated real-time
robot/suit model. The successful bounded trace does not prove a general
return-priority controller for arbitrary interruptions or depleted resources.

Large-map controls retain fixed Bunsen1024 endpoints and budgets. Both2 s /
200,000-label and20 s /1,000,000-label variants retain UNKNOWN when bounded
search cannot decide. They are independent diagnostics, not extra phases or
resource resets in the EVA. Wall latencies are software diagnostics rather
than controlled hardware performance claims.

## Proposed levels for David's review

**Level S — independently checked analytical simulation.** This label is viable
if David accepts the declared single-agent scope and assumptions, and a second
reader reproduces the source/configuration/map hashes, exact numeric contexts,
observation causality, reached-step receipts, disjoint cost intervals, stationary
B coverage, return pose and separate reserves. Include negative tests for
changed duplicates, stale identities, NoData, invalid resources and insufficient
reserves. Verification establishes consistency under the model; the provenance
must remain SIMULATED. It cannot validate actual sensor precision, geology,
physical passage, EVA safety, scientific discoveries or battery availability.
Current status: software/analytical checks recorded; owner review pending.

**Level R — verified integrated simulated mission.** Keep the existing four
conjunctive success predicates and their evidence bindings:

1. B: public work-result receipt plus disjoint stationary intervals covering
   the approved service duration, bound to run/agent/task/route/map/model/context.
   Reject0/119 s, wrong location, future/foreign/stale data and overlaps; preserve
   completed service through interruption. Elapsed time alone is insufficient.
2. Return: actual post-B primary-agent telemetry within the approved1 m3D model
   tolerance, with clock and localization provenance. DEM spacing is not
   localization accuracy.
3. Traversal: every actually executed ground step has public map/profile/version
   justification, current observation/estimated-cell policy and independent
   step-count/distance closure. A contradiction invalidates the route; execution
   acknowledges stop before replanning from reached XYZ. No future route segment
   or private evaluator reference is evidence of traversal.
4. Resources: complete per-agent movement/service/wait ledger, remaining service
   and current resources, no overlap/duplicate debit/reset/regeneration, and
   independently directed return with separate reserves. Recheck before spending
   inspection/planning delays as well as before following a replacement route.

Before Level R, require reviewed profiles and regional allocations, registered
canonical public terrain, agreed production cost/context transport, a conforming
executor, work/traversal producers and same-run scientific/gateway records.
Run actual Ubuntu24.04/Jazzy exchange, close the exact package and replay it with
backends off; record video from that same run. Three executed roles are an
additional acceptance milestone. Current status: pending owners, not closed by S.

**Physical/LIVE acceptance** additionally needs appropriate vehicle/suit/sensor,
localization and terrain validation. Neither S nor R grants it. These labels
are proposed review language, not new values in the canonical ICD.

## Review/publication

The80 s video is a2D visualization of this recorded analytical timeline, with
variable time scale and permanent `AI-generated | SIMULATED | NOT LIVE` mark.
It contains no agency branding, audio, fabricated observation outside its
footprint or motion not present in the simulated receipts. Source/data/video
hashes and actual commands stay with the packet. Both AI registers identify
generated code, model diagnostics and video. All work remains local until the
owner gives the requested final publication approval.

For delivery, JES-07/AC-10 still requires organizer notification and explicit
endorsement. Jesus coordinates; David is backup, with the agreed review margin.
This local research result is not submission readiness or permission to send
an external message.
