# Cost context and execution evidence reconciliation proposal

The [operational scientific-cost candidate](scientific_cost_integration.md)
implements the shared search backend and typed request-context producer/consumer
described here. It retains historical comparison artifacts and separate profile,
execution and owner-review gates. The older proposal and its published-source
diagnosis below identify their original revisions.

Status: **proposal for David, Diego and Jesus review; no new active interface,
version freeze, profile approval or runtime authorization**. Audited published
baseline: `main@6bcf208868e37b7e15e9189fac11de96e7414eff`.

The same directed itinerary and activity schedule must produce compatible
costs in planning, mission audit and execution accounting. The current interfaces
lose activity context and the current implementations use different equations.
This cut records those boundaries and a concrete consumer agreement to review.
The approved experimental A/B configuration, durations, allocations, source
profiles and success predicates retain their existing approval states.

## Existing implementation and fresh comparison

Reuse the existing [experimental cost contract](../config/cost_agreement.experimental.json),
[owner handoff](cost_agreement_handoff.md), [success contract](mission_success_contract.md),
scientific APIs, vector exporter and evidence recorder. They are already in main
through the mission contribution at `c3ec4c1`. The audited planner branch
`69101e9` is also an ancestor of main. Their earlier comparison artifacts remain
historical records.

The [new comparison](../evidence/audit-reconciliation-20261115/cost/conformance.json)
materializes the exact planner source from published main through the existing
`scripts/check_planner_conformance.py` snapshot mechanism. Its newly executed
seven cases yielded **one agreement, six disagreements, seven feasible
candidates, zero errors**, with authorization **BLOCKED**. The report carries
the full planner revision, source manifest/content hashes, scientific source and
profile hashes, command, run ID and time. See its
[reproduction record](../evidence/audit-reconciliation-20261115/cost/README.md).
These are controlled model comparisons; no mission or executed work occurred.

| Boundary | Current code | Remaining consequence |
|---|---|---|
| Directed movement | `mge_mission.models.estimate_segment` and planner `_motion_costs` use different movement/energy/O2 equations. | A profile projection cannot establish model agreement. |
| Activity selection | Internal mission `PlanRequest.service_activity` accompanies its service duration. Canonical `PlanRoute.srv` carries only `service_time_s`. | Equal-duration inspection and sampling are indistinguishable at the service boundary. |
| Waiting | Scientific `estimate_activity` distinguishes activities, including drone ground wait/hover. | A single service power/rate cannot encode an arbitrary schedule. |
| Remaining work | Mission `_continuation_reason` audits the full declared service until explicit completion. | Partial service progress needs an evidence-backed remaining duration. |
| Completion | `MissionEvidence` carries Boolean facts; `TaskEvidence` carries identifiers and a timestamp. | These primitive APIs do not establish duration, interval coverage or scientific completion. |
| Execution | The MOCK executor follows the primary route and spreads total estimates over movement. | Service/wait and three-role cost accounting remain separate integration work. |
| Recording | Scientific `EvidenceRecorder` supports costs, traversal and tasks; the gateway recorder stores state/events/maps/rasters. | Bind both records to the same authorized run/context before making audit claims. |

## Accepted backend direction and proposed context

The owner selected [D-COST-02](decisions/2026-11-14-shared-scientific-cost-api.md):
reuse the existing scientific segment/activity API as the planner's cost backend.
This supersedes choosing between two competing formulations for implementation;
it does not approve parameters, freeze the context transport or establish mission
execution. The comparison above records the old projection on main6bcf208.

## Proposed immutable planning context

The proposed lookup key is exactly `(run_id, request_id, agent_id, map_version)`.
An identical retry resolves the identical context and answer. Reuse of a key
with different content is an explicit conflict. A changed map, task schedule,
profile or remaining-resource snapshot creates a new request/context; it never
rewrites the earlier one. Hashes identify content and do not grant approval.

