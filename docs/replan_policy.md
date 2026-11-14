# F03.4: ROS-independent event policy

Implementation: [replan.py](../src/mge_planning/mge_planning/replan.py).
This is a synchronous, serially called policy for one run/agent/mission. It
produces recommendations and candidate plans, never publishes/authorizes a route
and never commands a physical stop. No ROS messages/services change. This code is
not yet connected to the ROS node, MissionManager or supervisor.

## Inputs and ownership

- `ReplanConfig`: explicit corridor enter/exit distances, minimum search interval,
  immediate horizon in metres and validation/event-history bounds. No physical
  braking distance, physiological rate or scientifically approved default is claimed.
- `ReplanState.mission`: the original immutable PlanRequest (goal, explicit base,
  reserves, service requirement, run/agent). Changing the mission template requires
  a new policy instance. A TASK event requests reevaluation of that mission; it does
  not assign a task, select its value or insert B before the primary goal.
- `active_request` and `active_route`: the request/result pair installed by
  MissionManager. A returned candidate does not automatically replace these.
- `phase`: OUTBOUND, SERVICE or RETURN; `next_waypoint` is the next index in the
  current leg. Mission supplies progress, not a nearest-waypoint guess. Index starts
  at 1, including a stationary one-point leg; it cannot go backwards within a leg.
  Phase cannot go backwards even after route replacement. New route IDs reset the
  waypoint cursor, not the phase or service progress. Retired routes cannot reactivate.
- `pose`: current finite 3-D ENU pose; `remaining`: current authoritative availability,
  with reserves still included. The policy NEVER subtracts historical consumption.
  `service_remaining_s` is explicit and nonincreasing. It must equal the original
  service_time_s throughout OUTBOUND, including arrival until mission enters SERVICE;
  only SERVICE at the goal permits a decrease. RETURN requires zero (completed or
  abandoned service). A premature OUTBOUND debit returns UNKNOWN with
  OUTBOUND_SERVICE_MISMATCH, invalidate_active=True and no planner request. Mission must
  subtract actual movement/elapsed service exactly once before calling this policy.
- `ReplanEvent`: unique event_id, run_id, map_version, kind (MAP, POSE, TASK,
  RESOURCES, TICK, DANGER), optional task_id. `now_s` is an injected monotonic clock
  in seconds in this run, used only for hysteresis, never for resource debiting.
- `terrain` and `profile`: copied public belief snapshot and explicit motion model.
  Scope mismatch, version rollback, same-version raster mutation and changed grid
  geometry fail closed. An old active route may be checked against a newer map;
  a newly adopted route must match the current version. KEEP does not rewrite its ID
  or map version: mission must handle revalidation/authorization of an unaffected path.

## Validation, decisions and hysteresis

Every call checks the remaining current leg, the current pose-to-next-waypoint
segment, and the future return leg when outbound. Already travelled outbound
segments are excluded; a segment behind the agent is still relevant if needed for
the future return. SERVICE checks the stationary pose, remaining activity and
return. All pending segments are checked, irrespective of event kind.

The footprint bound uses nearest forbidden/unknown cell centres, minus the cell
circumradius, agent radius, localization allowance and half the validation probe
spacing. The 1-Lipschitz distance bound covers BETWEEN probes too. The map-boundary
minimum is exact. Zero obstacle margin is rejected even for point agents. All
crossed cells are enumerated by grid-line intersections (including arbitrarily
short corner crossings), so directed slope/step restrictions cannot be skipped by
uniform sampling. Existing geometry and directed cost helpers are reused; A* is
not duplicated. Changed belief heights at stored waypoints invalidate the old
polyline. No subcell terrain or dynamics is reconstructed.

The pending route is costed with remaining service, return and reserves to detect
resource loss even without a map event. Corridor deviation uses distance from the
pose to the current cursor's segment, not to an unrelated future segment. Enter
and exit thresholds implement spatial hysteresis; soft task/deviation searches
respect min_interval_s. Deferred causes survive until a TICK with fresh state.
Each distinct task event can reevaluate the mission; duplicates do not repeat work.

