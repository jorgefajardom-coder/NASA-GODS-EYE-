# F03.3 resource accounting audit (implementation approval pending)

Follow-up: the numerical audit below is preserved as the historical mainc58e7f6
cut. Issue3 (unexplained increases accepted by the pure policy) is now addressed
in the UNCOMMITTED availability-guard change based solely on main0339bbd.
The original characterization artifact intentionally reproduces old behavior;
run it only against its recorded source snapshot. It is not a regression test
for the corrected implementation. New tests are test_f033_resource_guard.py.
No formula/model discrepancy in the numerical tables has been corrected here.

Date: 2026-11-14, America/Bogota. Sole implementation baseline:
origin/main c58e7f6bd36411f2fb34e0389c8663ebde355544, fetched during this audit.
Local feat/planner remains a959d25, an ancestor 135 commits behind that baseline.
The remote planner head69101e9 and all open PR implementations were NOT used.
No merge, checkout of another branch, commit or push was performed. A git archive
of this exact main was extracted under ignored tmp/f033-main; all numerical and
pytest imports used that snapshot, not local branch production modules.
Existing untracked .vscode and scripts/demo_mars_a_estrella.py were left intact.

## Integrated state and ownership

Main contains joint resource-constrained A* FAST, SAFE clearance optimization,
continuous ground-start connectors, D-07 and F03.4 including service progress,
remaining-resource inputs, immutable mission reserves and contingency return.
Snapshot completion/recovery fixes after PR12 are already in main and retained
in the audit snapshot. None is reimplemented here.

The search uses MotionProfile. Mission separately uses mge-science-1.0.0 in
models.py and independently audits the actual outbound/return paths and service
in MissionManager._audit. export_planner_profiles explicitly says NOT equivalent.
Recomputing its projection exactly matches main's planner_profiles.proposed.json;
the numerical discrepancies are mathematical, not a stale registry file.

config/cost_agreement.experimental.json is awaiting_consumer_agreement, with
cost_agreement_approved=false, profiles_approved=false and operational_authorization=false.
Scoped scenario approval JZ-APP-20261114-01 does not approve the projection.
activity_duration.pilot.json is pending_review; do not promote its sensitivity
durations to mandatory activities. D-EST-01 is accepted scope with coordinated
implementation pending, not a new cost formula or safety waiver.

## Formula inventory (actual code, not independent scientific validation)

h = horizontal distance; z = signed rise; d = sqrt(h*h+z*z);
u=max(z,0)/h; w=max(-z,0)/h; v=speed; duration=t. Ground edges require h>0.
k = OXYGEN_L_PER_WH defined in models.py from the registered standard-gas model.
All coefficients below are loaded from existing main profiles, never invented.

| Layer / operation | Time | Energy Wh | Human O2 litres |
| --- | --- | --- | --- |
| Planner movement | d/v * (1+a_up*u+a_down*w) | d*e_m*(1+b_up*u+b_down*w) | time*r_O2 |
| Planner service (one goal transition) | t | P_service*t/3600 | t*r_O2 |
| Human science movement | h/v*(1+s*abs(z)/h) | (P_walk*time + (m_body+m_suit)*g*max(z,0)/eta_climb)/3600 | energy*k*oxygen_scale |
| Rover science movement | d/[v*(1-slip)] | [P_aux*time + max(0,m*g*(Crr*cos(theta)+sin(theta)))*d/(eta_drive*(1-slip))]/3600 | Not applicable |
| Drone science movement | max(h/v,abs(z)/v_vertical) | [P_selected*time + m*g*max(z,0)/eta_climb]/3600 | Not applicable |
| Science explicit activity / wait | t | P_activity*t/3600 | energy*k*oxygen_scale for human only |

Drone power selection is translate if h>0, else ascent/descent. The current
planner drone grid projection does not establish flight/clearance capability.
There is no regenerative energy credit in these models. inspect/wait/sample
are different named activities even when current human inspect/wait powers match.
The projection uses max(activity powers) for P_service and a constant conservative
human oxygen rate. It cannot express a mixed activity schedule exactly.

## Reproduced numerical discrepancies

Inputs: ten consecutive 1 m horizontal segments, each rising/falling 0.1 m for
the slope cases (10 m horizontal, +/-1 m total); profile step/grade constraints
are respected per edge. Stationary cases last120 s. These are synthetic analytic
inputs using main's proposed coefficients, not physical consumption measurements.
Full precision and profile/source hashes are in the evidence numeric JSON.

