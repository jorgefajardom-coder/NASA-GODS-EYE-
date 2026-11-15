# D-COST-02 — Reuse the existing scientific cost API

Authority: project owner, explicit reply in the reconciliation chat on
14 November 2026 (America/Bogota): reuse the existing scientific API as the
planner's single cost calculation. Status: **accepted implementation direction**;
profile/parameter approval, transport review and operational acceptance remain
separate. This does not change the mission's scientific target or approved values.

Reuse `mge_mission.models.estimate_segment` and `estimate_activity` rather than
copying their formulas into the planner or adjusting the old projection to match
a few examples. Preserve the existing bounded search, directed geometry and
continuous connector; cost exact directed edges, service/wait activities and
return once through the shared API. Verify admissible search bounds and cost
dominance after changing the backend. Human metabolic Wh/O2 and robot electrical
Wh retain their declared meanings.

Activity, remaining service, waiting and model/profile/configuration identity
must survive the request boundary. The legacy `PlanRoute.srv` cannot distinguish
equal-duration inspection and sampling, so it must not silently imply that it
does. Reconcile an explicit additive context path with producers, consumers,
tests and versioning together; retain legacy compatibility under its documented
scope. Do not encode semantics in IDs or use an approval Boolean as evidence.

Numerical tests compare the actual planner backend and independent full-itinerary
audit across all kinds, grades, activities, connectors, return and budget edges.
Retain the old one-agreement/six-disagreement result as historical evidence of
the old projection. New numerical identity establishes software behavior, not
approval of coefficients or execution of work. Existing model/profile/mission
authorization gates remain closed until their real review evidence exists.

Owners: Diego planner/search, David scientific API/profiles, Jesus context/ROS
wiring and execution, Jorge recorded display, Daniel public map/uncertainty.
The [cost and execution gap record](../audit_cost_execution_gaps.md) describes
the remaining context, interval and real-role consumers. No new approval or
completed mission is asserted by this decision.
