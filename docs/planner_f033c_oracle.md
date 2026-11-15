# F03.3-C independent itinerary oracle — integration pending

Base: feat/planner 921f1d06f5caff85c42d323af757b882b3b05d4c, preserving
1f90854407817ef464f9acc74b5501d21f687c1c. Fetched main remains
6bcf208868e37b7e15e9189fac11de96e7414eff. No PR implementation imported.

## Coordination boundary

PR28 metadata inspected via GitHub, head 7f0ebaaefa90b7ae48505f8e06d22f2660e5d491,
draft/open at inspection. Its description says the scientific API selection
(D-COST-02) is being integrated in a separate logical commit and current draft
does not claim backend/activity transport complete. This is a coordination claim
on an open PR, not published main or scientific approval. No patch was copied.
Jesus must assign the owner and reconciliation order for core/replan changes
before those files are edited. This cut is tests, evidence and design only.

## Oracle and scope

tests/planning/scientific_oracle.py enumerates every simple directed path on each
leg and every outbound/return combination. It does not use production A*, heaps,
labels, dominance, geometry or adapter aggregation. Direct calls to published
estimate_segment/estimate_activity supply costs; no equations are copied.
Cycles can be removed without improving nonnegative additive resources under the
fixed activity schedule. Returning may revisit outbound cells. This deliberately
exponential method is for tiny graphs only; no real-time claim is made.

Activities require distinct explicit identities, kinds and pending duration.
No consumed prefix is debited. Each complete candidate is checked against
available minus each separate reserve, without tolerance credit. FAST oracle
chooses minimum time; SAFE oracle chooses maximum bottleneck then minimum time
among feasible itineraries. All alternatives remain available until feasibility
selection, so a slow resource-saving path is retained.

Graph adjacency and clearance are SYNTHETIC supplied inputs. They do not prove
map footprints, obstacles, corners, sigma, slope or connector safety. Profiles
provide grade checks through the science API; full geometric admission stays
with production and must be tested separately when wiring the backend. A connector
node represents the exact current pose and its cost once; this is accounting
evidence, not a new physical connector validator. No mission is authorized.

## Reproducible counterexample

Coordinates/edges and both full-itinerary totals are in results.json. Human
profile coefficients are unchanged. Start S=(0,0,0), goal G=(4,0,0), base S;
alternative intermediate nodes H=(2,0,0.2) and D=(2,1.5,0). Outbound edges S-H,
H-G, S-D, D-G; return edge G-S. No activities for this counterexample.

| Full itinerary | Legacy time s / Wh | Science time s / Wh |
|---|---|---|
| S-H-G-S | 10.589151924 / 1.338953692 | 10.560422417 / 1.390768345 |
| S-D-G-S | 10.800432017 / 1.253150126 | 10.800432017 / 1.253150126 |

Available energy 2.36 Wh and reserve 1 Wh give a cap of 1.36 Wh. Time and human
oxygen availability are each 100, with separate reserves of 1. Legacy selects
H; science rejects H and selects D. This is a full-route resource-constrained
selection change in the independent oracle, NOT an executed production A* result.
The test imports legacy _motion_costs only for the comparison; science enumeration
does not depend on it. SAFE uses synthetic H clearance2 versus D clearance4.

Tests additionally cover human/rover directed grades, inspect plus wait, partial
service, exact/representable reserves, individual nextafter shortages, continuous
prefix accounting, disconnected graph, duplicate IDs and the known descent edge
feasibility discrepancy. Published functions are the numerical reference; existing
F03.3-B tests retain direct stored-vector equivalence checks.

## Minimum future production diff (NOT APPLIED)

1. plan_route: optional keyword-only scientific context, absent by default. Require
   matching run/request/agent/map, model/profile/scenario identity and explicit
   pending schedule. Incomplete context fails closed with no legacy fallback.
   Keep service_time_s semantics; never infer inspect. Fixed goal waits have their
   own IDs/kinds; arbitrary route stopovers/time windows remain unsupported.
2. _Geometry.edge/start_connector: separate legacy admission from _motion_costs;
   preserve all current step/grade/corner/footprint/sigma/z checks before delegation.
   After admission call the same ScientificCosts.movement on directed endpoints.
   Store connector costs in the initial label exactly once. Geometry clearance
   may use symmetric keys; cost cache must use ordered endpoints/model/profile.
3. _search: use selected costs BEFORE capacity pruning and dominance; sum explicit
   pending goal activities once at the goal phase transition. Retain joint return
   search and resource caps. Reconstruction must expose the same estimates.
4. Heuristic: planar remaining outbound+return distance divided by a proven maximum
   horizontal speed, plus pending fixed goal duration. Human vmax=speed; rover
   vmax=speed*(1-slip). Prove consistency on each edge and phase transition against
   the oracle. Until proved for the selected context, use h=0. No flight safety
   inference from drone cost estimates.
5. SAFE: same backend/context in every threshold trial, unchanged lexicographic
   clearance/time objective and shared work limits. Optima may change with resource
   feasibility. Exhausted work remains UNKNOWN; caches bounded and map-sensitive.
6. ReplanPolicy: identical backend for pending validation and candidate search;
   preserve F03.3-A's nonincreasing resources, reserves, phase/progress/service,
   invalidation and external route adoption. RETURN abandons goal work, SERVICE
   retains unfinished work only. Costs never replenish or debit execution resources.

Future acceptance must compare actual A*/SAFE output to this oracle (including
the route-flip fixture), test heuristic bounds, actual raster admission, connectors,
map/backend cache changes and search caps. Current tests do NOT validate a wired
production backend. Full raster counterpart still requires layout/clearance checks.

## Dependencies, approvals and validation gates

No dependencies added. Experimental adapter imports pure mge_mission.models;
neither package manifest declares a dependency on the other. Jesus must approve
planning->mission runtime dependency/import graph or owner-led shared extraction,
plus schedule transport and who implements the overlap with PR28. No copied model,
ROS schema change or MissionManager edit is proposed here. David must review
numerical equivalence, activity meanings, provenance and heuristic assumptions;
proposed profiles and MODEL_NOT_AGREED/MODEL_MISMATCH gates remain intact.

Performance risks: exponential oracle, more nondominated labels under science,
repeated SAFE searches, directed cache growth. Preserve bounded work and fail closed
on incomplete context, overflow, unresolved geometry or stale resource snapshots.

Native ROS and actual consumer wiring are not executed in this cut. Prior WSL
resource failures remain an unresolved validation limit, not a pass. No LIVE or
physical certification claimed. Organizer notification/endorsement remains a
separate team submission gate; this cut is not submission readiness.

Final validation: 12 independent cases passed; full Python suite 1085 passed,
20 skipped, one existing warning. Counts overlap. Repository and whitespace
checks passed. Exact JUnit results/hashes are in the oracle evidence directory.