| Agent / case | Planner (time s, Wh, O2 L) | Science (time s, Wh, O2 L) |
| --- | --- | --- |
| Human flat | 12.000480, 1.392389, 0.504558 | 12.000480, 1.392389, 0.284330 |
| Human ascent 10% | 14.472400, 2.510657, 0.608489 | 14.400576, 2.498197, 0.510139 |
| Human descent 10% | 14.472400, 1.399334, 0.608489 | 14.400576, 1.670867, 0.341196 |
| Human inspect or wait120s | 120, 15.372333, 5.045374 | 120, 11.936000, 2.437364 |
| Human sample120s | 120, 15.372333, 5.045374 | 120, 15.372333, 3.139072 |
| Rover flat | 277.777778, 9.392747, N/A | 277.777778, 9.392747, N/A |
| Rover ascent 10% | 279.163212, 12.809714, N/A | 279.163212, 12.784626, N/A |
| Rover descent 10% | 279.163212, 9.439594, N/A | 279.163212, 7.754534, N/A |
| Rover wait120s | 120, 6.666667, N/A | 120, 2.666667, N/A |

Critical counterexample: the same human ascent+return descent costs3.909990 Wh
under search versus4.169064 Wh under science. On the returned FAST and SAFE
paths, an allocation of search_cost+5 Wh accepts the candidate with5 Wh reserved,
but science leaves only4.740927 Wh. This does NOT mean MissionManager authorizes
an unsafe route: MODEL_NOT_AGREED/MODEL_MISMATCH gates remain. It demonstrates
that the search projection is not a uniformly conservative energy bound.
Changing only one slope coefficient cannot remove the 3-D/horizontal-distance
and activity/O2 differences. Do not loosen tolerances to hide this gap.

## Estimated versus consumed: what already works

- core._search adds the connector once before pruning; adds goal service once
  in the phase transition; searches directed return jointly; caps every label by
  available minus required time/energy/human-O2 reserves. Unknown proof/search
  bounds remain UNKNOWN, not a fabricated insufficient-budget proof.
- Input ResourceBudget reserves are required minima. Output RouteResult.reserve_*
  represents estimated availability AFTER the entire candidate, not actual spent
  resources and not another reserve debit. Do not subtract it again.
- ReplanPolicy never debits history. It uses supplied current remaining resources,
  zero service in RETURN, and only service_remaining_s during SERVICE. OUTBOUND
  cannot claim service completion. It separately stops on depleted reserves.
- MissionManager._remaining_primary_budgets subtracts telemetry deltas from the
  goal allocation, preserving reserves. update_agent rejects resource increases;
  estimates are not automatically booked as consumption.
- RemainingResources supports below-reserve telemetry without weakening the
  ResourceBudget planning invariant. Robots retain None oxygen internally,
  with existing ROS NaN / JSON null representations at the boundary.

## Gaps and audit findings

1. No exact science-cost backend in A*. Movement/O2/activity mismatches can
   change feasibility as well as mission acceptance. The human descent case is P0.
2. PlanRequest only has aggregate service_time_s; no activity identity, wait kind,
   stop interval or schedule ledger in the planner contract. Mission's internal
   request has service_activity but the unchanged ROS PlanRoute does not transmit
   it. Main's cost-agreement kit proposes versioned context binding; it is pending.
3. ReplanPolicy trusts supplied availability and has no consumption ledger or
   monotonic-availability guard. A characterization supplies the original budget
   after a spent budget; policy issues a new request with that larger availability.
   MissionManager rejects replenishment, but the independent Python API does not.
   This is a caller-boundary risk, not evidence that the existing manager resets it.
4. Partial service is supported by the pure policy with an explicit remaining
   duration; MissionManager._schedule_plan still uses the full primary duration
   until explicit completion. _continuation_reason documents this limitation.
   Once telemetry includes partial service spent, charging full future service
   can be conservative double-accounting. No runtime fix to mission is made here.
5. Reserves are enforced as supplied, immutable across policy replan context;
   zero reserve values remain legal inputs. The core cannot infer David's minimum
   required allocation or verify telemetry truth. Do not invent positive minima.
6. No planner-side distinction between ground wait and airborne hover, or distinct
   inspection/sample powers. Unknown height/terrain and all existing physical
   constraints must remain independent of cost reconciliation.

## Proposed stages and files (not implemented)

1. Freeze this main source and adopt independent numeric golden/differential
   tests; review cost_agreement.experimental.json with David/Jesus. Confirm
   model/profile hash and explicit activity/wait/current-budget context binding.
2. Small planner-only guard: ReplanPolicy.evaluate should reject unexplained
   increases in supplied remaining resources across the same mission, with
   human/rover tests and latched invalidation. Do not debit telemetry a second time.
3. After formula approval, add a pure immutable science-compatible cost backend
   under mge_planning; reuse main's models API or reviewed common implementation,
   not a copied competing science model. Wire core._motion_costs/_search and
   connector costs, explicit fixed-schedule service costs and policy pending costs
   through one backend. Default model/version and adapter.load_profiles migration
   require consumer agreement. No MissionManager or ROS edits are authorized here.
4. Owner-led actual consumer acceptance, partial-service/stop schedule integration,
   source/model/config hashes and FAST/SAFE workload benchmarks. Keep scientific
   and route-authorization gates until that evidence passes.