| Action | Meaning |
| --- | --- |
| KEEP | No search needed, duplicate, or soft reevaluation deferred; inspect reason_code. Does not authorize execution. |
| REPLAN | New candidate requested for task/deviation or an affected distant segment. Inspect candidate status and invalidate_active. |
| STOP_REQUIRED | Immediate segment hazard, explicit DANGER, infeasible remaining mission, or invalidated route awaiting replacement. Advisory to mission/supervisor. |
| UNKNOWN | Context, data, search proof or validation is unresolved; never treat as permission to continue. |

`invalidate_active=True` means mission must inhibit reuse of that active route,
including when action=UNKNOWN. Invalidation is latched until mission supplies a
different authorized route. A feasible candidate NEVER clears the latch; stopping
and restarting remain supervisor responsibilities. The immediate horizon classifies
any bad segment whose start lies within the threshold as urgent (including the
entire next segment); it is deliberately conservative, not a stopping-distance model.
All route invalidations bypass search cooldown. DANGER returns STOP_REQUIRED without
search. Safety validation precedes deduplication: stale/duplicate events cannot hide
new hazards. Identical affected inputs do not repeatedly launch A*. The bounded
event cache deduplicates within its retention window, not across process restarts.

An event/map version mismatch always invalidates the active route, even if its
geometry remains admissible: UNKNOWN/EVENT_MAP_MISMATCH carries
invalidate_active=True and no request/candidate. An immediate hazard retains
STOP_REQUIRED priority. A subsequent matching event or TICK does not clear the
latch; mission must supply a different authorized route on the current version.

`reason_code` records the decision/result cause; `trigger_reason` preserves the
original search trigger if planning fails. `request` and `candidate` expose exactly
what was computed. A source-z mismatch caused by the core's legacy centred-pose
behavior or a candidate failing policy revalidation returns UNKNOWN without an
executable candidate. Search/validation bounds also fail closed.

## Phase-aware requests, unchanged ROS wire

- OUTBOUND: start=current pose, primary goal unchanged, current map version and
  remaining budget; service_time_s=service_remaining_s (must equal the full original
  service requirement in this phase); retain required return.
- SERVICE: pose must be at the primary goal. Only remaining service is charged;
  the zero-distance goal transition adds no repeated outbound travel. If service
  remaining is zero, produce a RETURN candidate directly.
- RETURN: goal=base, require_return=False, service_time_s=0. This solves the core
  request's lack of a phase field safely as a ONE-leg route. Its path is in
  `candidate.outbound_path`, its `return_path` is empty, and `candidate_phase=RETURN`.
  After adoption, the policy selects that outbound path as the current return leg.
  Mission/Jesus must preserve that phase metadata outside the unchanged ROS message;
  blindly treating this result as a new outbound mission would be incorrect.

Candidate totals include only future connector, movement, remaining service and
return. Consumed resources and completed service are never charged again.

### Automatic contingency from OUTBOUND

This is distinct from planning when the incoming phase is already RETURN.
After a primary-mission result of NO_PATH or INSUFFICIENT_BUDGET, evaluate() now
automatically requests ONE direct return to base from the same current pose/map
and authoritative remaining budget. Service is set to zero; no primary estimate
or historical consumption is debited. A feasible goal detour never invokes this
fallback. Primary UNKNOWN/STALE_MAP/ERROR does not establish infeasibility and does
not trigger fallback; ordinary fail-closed handling applies instead.

The selected request/candidate describe the return attempt; primary_request and
primary_candidate retain the unsuccessful original attempt. A feasible return
has reason_code=CONTINGENCY_RETURN and candidate_phase=RETURN, with invalidation
still latched. Action is REPLAN unless an immediate danger requires STOP_REQUIRED.
An infeasible return yields STOP_REQUIRED; an unresolved return yields UNKNOWN,
with no executable route. Both attempts use existing plan_route() and independently
apply its SearchLimits (at most two searches, not one shared wall-clock deadline).
Candidate pose/segment revalidation also applies to the fallback.

