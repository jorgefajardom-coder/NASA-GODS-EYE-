# F03.3-C2 final LOCAL admission/performance audit

Audited source afd6a281ab0c549332b8ac411e4b931ad1f33799, preserving
9c69980a308644a5d1632c1e24d7d45fb73de160 and the original F03.3 history.
Reference-only main7ad6050 was fetched; no remote implementation was incorporated.
No publication, PR action, merge, model coefficient, ROS contract, MissionManager
or backend activation is part of this cut.

## Confirmed defect and minimal fix

ReplanPolicy stored _remaining_floor before validating the pending scientific
context. Ten human/rover regression cases reproduced the defect: admit a valid
snapshot, reject a lower value with missing/mismatched context, then falsely
reject the original admitted availability as replenishment after context repair.
Before-fix failures are retained separately from final passing results.

Commit availability only AFTER complete applicable scientific context admission.
The earlier increase check still compares to the last admitted bound. Corrected
inputs retain STOP_REQUIRED/AWAITING_ROUTE_AUTHORIZATION; only a separately
authorized compatible route adoption clears invalidation. An actually admitted
reduction still prevents later increases, including admission at reserve boundary.
No costs/reserves are debited or reset by this change.

Reserve failure still issues immediate STOP_REQUIRED before planning. Legacy
depleted telemetry retains its old lower bound. Scientific availability below
reserves cannot form a valid immutable ResourceBudget/context, so this early
STOP does not admit its unvalidated availability. Correcting such a snapshot
still requires external route authorization; it does not restore movement.
No reserve, phase, service, progress or unjustified-increase predicate is relaxed.
This is a targeted availability-admission fix, not a new execution ledger.

## Benchmark protocol

Run scripts/benchmark_scientific_planner.py --repeats 10 --output NEW_PATH.json.
The committed run has 80 samples: two existing cases, two backends, FAST/SAFE,
ten independent fresh worker processes per combination. Backend/mode ordering
alternates across repetitions. Only plan_route is timed; imports, input validation
and context construction are outside the timer. Both worker types prepare the
same context for comparable setup. Cold geometry caches; unchanged SearchLimits
defaults: max_labels200000 / timeout2 seconds. No retries-to-success, higher
limits, profile changes, observations or sigma reduction are applied.

- Public control: data/sample/manifest.json and its owner-validated public terrain,
  four control points, 32x32 cells, 4 m grid; mission_jezero.experimental.yaml's
  exact primary human base/goal, 120 s inspect, resources and reserves. The sizing
  wait allowance is not an explicit pending interval, so it is not added. The
  existing estimated-prior mask policy is applied; the independent science/profile
  limit remains 1 m sigma while actual prior sigma stays 2.5 m. All cells remain
  unobserved. Neither private evaluator data nor new observations are loaded.
- Search control: existing flat D-07 9x18/3 m map, 39 m outbound, 4 s explicit
  inspect, source scientific human profile and C2's already-used synthetic
  allocation. No future obstacle is in this initial snapshot. This supplementary
  known-grid control does not substitute for the public case. Its fixed inputs
  are recorded in script/request/provenance; the scenario-file hash is a reference
  identity, not approval of synthetic control values.

Sources and hashes are in benchmark.json/validation.json. RSS is the OS process
high-water mark INCLUDING common imports and preparation, not isolated planner
heap. Additional high-water can be zero if planning never exceeds startup peak;
it is not a claim of zero allocations. Latencies are local computational samples,
not simulated mission time, physical costs, a real-time guarantee or a frozen
mission-execution benchmark under docs/benchmark_evidence.md.

## Results (milliseconds; memory in MiB)

| Case | Backend | Mode | p50 | p95 | Expanded | Max process RSS |
|---|---|---|---:|---:|---:|---:|
| Public Jezero | legacy | FAST |115.17|147.71|610|61.97|
| Public Jezero | legacy | SAFE |109.42|141.62|610|61.93|
| Public Jezero | scientific | FAST |111.32|142.72|610|62.09|
| Public Jezero | scientific | SAFE |106.93|124.48|610|62.12|
| Existing D-07 | legacy | FAST |4.89|5.95|28|61.04|
| Existing D-07 | legacy | SAFE |4.90|6.40|28|60.79|
| Existing D-07 | scientific | FAST |48.64|55.01|408|61.56|
| Existing D-07 | scientific | SAFE |48.54|53.63|408|61.55|

Each public combination: UNKNOWN/UNVERIFIED_CORRIDOR10/10; SEARCH_LIMIT0/10.
The610 expansions diagnose optimistic connectivity, not a successful scientific
A* route. No route cost/reserve metrics are available (null, not zero). Backend
timing differences here do not prove a faster scientific feasible search.

Each D-07 combination: FEASIBLE/FEASIBLE_UNDER_MODEL10/10; UNKNOWN0/10;
SEARCH_LIMIT0/10. FAST and SAFE have equal paths/resources in this open control.
Predicted total time97.603744150 s for both. Legacy energy11.373045536 metabolic Wh
and O2 4.103727890 L; scientific energy11.258501092 Wh and O2 2.299016536 L.
Separate required reserves are1 s /1 Wh /1 L; complete predicted resources fit.
Full remaining reserves, budgets, route IDs and every attempt are in benchmark.json.
Human metabolic Wh and ideal dry-equivalent oxygen are estimates, not measurements.

## Risks and recommendations

1. The admission defect is fixed locally; retain tests for both rejected and
   admitted reductions and the external authorization latch before publication.
2. Jezero cannot establish real-map feasible-search performance under the current
   sigma/profile mismatch. Daniel/David must resolve evidence/profile compatibility;
   do not increase max_sigma, synthesize observations or reduce uncertainty here.
3. On the known control, scientific h=0 expands14.6x more labels and takes about10x
   the median time. Default bounds were not approached in these samples, but this
   says nothing about larger or harder maps. A stronger admissible heuristic would
   need separate approval, proof and independent-oracle tests; it is NOT implemented.
4. Process RSS includes setup and host variation; no isolated peak-heap, CPU
   isolation, long-running warm-cache ROS service or physical-memory budget is proven.
5. The backend stays local/explicit. Dependency/context/science review by Jesus
   and David, full role/Gazebo execution, and separate organizer endorsement gates
   remain. This software audit does not establish submission readiness.

Exact current test outcomes and native-environment availability are recorded in
evidence/planner-f033c2-audit-local/validation.json; earlier C2 results remain
historical evidence at their own source revision.

Final validation: focused267 passed; Windows full1224 passed/22 skipped/one
existing warning; native Jazzy planning/contracts/mission/unit1105 passed/one
absent external snapshot skipped. Web201 passed/one skipped and build passed.
Eight packages built and six messages/two services inspected. WSL initially
failed before execution due to resources; retry after web completed succeeded.
Repository/whitespace checks passed. No full Gazebo/integration mission was run.