Likely owned files: new mge_planning/resource_costs.py (proposed), core.py,
replan.py, adapter.py and tests/planning/test_resource_costs.py (proposed), plus
MODEL.md, planner_handoff and required disclosures. node.py only if approved
configuration needs binding; no unilateral wire fields. Other-owner models.py,
MissionManager and configuration remain dependencies, not authorized edits.

Heuristic: with the existing projected speeds, science ground times remain at
least h/v_projected. The planar-time bound plus the exact remaining fixed service
duration can remain admissible; re-prove it for the chosen backend. Nonnegative
edge costs preserve additive label dominance; regenerate budget-boundary and
directed-return tests. SAFE geometry is unchanged, but feasible paths/bottleneck
optima may change. Cache by model/profile identity; never mix backend versions.
Complexity is unchanged for fixed edge/goal costs, but label counts and runtime
are NOT measured for the proposed backend; benchmark rather than promising speed.

Required regressions: flat/up/down/zero and invalid ground vertical; profile limits;
human-only O2; distinct activities/waits; consumed prefix plus remaining suffix;
45s completed +75s pending activity versus120s whole; duplicate completion/event
idempotency; monotonic budgets; exact reserve boundary and one-resource-at-a-time
shortage; return from current pose; connector once; FAST vs independent oracle,
SAFE clearance and bounded UNKNOWN; same model on actual mission consumer.

## Executed tests and limits

Main planning + mission models/conformance/manager selection:407 passed,2 omitted.
New characterization regressions:10 passed, none omitted. They deliberately
ASSERT existing discrepancies; these passes do not imply model agreement.
Full snapshot plus those10 tests:991 passed,20 omitted, one existing
Starlette/httpx warning (981 original tests passed). ROS modules, host symlink
privileges and an unavailable optional external snapshot account for omissions.
No ROS/Gazebo/physical run or new backend performance test was executed here.
Baseline snapshot production sources were not modified. No new implementation,
commit, push or PR; stop here for approval of formulas and implementation scope.

## Implemented first correction: main0339bbd review cut

ReplanPolicy.evaluate stores a bounded observation of admitted remaining values,
initially capped by the original mission allocation. It rejects strict increases
of time/energy/human oxygen with an explicit UNKNOWN reason, latched invalidation
and no search/candidate. Original reserves and phase, progress, service and map
guards remain. A rejected increase cannot ratchet up the bound; lower depleted
resources also remain recorded, so later route replacement cannot replenish them.
No consumed estimate, telemetry delta or reserve is debited by this guard.

The immutable mission template and run/agent scope are existing instance limits.
New mission = new externally supplied policy instance, not a route/event reset.
Corrected resources alone cannot recover authorization; an independently adopted
compatible new route can clear invalidation without resetting the resource bound.
There is no new reset/recharge API, no authentication/mission-authority claim and
no restart persistence. Legitimate future replenishment requires a new contract.
Strict comparison matches main's no-replenishment telemetry assumption; no
floating-point allowance grants extra resources. Callers must supply coherent
authoritative snapshots and serialize calls.

The initial regression run exposed reason-priority masking of PROGRESS_ROLLBACK;
the guard order was corrected, preserving the existing test unchanged. New cases
cover human/rover constant and decreasing resources, partial service, each
resource increase, both budget types, duplicate/obsolete events, lower depleted
reserves, continuous starts, authorized adoption, and new missions/runs.
Exact outcomes and final source hashes are retained in
evidence/planner-f033-guard-20261114. The historical implementation.patch remains
local and unchanged, excluded from the commit; use Git's committed diff for review.
Production changes are confined to replan.py;
core costs, ResourceBudget, RemainingResources, MissionManager and ROS are unchanged.

Final guard validation: baseline planning283 passed; final planning309 passed (26 new cases); focused F03.3/F03.4/D-07123 passed; complete Windows1025 passed/20 skipped with one existing warning. Jazzy planning/contracts/mission/unit946 passed/1 optional external snapshot skipped; all8 packages built and6 messages/2 services inspected. No ROS integration/Gazebo run is implied. Repository and whitespace checks passed. These selections overlap and must not be added.

Delivery revalidation against published main `b5dc681` (fast-forward, no new
commit): the intervening changes affect web/Pages and disclosures, not planner
code or cost models. Planning 309 passed; focused F03.3/F03.4/D-07 123 passed;
Windows suite 1025 passed / 20 skipped. Web 170 passed / 1 skipped; build passed.
Fresh Jazzy validation is blocked before execution by WSL
`HCS/ERROR_NO_SYSTEM_RESOURCES`; the earlier 946 passed / 1 skipped result is
historical, with unchanged guarded-source hashes, not a new integration pass.
See `evidence/planner-f033-delivery-20261114/validation.json` for the delivery cut.
