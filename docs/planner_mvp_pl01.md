# MVP-PL-01 - Local planner/mission compatibility validation

Source: `feat/planner@d81407dea855c745976a731cfd5dfa8099caca94`, plus the
test/documentation changes recorded with this report. The three local C2 commits
`9c69980a`, `afd6a281` and `d81407de` are preserved. Fetch confirmed
`origin/main@7ad605039a524d5b5cbe2c983f2da9113f8b1ce9` (PR33 merged) and
`origin/feat/planner@ffea8c251a256524d409ad843c47fa1b39cc9b6b`.
No merge, rebase, publication or frozen-delivery baseline change was performed.

The owner reports David's and Jesus's technical conformity with C2. This closes
that local technical review; it does not approve profile coefficients, select a
ROS context contract, activate the backend or complete mission acceptance.

## Reconciliation and actual gap

Read AGENTS, ICD/contract baseline, mission checklist, D-COST-02, D-DEL-03 and
current owner handoffs. Main's intervening commits change documentation/web,
including delivery-scope clarification and display resource sufficiency.
`git diff HEAD...origin/main -- src tests config scripts data` is empty:
published mission, ROS consumers, scientific models and input fixtures have no
new concurrent implementation changes relative to the common source.
Main is a reference only; its newer web changes were not imported or tested here.

Existing code already provides joint outbound/work/return FAST/SAFE search,
directed scientific estimates, explicit activities, strict reserves, validated
continuous connectors, bounded search and F03.3-A/F03.4 invalidation/recovery.
Existing tests cover D-07, partial service, inconsistent scientific contexts,
geometry, depletion, the independent oracle and legacy regressions. Existing
MissionManager tests use a controlled candidate; existing C2 tests exercise the
planner/policy separately. The missing boundary was an actual scientific A*
result consumed by the unchanged actual Python MissionManager.

## Added coverage (12 cases; no production changes)

`tests/planning/test_mvp_mission_consumer.py` translates the existing Python
pending request explicitly in a test helper, calls the real planner, and passes
its actual output through the real manager's independent cost/identity audit.
The helper lives only in tests. It is not a proposed production adapter or wire
contract. Mission's uppercase kind is translated deliberately to planner's
lowercase kind. Activity comes from `pending.service_activity`, never inferred
from `service_time_s`. Both interfaces already expose the needed Python values.

| Cases | Evidence asserted |
| --- | --- |
| FAST and SAFE (2) | Scientific outbound + explicit inspect + return is feasible; computation alone does not authorize. Manager explicitly adopts the candidate, with success still false. |
| Same two flows | Synthetic telemetry advances 1 m; shared science API estimates that interval once. Map changes from 1 to 2 with a new obstacle, immediately clearing the route. Remaining time/Wh/O2 become the next budget; old result cannot replace the pending request. |
| Same two flows | Replanning starts at the exact continuous XYZ, retains its connector, avoids the obstacle with full-segment/expanded-square checks, and preserves return/reserves. An explicit manager return request creates one directed base leg without repeating service. |
| Wrong run/request/agent/map (4) | Actual feasible output with a corrupted identity cannot authorize a route. |
| Model gates/legacy (2) | Scientific candidate is blocked by MODEL_NOT_AGREED when agreement is absent. Default legacy search remains feasible under its own model; the manager rejects its incompatible numerical estimates with MODEL_MISMATCH. |
| Time/energy/O2 (3) | Availability equal to the required reserve leaves no spending allowance; actual search returns INSUFFICIENT_BUDGET and no route is authorized. |
| Bounded search (1) | Deliberately restrictive one-label negative test returns UNKNOWN/SEARCH_LIMIT, retained by the consumer without authorization. Normal cases use unchanged default limits. |

## Scenario, profiles and evidence meaning

The new fixture is a deterministic **synthetic** 7-by-9 flat grid, resolution
4 m, zero elevation/uncertainty, with no initial obstacles; it is not NASA terrain
or a claim that public Jezero uncertainty was reduced. Base is (6,14,0), goal
(30,14,0), current telemetry becomes (7,14,0), and cell (3,5) is blocked in map 2.
The one-metre interval is supplied test telemetry, not measured or dynamically
executed movement. D-07's separate actual 20 m polyline tests are reused unchanged.

Published `science_profiles.proposed.json` coefficients are unchanged. The
scientific context retains its proposed profile; only the test-local manager
profile copy is labelled illustrative, with explicit illustrative/model-agreement
flags to exercise the positive numerical audit. Negative tests retain the closed
model gate. No configuration file or production approval setting is changed.
The existing `mission_jezero.experimental.yaml` hash is context provenance reused
by the C2 test helper; it does not approve this synthetic geometry or budget.
The explicit inspect duration is 10 s, no waiting is declared. Initial budget is
1000 s / 100 metabolic Wh / 100 equivalent O2 L; reserves are 10 s / 1 Wh / 1 L.
These are software-test allocations, not approved physiological capacities.