| Context component | Proposed required content and interpretation |
|---|---|
| Identity | Lookup key, context identifier, content SHA-256 and proposed context-schema identifier. |
| Public geometry | Dataset ID, `map` ENU frame, public vertical datum, coherent map batch stamp and geometry fingerprint. Pose XYZ and uncertainty retain their recorded meaning. |
| Model | Model ID, executable cost-kernel/source revision and SHA-256; comparison-policy identifier. |
| Configuration | Exact profile-registry SHA-256, selected agent profile ID, scenario/configuration SHA-256 and applicable owner review references. |
| Execution snapshot | Current pose, state revision/time, current remaining time/Wh/applicable O2 and unchanged separate reserves. |
| Phase and task | Task ID, activity kind, mission phase and explicit remaining service duration. |
| Stationary schedule | Ordered service/wait components with activity kind, duration and phase/location binding; distinguish ground wait and hover. Record already accepted completed intervals by evidence ID. |
| Movement binding | Start/goal/return policy in the request; the returned candidate supplies the exact directed outbound/return polyline, including any permitted connector. Its candidate digest binds that path to this context. |

Durations and costs use the existing SI/Wh/O2 conventions. Nonhuman O2 remains
absent internally, ROS NaN and JSON null. Finite comparison tolerances remain
`rel=1e-5`, `abs=1e-3`; a negative cost-plus-reserve margin still fails. An
activity schedule counts each component once, including separately directed
return. Accepted completed work and travel are excluded from remaining costs.

The planner must resolve and validate the context before search. A missing,
conflicting, stale or unsupported context yields an explicit unavailable/error
result with no executable route. Mission independently checks the response's
context, current pose/resources, path and costs before authorization. Executor
orders and recorded evidence reference the same authorized candidate/context.

## Interface decision required before implementation

Existing `PlanRoute.srv` fields preserve current callers but cannot express
inspection versus sampling at an equal duration, a waiting schedule, remaining
service evidence or model/configuration identity. A filename or approval Boolean
does not resolve that ambiguity. Request-ID text must not become an implicit
activity or model channel.

Review an **additive typed context interface keyed by the existing request**,
with explicit delivery/readiness and immutable-content acknowledgement, as the
initial compatibility option. It would leave existing ROS fields intact while
the experimental consumer waits for the corresponding context. The contract
review must specify QoS, size bounds, ordering, expiry, conflict handling and
how the reply/candidate confirms which context it used. The current map-batch
protocol is a useful delivery pattern, not a substitute for this separate key.

Jesus and the owners may instead choose a new versioned planning service with
an explicit context reference if it gives a simpler atomic request/reply
boundary. Existing `PlanRoute` remains available under its documented legacy
scope until producers and consumers migrate. Do not append unreviewed fields
to the canonical service, overload an existing unit/enum or infer capabilities
from a successful legacy call.

The interface name, exact transport, failure vocabulary and context/cost schema
version remain **pending owner review**. No new topic, message, service or active
schema is introduced by this document. Following the choice, change interface,
ICD, providers, adapters, consumers, tests and versions together. Versioning and
rollout approval must precede enabling the experimental path in integrated runs.

## Proposed execution progress and evidence binding

Use an append-only interval record with evidence ID, previous/parent reference,
run/agent/task/route/map/context identity, clock start/end, activity/phase and
relevant start/end pose/resources. Movement records identify the executed
polyline portion and public map/model justification; stationary service records
identify work and valid stationary coverage. Completion additionally needs the
agreed public work-result evidence. A time span alone is insufficient.

The receiver must validate finite nonnegative durations, an authoritative clock
upper bound, monotonically ordered per-agent progress, non-overlap, current
assignment and matching context. An exact duplicate has no second debit/effect;
a reused evidence ID with changed content is rejected. Adjacent disjoint
intervals may accumulate; completed prefixes survive interruption only with
their valid recorded context. Required work cannot increase or disappear through
a retry or an unrelated phase change.

At contradiction, invalidate the old command immediately, obtain a fresh
HALTED/zero-speed/stable-pose acknowledgement, close executed progress, then
request remaining work from actual XYZ/resources. Late old-context responses or
future progress cannot resume motion. Preserve the validated continuous connector
and its explicit gate. D-EST-01 permits a hypothetical route over valid estimates;
traversal evidence still covers the steps actually executed under the reviewed
inspection/stop policy.

