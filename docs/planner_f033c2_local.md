# F03.3-C2: local, explicit scientific Python search

Local base ffea8c251a256524d409ad843c47fa1b39cc9b6b preserves F03.3-A/B/C1
and PR33's synchronization. Reference-only origin/main at inspection:
5a7db3d5081f9e85a824744124aa2dcb2a8c792e. No remote changes were incorporated.
This work is local-only, not an update to PR33 or the integrated application.

## Interface and admission

Call plan_route(..., scientific_context=context) explicitly. Absent context
preserves legacy costs, heuristic and route identity; an incomplete/mismatched
non-None context returns ERROR/INVALID_SCIENTIFIC_CONTEXT, never legacy fallback.
ScientificContext.from_files binds the actual registry/scenario bytes and selected
profile to one immutable PlanRequest. See planner_scientific_context.md for scope.
All coefficients remain those of the published mge-science-1.0.0 model; no model
equation, profile approval or transport contract was changed.

Supported scientific search agents are human/rover. All fixed service activities
and goal waits have explicit IDs, kinds and remaining durations. The service
tuple must match service_time_s; a positive duration without explicit activities
is rejected. Waiting is separate and occurs after service. There is no activity
choice, dynamic/parallel waiting, stopover, recharge or flight-planning extension.
SERVICE starts at the goal with unfinished work; RETURN is a one-leg base request
with empty abandoned/completed goal work. The caller owns authoritative accounting.

## Search integration

_ScientificGeometry wraps the existing admitted geometry. Its base still checks
directed slope/step, corners, unknown/NoData, sigma, footprint/localization, z and
swept margins. Legacy resource estimates in that geometry view are discarded;
they cannot prune scientific labels. The scientific profile cannot weaken the
geometric profile. Exact directed endpoints are then passed to ScientificCosts,
which delegates estimate_segment. A validated continuous connector is costed the
same way and seeds the first label once, including human oxygen. ROS still has
no opt-in path for scientific context.

Scientific edge and goal-activity costs enter the same _search labels before
capacity checks and componentwise dominance. Goal costs are precomputed through
estimate_activity and charged once at the phase transition. Joint outbound/return
search remains; reverse edges never reuse forward costs. Limits and separate
reserve caps are unchanged. No numerical comparison tolerance grants resources.
Nonfinite scientific accumulation fails with SCIENTIFIC_COST_ERROR.

The scientific heuristic is intentionally h=0. Nonnegative additive costs make
this an admissible multi-label A* specialization. This avoids unproved legacy
speed/grade assumptions, at the expense of more expanded labels. Dominance remains
valid only at the same cell/phase and fixed context, with arrival-history-independent
work. SAFE still maximizes conservative bottleneck then minimizes complete time
among resource-feasible routes; every threshold uses the same context and shared
work budget. Incomplete proofs still return UNKNOWN/SEARCH_LIMIT.

The scientific ordered-endpoint cost cache is bounded at 8192 entries and local
to one immutable request/map view; it is reused across that call's SAFE trials.
The legacy geometry cache remains separate. No cross-request scientific cost
reuse, model switch or reverse-edge collision is allowed. Geometry is untouched
by selecting/deselecting the backend.

Python RouteResult.cost_context retains the admitted context. Its fingerprint
binds scientific route identity, including the pending schedule even when numeric
costs match. This is Python provenance, not authentication. Do not send the context
through current ROS fields or dataclasses.asdict serialization: profile maps are
immutable and there is deliberately no wire schema or node activation for it.

## Replanning and F03.3-A

An experimental policy call must supply scientific_context for the CURRENT
snapshot. Construct its request from the original mission with current pose,
remaining budget, map version, explicit pending service duration and the active
request ID. Bind its phase to ReplanState.phase; RETURN targets the base with no
goal work. The active RouteResult also supplies its original context, validated
against active_request. Missing context, model mismatch or an attempted legacy
downgrade fails closed with invalidation, before a new candidate is produced.

