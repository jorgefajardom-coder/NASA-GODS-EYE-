# Single-human scientific stop/replan — reconciled PR candidate

Base main: `d06de5e6532811a6becbd5be6d52df0e85ab81bf` (including PR52 / D-CLK-01).
Branch: `codex/scientific-human-replan`. David authorized the late-ACK correction,
main reconciliation, regressions, commit and PR. Integration requires review;
this cut does not merge, deploy, freeze the ICD or close delivery milestones.

## Control and ownership

The existing MissionManager is the sole authority. The planner-owned policy
accepts an explicit scientific profile: pending movement/service and advisory
searches reuse ScientificCosts/scientific_plan_route. Historical direct callers
retain explicit legacy compatibility; the integrated wrapper always supplies
the scientific profile. Advice cannot authorize a path: MissionNode registers
fresh immutable context, validates its acknowledgement, calls canonical
PlanRoute and submits the result to the manager's independent current-state audit.

`mge_bringup.mission_replan` composes the existing MissionNode and planner adapter
without a dependency cycle, duplicate manager or service. `mission:=real` selects
this entry point. `replan_policy_file` explicitly opts into the policy; an empty
path retains the existing consumer. A selected policy without its factory fails
closed. The policy configuration is labelled illustrative and does not approve
physical thresholds or scientific coefficients. Operational model-agreement
defaults remain false.

Map advancement invalidates the authorized route before further planning. The
node cancels stale work and publishes an empty active Path. A stop receipt needs
two distinct, post-command, nonfuture stationary AgentState stamps, at least
50 ms apart, stable XYZ and zero linear/angular twist (software tolerances
1e-6). Wrong scope, old/repeated/future stamps, motion and invalid numbers cannot
acknowledge it. These assumptions are software test bounds, not calibrated
hardware safety guarantees.

## Late ACK and D-CLK-01

The defect was callback-order dependent: `observe()` could acknowledge an
already-expired barrier before the polling callback checked its steady timeout;
the old `expired()` then returned false. The corrected receipt checks and
latches failure before accepting feedback and at dispatch, context-response
and plan-response boundaries. An ACK arriving exactly at or after its deadline
is late even when its message stamp predates the deadline.

David explicitly confirmed on 15 November 2026 that pausing the simulated clock
pauses the logical ACK budget, with a separate steady safety watchdog and no
automatic resumption. Accordingly:

- `STOP_ACK_TIMEOUT`: no ACK before five seconds of the run's clock.
- `STOP_ACK_LIVENESS_TIMEOUT`: no timely feedback within five steady seconds.
  While awaiting the ACK this is measured from the stop command; after an ACK,
  fresh stationary feedback maintains liveness until authorization consumes it.
  Repeated stamps cannot extend it. A long pause can therefore cause a safety
  block without exhausting logical ACK time or debiting resources.
- `STOP_ACK_LOST`: motion/pose change after acknowledgement but before a new
  route is authorized invalidates the receipt.

All three failures latch for this run, clear pending/in-flight work and retain
an empty route. Later ACKs, clock resumption and new goal IDs cannot rearm it;
start a new run after investigating the cause. The watchdog requests a logical
stop through the existing execution boundary; this is not physical braking
validation. A successfully authorized route consumes the receipt before its
motion starts. Clock reset remains a separate fail-closed condition.

Main's startup clock preflight is retained unchanged: every simulated-time
selection requires exactly one advancing external clock, including MOCK.
No clock, stamp, resource debit or synthetic stop feedback is invented here.
Jorge's display review and remaining resource-time validation in D-CLK-01 stay
open; this scoped owner confirmation does not approve rates or profiles.

## Current inputs and RETURN

MAP/POSE/RESOURCES/TICK feed a coherent public snapshot and the actual pose and
remaining allocation into the advisory policy. Identical semantic snapshots
are deduplicated. Repeated advice does not churn an existing pending request;
map advancement still invalidates the prior authorization conservatively.

`PlanRequest.candidate_phase` is immutable internal context, not a new ROS
field. Direct contingency RETURN keeps zero remaining service and
`require_return=false` across asynchronous registration/search; no request-ID
heuristic turns it into an outbound task. Existing map/profile/sigma/NoData,
return, reserve, current-pose and cost-agreement gates remain enforced.

## Verification and reproduction

Fresh reconciled evidence belongs to
[`evidence/scientific-replan-ack-20261115`](../evidence/scientific-replan-ack-20261115/README.md).
Its validation receipt, JUnit/logs, source hashes and actual recorder packages
identify the tested candidate. **Final result: 1,686 Python/Jazzy tests passed, 1 historical skip; all eight packages and nine interfaces verified. Web: 421 passed, 1 optional skip; build and repository checks passed.** After two trailing-blank-only cleanups with identical ASTs, 55 final-source consumer/regression checks also passed; both source cuts are recorded.

Earlier local one-hour evidence based on a2efc2e
is historical and is not used as proof of this correction. Its original files
are preserved locally rather than republished with changed provenance.

The end-to-end regression uses actual MissionNode/MissionManager, scientific
PlanningNode, registered context, policy, existing kinematic executor and
recorder over ROS 2 Jazzy / Ubuntu 24.04. It runs a detour, a direct contingency
RETURN and a blocked map, checking fresh ACK before planning, actual stopped
XYZ, consumed resources, unchanged reserves and same-run replay conversion.
The 20x20 flat map and map updates are deterministic SIMULATED test input,
not NASA observations or physical sensing. Model agreement is asserted only
for this fixture, and zero service duration isolates navigation control.
Arrival does not demonstrate inspect/sample work or scientific COMPLETE.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
python -m pytest tests/unit/test_stop_ack.py tests/contract/test_mission_service.py tests/contract/test_mission_launch.py tests/planning/test_scientific_replan.py -q
python -m pytest tests/integration/test_scientific_mission_replan.py tests/integration/test_scientific_cost_service.py -q
python -m pytest -q
python scripts/check_repository.py
cd web
npm test
npm run build
```

Use the pinned Node version and a fresh test-output directory. ROS tests must
run serially in an isolated domain; the integration fixture assigns its own
per-module domain. No evaluator-only reference data is copied or served.

## Remaining gates and next deliverables

- Jesus + Diego: review stop receipts, cancellation, policy wiring and RETURN
  transport in this PR. Gazebo/physical timing and extended concurrency need
  separate evidence; no Gazebo run is claimed by the kinematic fixture.
- David + Daniel + Diego: select a concrete NASA-prior scene and reconcile its
  2.5 m uncertainty with the scientific profile's 1 m limit through an explicit
  scientific decision. No estimate is relabelled or threshold relaxed here.
- Jesus + David: bind append-only movement/service/wait intervals, partial work
  and nonoverlapping cost debit to the real authority and recorder. Full ledger
  and work/result evidence remain deferred, not reimplemented here.
- Jesus + Jorge: demonstrate the same-run scientific work, return and four
  success predicates, then all three roles and their web video. Steps 4/5,
  scientific COMPLETE, three-role acceptance and submission readiness stay open.

JES-07/AC-10 also remains open without notification/endorsement evidence:
Jesus coordinates organizer review; David is backup. The planned 20:00 Bogota
submission cut and four-hour review margin have elapsed. Record the actual
package revision, notification, response and corrections before submission;
silence is not approval. This work sends no external coordination message.
