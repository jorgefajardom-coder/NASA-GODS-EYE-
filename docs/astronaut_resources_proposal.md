# Proposal — one resource model for the astronaut (after submission)

Status: **proposal for discussion**, requested by Jorge on 15 November 2026
(America/Bogota). It changes no code, ICD field, replay version, profile value or
reserve. It does not lift the D-DEL-03 freeze: the work below starts after
submission and each step needs its owner's review. Owners follow
[D-COST-02](decisions/2026-11-14-shared-scientific-cost-api.md): Diego planner and
search, David scientific API, profiles and reserves, Jesús context path, ROS wiring
and execution, Jorge recorded display, Daniel public map and uncertainty.

## Why

The astronaut's resources are computed twice, with different models:

| Where | Time | Energy (metabolic Wh) | Oxygen |
| --- | --- | --- | --- |
| Mission module, `mge_mission.models` | Walking speed slowed by slope | Walking plus climbing work from body + suit mass and grade; power **per activity** (`activity_power_w`: walk, inspect, sample, wait) | From energy, fixed L/Wh |
| Planner (exported profile) | Per distance | **Per metre**, one average | **Constant** rate (the maximum admitted climb/activity rate) |
| Viewer alert (`routeSufficiency.ts`) | Route totals spread evenly per metre | Same | Same |

So a route can pass one check and fail the other, the uphill return is
under-estimated (about 6 % at Jezero, see
[route_resource_sufficiency.md](route_resource_sufficiency.md) section 4) and
inspection or sampling costs the same as walking in the planner.

## The unification (item 1), already decided by D-COST-02

The planner calls `estimate_segment` and `estimate_activity` for every directed
edge, service, wait and the return, instead of its own per-metre projection. No
formula is copied; one function is the source of truth. Steps:

1. **Diego:** replace the planner's cost backend with the shared API; keep the
   bounded search and verify admissible bounds and cost dominance.
2. **Jesús:** carry activity, remaining service, waiting and model/profile identity
   across the request boundary (additive context path; legacy `PlanRoute` kept
   under its documented scope).
3. **David:** confirm the profiles in use; the existing numerical comparison
   (one agreement, six disagreements) becomes the regression to close.
4. **Tests:** planner backend and independent full-itinerary audit agree on every
   kind, grade, activity, connector, return and budget edge.

## What follows from it

| Item | What changes | Owner | Depends on |
| --- | --- | --- | --- |
| 2. Cost per segment | `RouteDecision` gains an **optional, additive** per-segment cost list (time, Wh, O₂ for each outbound and return segment), with an ICD/schema version step and producers, consumers and tests updated together. The viewer's turn-back point then uses real per-segment costs instead of an even spread | Diego (producer), Jesús (ICD/recorder), Jorge (viewer) | 1 |
| 4. Oxygen by activity and load | Oxygen follows the activity's metabolic power (already in `activity_power_w`) and the carried load (a new `payload_kg` next to `suit_mass_kg` in the human profile). Values need sources (Apollo and analog EVA metabolic data) | David | 1 |
| 5. Reserve by contingency | Replace the flat 20 % (JZ-P06, experimental) by a reserve that covers a stated contingency, for example the walk back within one hour from the farthest point at the suit's contingency rate (NASA's Artemis tenet). A decision record, not a code default | David | 4 |
| 8. Radiation as a resource | **Done in the viewer** (PR #37): each zone's dose rate over time, shown against NASA's 600 mSv career limit. A per-EVA dose budget would be David's decision | Jorge (done), David (budget) | — |
| 9. Real budgets in the replay | The recorder writes the mission's budgets and reserves (already in `SetMissionGoal`) into the replay, an additive field with a replay-version step; the viewer stops using the first sample as 100 % | Jesús (recorder), Jorge (viewer) | — |
| 10. Uncertainty on costs | `CostEstimate` carries a ± range from the profile's parameter ranges and the map's sigma; the reserve and the viewer alert can then say how confident they are | David (model), Daniel (sigma), Jorge (display) | 1 |

Item 3 (CO₂ removal, cooling water, suit battery) is outside this list; the viewer
already shows the exhaled CO₂ as an estimate from oxygen used. Items 6 (rover as a
safe haven) and 7 (two astronauts) are larger extensions for the
[science extension tree](science_extension_tree.md).

## Order

1, then 2 and 9 (independent of each other), then 4, 5 and 10. Each step is a
reviewed PR with its own tests; none changes approved values without David's
record, and none is presented as a validated mission.
