# mge_planning

Owner: Diego. Status: **P0 kernel, guarded ROS service and ROS-independent F03.4
policy implemented; mission/supervisor integration pending**.

| Layer | Responsibility |
| --- | --- |
| R | R07, R08, R09, R10, R12, R18 |
| F | F03: route feasibility and resource verification |
| L | GridValidator, CostmapBuilder, RouteSearch, ResourceEstimator, RouteVerifier, ReplanPolicy |
| P | Pure `mge_planning/core.py`, event policy `mge_planning/replan.py`, ROS service `mge_planning/node.py` |
| V&V | Synthetic unit/integration tests, including 20 m D-07 and contingency return; full mission acceptance pending |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_planning planning_node`.
This starts the PlanRoute service; explicit profiles and a coherent map batch
are required before it can return a candidate. It never publishes an active route.
Scientific mode is now the default: set `scientific_profiles_path` to the same
full registry as MissionNode and register each typed activity/request context
through `/mge/planner/register_context` before PlanRoute. Proposed profiles need
explicit illustrative opt-in. `profiles_file` applies to explicitly selected
legacy compatibility (`allow_legacy_cost_model=true`), not scientific pricing.
See [migration and executed verification](../../docs/scientific_cost_integration.md).
`core.py` imports without ROS; NumPy and SciPy are required.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Planning: outbound, service and return

Input: public belief, sigma, NoData/traversability masks, TerrainMeta, current pose,
goal, base, run/request IDs, map version, route mode and per-agent budget. Output
RouteDecision with outbound/return paths, costs, reserves, version,
status and reason. SI fields use snake_case (`energy_est_wh`, `oxygen_est_l`).
FAST uses bounded resource-constrained A* jointly over outbound travel, service
and directed return. It retains nondominated resource labels rather than choosing
each leg greedily. SAFE maximizes conservative bottleneck clearance within budget,
breaking ties by time. EFFICIENT explicitly returns MODE_NOT_SUPPORTED; D* Lite is
not implemented. See [MODEL.md](MODEL.md) for heuristic and proof boundaries.

Unknown terrain is not free space. `UNKNOWN` and `NO_PATH` are distinct outcomes.
Humans alone have a separate oxygen budget; all profiles have hypothetical time
and energy constraints. Validate outbound + service + return + reserve for every
resource. Never read evaluator reference or undiscovered POIs.

## Continuous initial positions

Continuous human/rover starts are an experimental opt-in: Python
`plan_route(..., allow_continuous_start=True)` or the ROS node startup parameter
`allow_continuous_starts:=true`. Both defaults are false, retaining the current
consumer NON_CELL_CENTER baseline until Jesus/David approve the extension.
The planner validates a straight
connector to the containing cell centre: the whole swept segment must satisfy
known terrain, obstacle/uncertainty clearance, footprint plus localization allowance,
map boundaries and directed slope/step restrictions. It never snaps an unsafe start
to another free cell. Connector time, energy and human oxygen initialize A* before
budget pruning. The output retains the exact initial 3-D pose and every graph
waypoint, with Python-only start_connector metadata. A 2-D start uses belief height.
An explicit human/rover z must match the known containing-cell height within
1e-6 m for both centred and continuous starts; otherwise ERROR/INVALID_START_Z.
It never projects an inconsistent pose silently. This is a grid-model guard,
not validated localization accuracy. SERVICE/RETURN goal/base comparisons use XY.
Goals/bases remain cell centres; a continuous start requiring return needs an
explicit centred base. Continuous drone flight is unsupported.

## D-07: request after 20 metres

`tests/planning/test_d07_twenty_metres.py` traverses/interpolates exactly 20 m of the
initial synthetic polyline before adding an obstacle to its pending portion and
incrementing map_version. The next explicit request starts at the resulting
continuous pose and uses availability minus actual prefix consumption exactly once,
with reserves unchanged. Tests check detour, connector, full-segment collision,
remaining service, return and separate no-path/resource failures for human/rover.
This is computational trajectory interpolation, not validated vehicle motion.

## F03.4: events, hysteresis and contingency return

`ReplanPolicy.evaluate()` accepts an authoritative pose, phase, progress cursor,
remaining resources, public map and event. It checks complete pending segments,
including the future return, for obstacles, uncertainty, margin and terrain changes.
It detects corridor deviations and task notifications, and records reason_code,
trigger_reason and candidate results in a structured decision:

| Decision | Meaning |
| --- | --- |
| KEEP | Route unaffected, duplicate event, or soft reevaluation deferred; no execution authority |
| REPLAN | Candidate proposed; MissionManager must inspect and authorize it |
| STOP_REQUIRED | Immediate hazard, infeasible continuation/return, or invalidated route awaiting replacement; supervisor performs the stop |
| UNKNOWN | Insufficient data, stale/inconsistent context or work bound; never authorizes movement |

Spatial enter/exit thresholds and a minimum search interval suppress soft-event
storms. Deferred deviations are discarded after corridor recovery; task
notifications survive until reevaluation. UNKNOWN/SEARCH_LIMIT has at most two
retries by default, separated by min_interval_s, then STOP_REQUIRED with
SEARCH_RETRIES_EXHAUSTED. These remain proposals and never restore authorization.
Safety checks precede
deduplication/hysteresis and invalidation is never delayed by cooldown. Finding a
feasible candidate does not clear invalidation or authorize its execution.

During OUTBOUND or SERVICE with unfinished activity, a primary mission result of NO_PATH or INSUFFICIENT_BUDGET triggers
one automatic direct-base evaluation from the current pose, using the SAME remaining
budget and reserves, service_time_s=0 and require_return=False. If feasible, the
policy proposes candidate_phase=RETURN and reason CONTINGENCY_RETURN. The failed
primary request/result remain available for audit. If base is also inaccessible or
unaffordable, it returns STOP_REQUIRED; unresolved return data/search yields UNKNOWN.
A viable goal detour retains the primary objective and required return. An
inconclusive primary search is not a proof of infeasibility and does not trigger
this fallback. No recursive contingency search occurs during RETURN.

This proposes a phase transition; it does not enact it. MissionManager must adopt
the candidate, change the phase to RETURN and abandon the pending service. The
unchanged ROS service has no phase field: the single-leg return appears in
outbound_path with an empty return_path. Consumers must preserve the policy's
phase context. Existing RETURN requests also charge zero service; SERVICE requests
charge only service_remaining_s. The policy never debits historical consumption.
RemainingResources accepts depleted live availability; the policy returns an
explicit STOP_REQUIRED for violated time/energy/human-oxygen reserves before
constructing a strict ResourceBudget. Planner admission invariants stay unchanged.
During OUTBOUND, service_remaining_s must still equal the original service duration;
a decrease is rejected as UNKNOWN/OUTBOUND_SERVICE_MISMATCH without launching A*.
Service can decrease only in SERVICE at the goal. Event/map version mismatches
also return a fail-closed decision with invalidate_active=True, including harmless
map changes; matching subsequent events cannot silently restore authorization.

Full API/limits: [event policy](../../docs/replan_policy.md).

## Local checks and integration limits

From the repository root, using Python 3.12 and the existing development environment:

```sh
python -m pytest tests/planning -q
python -m pytest
python scripts/check_repository.py
git diff --check
```

For native Windows, invoke `.venv/Scripts/python.exe` explicitly. Create the ignored
tmp parent, then use fresh `--basetemp=tmp/NAME` and `--junitxml=tmp/NAME.xml` options
when system temp permissions require it or recording execution evidence.

ROS tests require Ubuntu 24.04 / ROS 2 Jazzy, a built/sourced workspace and coherent
metadata/belief/sigma/mask batches. The event policy is not wired into the ROS node,
MissionManager or supervisor. No ROS wire definitions were changed. Physical
stop/resume, dynamics, real pose/resource synchronization, restart recovery and
full-terrain runtime remain unvalidated. All test profiles/thresholds are
illustrative. Daniel's final map products and David's approved assumptions are
pending. See [handoff](../../docs/planner_handoff.md) for producer/consumer dependencies.
See the [PR12 review audit](../../docs/pr12_review_corrections.md) for executed
results, regression evidence, cache/clearance rules and remaining integration gates.
