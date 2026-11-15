# Mission success and remaining acceptance boundaries

Status: criteria defined; **execution binding and runtime acceptance pending**.
The [machine-readable criteria](../config/mission_success.experimental.json)
retain the four conjunctive success predicates already selected by David.
They bind the approved 120 s primary check-in and 1 m 3D model tolerance to
the [approved experimental scenario](../config/mission_jezero.experimental.yaml).
The [duration research/pilot](activity_duration_research.md) is a separate,
unapproved extension; no 300/600 s alternative is substituted at runtime.

1. Primary B work: receive public completion evidence and disjoint stationary
   service intervals meeting the approved duration. Presence, a planned cost
   or elapsed telemetry alone is insufficient. Inspection costing does not
   complete an optional inspection task or unlock sampling.
2. Return A: observe the primary human after B within 1 m in the core's 3D
   model distance. Do not infer physical localization accuracy from the DEM.
3. Traversal: close every executed ground step against the declared public
   map/model. No gaps, unchecked unsafe steps, future route segments or
   hypothetical prior routes count as verified executed distance.
4. Resources: retain a complete per-agent ledger for movement, service and
   wait exactly once, including elapsed time and separate reserves. Replanning
   uses actual remaining resources and unfinished service, never a reset.

All four need affirmative, context-bound evidence for the same run. Missing
evidence remains unknown; a correct block/abort/insufficient-budget rejection
is not mission success. Full three-role demonstration and replay acceptance
are additional integration deliverables, not inferred from this Boolean rule.

## Newly published scope and source audit

The accepted [D-EST-01 decision on main](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/2f50ae697b34fe82e575b386936d0d5e4d74db64/docs/decisions/2026-11-14-estimated-terrain-planning.md)
allows hypothetical planning over valid unobserved estimates while preserving
uncertainty and NoData distinctions. It supersedes blanket rejection based
only on `observed=false`. It does not certify the complete corridor. Daniel
and Diego own coordinated implementation; wire codes are not changed here.
The proposed next-segment rule is to hold human/rover execution before an
unjustified upcoming segment/footprint, request inspection, and require updated
public justification. Its exact producer/consumer binding needs Jesús review.
Drone altitude/footprint and validated flight are separately unresolved.

Reviewed source: main `2f50ae6`, planner `69101e9`. This branch did **not merge**
those producer/executor changes. The public executor follows the primary agent,
averages total route costs into movement rates and does not yet execute/charge
stationary service/wait. Stop acknowledgement alone does not prove completed
work or traversal. Discovery/work/traversal inputs are not wired to MissionNode.

Mission's current Python Boolean completion boundary also does not establish
120 s of service, optional duration, or remaining-service progress. This is a
known runtime gap, not a closed acceptance. Keep operational authorization
blocked until typed execution progress/results are agreed and consumed. No
new evidence input or producer was fabricated in this cut.

## Required executable acceptance before closure

- At B, reject completion at 0/119 s; at 120 s require public completed-work
  evidence and stationary interval coverage. Arrival alone never completes.
- Reject stale/foreign run, agent, task, route, map, model and future evidence.
- Stop/replan during service: preserve justified completed work, request only
  remaining time and do not charge the consumed prefix again.
- Execute separate movement/service/wait debits; keep each reserve, robot O2
  absent, elapsed mission horizon consistent and no regenerative credit.
- Contradiction: invalidate old route, observe HALTED/zero-speed/stable pose,
  replan from that actual pose/resources; reject late old candidates. Empty
  Path alone is not acknowledgement.
- Initial estimated proposal, contradiction/detour, all alternatives blocked,
  NoData refusal, resource rejection, duplicate evidence and partial recorder
  closure remain distinct cases. Keep MODEL_NOT_AGREED/MODEL_MISMATCH until
  the cost contract is evidenced; no new success claim comes from this packet.

CONT-DAV-01/02 are prepared for joint review, **not completed**. The local
tests of contract consistency and analytic costs do not close these future
execution acceptance cases. Original scenario-value approval is retained;
profile approval, cost agreement, execution and larger-map work stay separate.