Policy compares source/profile/scenario identity and per-activity pending progress
throughout the instance. OUTBOUND cannot complete goal activities; SERVICE may
decrease service durations, then explicit goal waiting. Types/IDs cannot be added
or changed to hide rollback. RETURN may abandon remaining goal activities. A
new model or mission needs a separately controlled new policy instance; the policy
does not authenticate who creates it and does not persist across restarts.

F03.3-A's availability bound, original reserves, phase/progress/service checks,
invalidation latch, event/hysteresis/retry behavior and external route authorization
remain. A different authorized route can clear the latch, never restore budget.
Pending movement/work uses the same scientific functions as candidate search.
Candidate contexts are rebound to the new request without any resource debit.
Contingency return drops abandoned work explicitly. Zero service does not silently
discard pending waiting or imply that waiting has already been consumed.

## Independent validation

- The unchanged C1 oracle enumerates full itineraries using published functions;
  neither its enumeration nor its dominance is reused by the production search.
- The actual _search engine is exercised on C1's directed graph. At a 1.36 Wh
  usable cap it retains S-D-G-S, matching the exhaustive optimum; synthetic graph
  clearance does NOT validate a physical/raster corridor.
- Public plan_route is checked against exhaustive enumeration on a fully known
  tiny raster, for both agents and FAST/SAFE, explicit service and waiting.
- A separate real 2x3 raster with heights [[0,0.2,0],[0,0,0]], resolution2 m,
  human published profile, and 1.6 Wh usable cap changes legacy/scientific routes
  in both FAST and SAFE. Science avoids the hill and matches the exhaustive
  feasible time/resource optimum. No coefficient was adjusted.
- Exact reserves and nextafter shortages, directed costs/cache separation,
  blockers/unknown/sigma/height/footprint/z, partial service, continuous connectors,
  wrong context, work limits and medium-grid bounded work are covered.
- Scientific D-07 tests interpolate an ACTUAL 20 m polyline prefix, subtract only
  its science estimates, update the obstacle/map version, and replan from current
  continuous pose with future work and return. Whole-segment obstacle checks are
  independent. This is synthetic travel, not vehicle dynamics or physical validation.
- The first search-test run rejected rover fixtures because its unchanged 1.75 m
  footprint could not fit the 2 m cells/map boundary. Fixture scale was corrected;
  no profile or safety validation was relaxed to make tests pass.

Exact outcomes, source hashes, computational comparisons and JUnit are retained
under evidence/planner-f033c2-local. Tests overlap; do not add selection counts.
Timing/label measurements are software measurements, not physical resource data.

Final validation: Windows full1207 passed/22 skipped/one existing warning; focused
F03.3/D-07/F03.4 250 passed; native Jazzy planning/contracts/mission/unit1088 passed/
one absent external snapshot skipped. Eight packages built, six messages/two
services inspected. Web201 passed/one skipped and build passed. The first native
run had14 setup errors because pytest treated helper setup as an xunit hook;
renaming it scientific_case fixed cross-version collection without changing any
assertion. Superseded error evidence is retained. Repository/whitespace checks pass.

## Integration limits and owner review

Nodes, adapter, MissionManager, scientific models, package manifests and ROS
definitions are unchanged. Legacy imports do not load mge_mission; explicit science
still needs the experimental planning->mission import in the local Python path.
Jesus must review installed-package dependency and complete context/consumer
transport before activation. David must review numerical semantics, profiles and
precision separately. MODEL_NOT_AGREED/MODEL_MISMATCH and all mission-authority
gates remain; a Python FEASIBLE result is not approval, LIVE execution or certification.

No push/PR/update/merge is part of this cut. No real mission, Gazebo dynamics,
three-agent mission or same-run science execution/replay closure is established.
Submission readiness and organizer notification/endorsement remain separate
AGENTS.md gates coordinated by Jesus/David.