Mission derives the four existing success facts only after validated work,
return, traversal closure and resource-ledger closure. The current Boolean APIs
remain primitives until that stronger binding is implemented and reviewed. A
negative scenario or correct block/return does not become mission success.

## Producers and consumers that must change together

| Owner / component | Producer obligation | Consumer/acceptance obligation |
|---|---|---|
| David / mission models, manager and types | Canonical cost/activity semantics, immutable schedule, interval accumulation and derived completion. | Independently audit returned itinerary and actual debit; retain model/profile/success gates. |
| Diego / planner core, node and replan policy | Resolve context; use the reviewed cost backend for edges, connector, activities and return; preserve bounded search and geometry checks. | Recheck admissible heuristics/dominance; reproduce cost vectors and current-resource/partial-service cases. |
| Jesus / interfaces, MissionNode and executor | Publish/acknowledge context, typed orders/progress/work results, stop feedback and role-specific execution. | Reject stale/missing/mixed inputs; charge movement/service/wait once; preserve mission's sole authority. |
| Daniel / mapping and observations | Coherent estimated/observed/NoData batches and traceable executed-sensor footprints. | Public geometry and map/model references used by route/traversal closure; no evaluator data in the context. |
| Jesus / gateway recorder and scientific EvidenceRecorder | Persist the context, task discovery, accepted interval/cost/traversal records and final closure under the same run. | Link existing journal/export through an agreed optional audit attachment; validate hashes, counts, event closure and used map versions. |
| Jorge / replay consumer | Display the recorded phases, costs, progress, reasons and model/configuration provenance supplied by the package. | Read the exact package with backend off; preserve IDs and source labels; no independent cost calculation or fixture completion. |

Keep the existing `EvidenceRecorder` and its hash-chained journal as the
scientific audit implementation. Bind it to MissionNode's accepted inputs and
link its export to the replay package through the reviewed optional attachment.
No second recorder, planner implementation or duplicate mission authority is
needed. Public replay must exclude evaluator reference data and hidden tasks.

## Closure tests and integration sequence

1. **Model agreement:** execute the existing vectors through the real planner
   backend and independent mission audit: flat/up/down, zero/invalid ground
   vertical, drone vertical, connector, all activities, ground wait/hover,
   directed return, boundary resources, partial service and sensitivities.
   Retain exact inputs/source/configuration hashes, disagreements and limits.
2. **Context consumer:** equal-duration inspect/sample requests resolve different
   explicit contexts; an absent/stale/conflicting context, mismatched model or
   altered profile hash cannot publish a route. Identical retries are idempotent.
3. **Work evidence:** reject completion at 0/119 s; at 120 s require valid
   disjoint stationary intervals and work-result evidence. Reject overlapping,
   duplicate-changed, future, foreign and wrong-task/route/map/model progress.
4. **Partial recovery:** interrupt movement and service, acknowledge stop,
   preserve XYZ and accepted completed work, and charge only the connector and
   remaining itinerary/work. Recheck reserves with current availability; refuse
   stale authorization and below-reserve execution.
5. **Opportunistic science:** a public discovery drives mission assignment;
   execute one affordable optional inspection and reject another with an
   explicit budget reason. Test sampling-before-primary/inspection rejection,
   capability limits, map invalidation and return priority through actual node
   consumers rather than prewritten demo events.
6. **Same-run closure:** execute the three declared roles; close traversal,
   per-agent cost intervals and journal; validate the exact recorder package;
   load it in the production viewer with ROS/gateway stopped. Match all IDs,
   resource changes, phases, events and map versions, including honest blocked
   cases and the final recorded state.

Implement in that dependency order, with model/context/evidence fixtures
prepared in parallel by their owners. Existing Python, web and ROS CI suites
remain required alongside these new actual-consumer cases. The current recovery
replay proves a narrower MOCK stop/replan/return workflow; this proposal does not
promote it to a complete scientific mission. Profile/cost/integration approval
requires recorded David/Diego/Jesus review after the relevant evidence exists.