JUnit properties retain actual initial/replanned/return paths, IDs, estimates,
remaining budgets and reserves for FAST/SAFE. The accompanying JSON records
source/configuration hashes and extracted traces. A feasible plan and manager
READY/RETURNING states never set `mission_success`; no work-completion or physical
traversal evidence is fabricated.

Actual predicted full-itinerary estimates in the new synthetic fixture:

| Candidate | Time s | Metabolic Wh | O2 L |
| --- | ---: | ---: | ---: |
| Initial, both modes | 67.602304 | 7.678134 | 1.567896 |
| Map-2 detour, FAST | 84.708789 | 9.662961 | 1.973203 |
| Map-2 detour, SAFE | 90.332564 | 10.315476 | 2.106448 |
| Explicit immediate base return, both modes | 1.200048 | 0.139239 | 0.028433 |

The supplied one-metre prefix costs 1.200048 s / 0.139239 Wh / 0.028433 L.
It is subtracted from availability once before replanning. Initial/replanned
estimates are alternative future predictions, not accumulated consumption.
The final return request occurs at the same supplied current pose, without
executing the detour or service. Its predicted unspent reserves can therefore
be higher than a full-mission prediction; current availability never increases.

## Validation and remaining integration

Exact current commands, outcomes and omissions are recorded in
`evidence/planner-mvp-pl01-local/validation.json`. Previous C2 benchmark and Jazzy
results remain historical at their own source revisions. This run does not
repeat a performance study or claim improved latency.

| Current check | Passed | Failed/errors | Skipped |
| --- | ---: | ---: | ---: |
| New consumer cases, Windows | 12 | 0 | 0 |
| All planning, Windows | 465 | 0 | 0 |
| Full Python suite, Windows | 1236 | 0 | 22 |
| Jazzy planning/contracts/mission/unit | 1117 | 0 | 1 |
| Existing ROS mission/execution/estimated integration selection | 8 | 0 | 0 |
| Local web tests | 201 | 0 | 1 |

These selections overlap and must not be added together. Eight ROS packages
built; all six messages and two services were inspected. Repository and whitespace
checks passed; local web TypeScript/Vite build passed. Windows omissions include
ROS imports, unsupported symlink fixtures and an absent explicit external
snapshot; native's sole omission is that absent snapshot. Web's omitted test
requires an explicitly supplied external recorder package.

WSL initially failed to start with HCS/ERROR_NO_SYSTEM_RESOURCES, then succeeded
without configuration changes. The first integration collection used system
Python without httpx (one collection error, zero executed cases). Rerunning with
the pre-existing Linux environment resolved that environment issue: all eight
cases passed. No packages were installed. Native environments currently use
pytest 7.4.4, outside requirements-dev's >=8 range; Node is 24.18.1 versus the
pinned 24.18.0. Record these deviations; this is not a claim of an identical
locked CI environment. The native base selection emitted two JUnit property
format warnings; assertions and captured properties are retained.

The existing ROS checks were reused unchanged, with distinct meanings:

- Real MissionNode + real legacy planning service + synthetic MOCK inputs:
  service exclusivity, idempotency and the expected MODEL_NOT_AGREED rejection.
- Real public Jezero data/mapping/planner/recorder + MOCK mission and kinematic
  primary execution: authorization wait, movement/return, stop acknowledgement,
  continuous replanning and validated recorded package; estimated-policy case
  additionally tests a later SIMULATED contradiction and stale/duplicate input.
  Closing state is READY, with all agents IDLE, not scientific COMPLETE.

Those ROS flows use their existing illustrative legacy planner profile, distinct
from the proposed science profile and its independent sigma limit. They do not
demonstrate the scientific backend over the wire. Public reference data was not
used; the new evidence stores package hashes/summaries, not evaluator arrays.
Web results apply to this local checkout, not main's newer unmerged viewer code.

- Jesus owns context transport, package/runtime dependency review, authoritative
  state association, execution/stop acknowledgement and three-role integrated
  evidence. Scientific costs remain Python-only; ROS still selects legacy costs.
- David owns scientific profile/uncertainty/budget approval and evidence-backed
  service/wait consumption and mission success. Test flags are not that approval.
- Daniel owns public terrain/uncertainty/provenance compatibility. The existing
  public control still has sigma 2.5 m versus profile limit 1 m; the earlier
  UNKNOWN outcome is retained. This synthetic positive test does not resolve it.
- D-DEL-03 remains in force: this is local validation, not new delivery scope,
  a change to the frozen revision, E1/E2, D* Lite or operational certification.
  Full three-role scientific execution and its same-run replay remain separate
  acceptance gates. No successful unit/transport test closes them.

At delivery handoff, Jesus (David backup) must record organizer notification and
explicit endorsement of the exact package, preserving at least four hours or
the longer requested review margin. This local planner cut is not submission
readiness and does not supply that evidence or authorize external contact.
