# New P0 planner computational evidence

Code under test: `6e4984d38dd0083c014c353673b49781c5f1185b` on feat/planner.
Produced during the competition from the commands and code commit recorded here.

Commands:

```sh
python scripts/benchmark_planner.py --output evidence/planner-p0-20261114/benchmark.json --repeats 3
python scripts/check_planner_crop.py --output evidence/planner-p0-20261114/ctx_prior_check.json
```

The benchmark contains nine measured queries across seeds 7, 19 and 41. All
returned FEASIBLE and matched the independent flat-grid Dijkstra round-trip cost.
Observed p50/p95 are recorded in the JSON with configuration and environment;
they are not latency guarantees or evidence of real-world mission performance.

The fresh real CTX prior check returned UNKNOWN/UNVERIFIED_CORRIDOR with no route.
Finite orbital heights were deliberately not promoted to locally verified cells.
Profiles, budgets and synthetic benchmark obstacles are illustrative; final
science products and parameters require Daniel and David's review.

Separate local verification: 154 tests passed; two ROS-only modules skipped on
native Windows. The PR's Jazzy CI must additionally run the generated interfaces
and actual ROS service tests. Full mission E2E acceptance remains pending.