MissionManager must explicitly authorize the candidate, switch to RETURN and set
service_remaining_s=0 because the original service is abandoned. No internal
phase switch or physical movement occurs automatically. RETURN never recursively
tries another contingency. Tests cover human/rover goal detour, base-only access,
no escape, uncertain base access and separate contingency budget feasibility.

## Validation and pending integration

Latest service/map audit on 14 November 2026 (Python 3.12.3): 74 policy cases plus
9 D-07 cases passed (83 passed, 2.85 s). Full suite: 267 passed, 2 ROS modules
skipped, 0 failures (4.53 s), with the existing Starlette/httpx warning. Repository
checks and git diff --check passed. The 18 added cases cover human/rover premature
service (including first observed state), valid SERVICE progress, and stale/future
event versions with latched invalidation until explicit adoption. JUnit outputs:
tmp/f034-service-map-fix-focused.xml and tmp/f034-service-map-fix-full.xml.

Contingency audit on 14 November 2026 (Python 3.12.3): 56 policy cases plus 9
D-07 cases passed (65 passed, 2.60 s). Full suite: 249 passed, 2 ROS modules
skipped, 0 failures (4.13 s), with the existing Starlette/httpx warning. Repository
checks and git diff --check passed. JUnit: tmp/contingency-audit-focused.xml and
tmp/contingency-audit-full.xml (local ignored artifacts). The contingency tests
exercise both human and rover with goal detour, direct-base fallback, no escape,
unknown return, insufficient budget and primary search limits. No ROS or physical
return-to-base execution is established by these results.

Earlier audit before contingency support (14 November 2026, Python 3.12.3): 40 policy cases
and 9 D-07 cases passed together (49 passed, 1.84 s). Full Python suite: 233
passed, 2 ROS modules skipped, 0 failures (3.78 s), with the existing Starlette/
httpx deprecation warning. Repository checks and git diff --check passed. Local
ignored outputs: tmp/f034-audit-focused.xml and tmp/f034-audit-full.xml.

Reproduce with fresh basetemp/XML paths (create the ignored tmp parent first):

```sh
python -m pytest tests/planning/test_replan_policy.py tests/planning/test_d07_twenty_metres.py -q -p no:cacheprovider --basetemp=tmp/f034-focused-NEW --junitxml=tmp/f034-focused-NEW.xml
python -m pytest -q -p no:cacheprovider --basetemp=tmp/f034-full-NEW --junitxml=tmp/f034-full-NEW.xml
python scripts/check_repository.py
git diff --check
```

Tests: [test_replan_policy.py](../tests/planning/test_replan_policy.py), including
automatic D-07 after an actual interpolated 20 m prefix, human/rover budgets,
obstacle/uncertainty/margin, irrelevant updates, future return, tasks, deviation,
duplicates, hysteresis, immediate hazard, stale inputs, service progress and
one-leg return adoption. All scenarios/rates are illustrative synthetic data.

Jesus: wire coherent pose/budget/phase/cursor/map snapshots into this API, drive
TICK for deferred work, serialize calls, discard stale asynchronous candidates,
retain return-phase metadata, connect route authorization and supervisor feedback.
No ROS/Gazebo or physical stop/resume validation has been executed here.

David: approve corridor thresholds, horizon, resource/service ledger semantics,
profiles and acceptable uncertainty. Task allocation and multi-goal insertion
remain outside this policy. Callers must authenticate the adopted route context;
this Python API is not an authorization/security boundary. Restart recovery,
persisted event IDs/request sequences and liveness under repeated uncertain maps
still require integration design. Runtime performance on full terrain is unmeasured.
