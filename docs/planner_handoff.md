# Diego's planner handoff

Branch: **feat/planner**. Continue here; do not restart from the original scaffold.
Integration review: Jesus. Scientific profiles/mission acceptance: David.

## Implemented

- Pure typed inputs: TerrainGrid, MotionProfile, PlanRequest, ResourceBudget,
  SearchLimits and RouteResult. `plan_route(terrain=..., request=..., profile=...)`.
- Joint outbound/service/return resource-constrained FAST search and conservative
  bottleneck-maximizing SAFE. EFFICIENT and D* Lite are explicitly outside P0.
- Corners, profile slopes/steps, footprint/localization, unknowns, NoData,
  human oxygen, reserve checks, stale versions and bounded work.
- Actual `/mge/planner/plan_route` server with unchanged ROS wire definitions,
  strict immutable snapshot assembly, per-agent profiles and stale-result checks.
- New illustrative acceptance scenarios and three-seed benchmark generator.
- Fresh public CTX crop from upstream; a separate freshly processed HiRISE
  evaluator crop remains local/ignored and is never passed to the planner.

The full cost model, heuristic and proof boundaries are in
[MODEL.md](../src/mge_planning/MODEL.md). API fields/docstrings are the source of
truth for Python. ROS field/casing/NaN conversions are in adapter.py and ICD.md.

## Reproduce locally

From the repository root, after activating Python 3.12 with development dependencies:

```sh
python -m pytest
python scripts/check_repository.py
python scripts/benchmark_planner.py --output evidence/NEW_RUN/benchmark.json
python scripts/check_planner_crop.py --output evidence/NEW_RUN/ctx_prior_check.json
```

Use a new evidence directory every time; the scripts refuse artifact overwrite.
On this Windows session the restricted system temporary directory required
`--basetemp=tmp/pytest-planner-NEW_RUN` for the unrestricted HTTP-test execution.
The Linux CI environment uses normal pytest temporary directories.

Jazzy after colcon build and source install/setup.bash:

```sh
ros2 run mge_planning planning_node --ros-args -p profiles_file:="$PWD/config/planner_profiles.illustrative.json" -p allow_illustrative_profiles:=true -p snapshot_contract_confirmed:=true -p use_sim_time:=true
python3 -m pytest tests/contract -q
```

The illustrative opt-in is for tests only. The node has no data publisher;
without a coherent metadata/belief/sigma/mask batch it returns UNKNOWN. Publishers
must implement the unique-stamp protocol in ICD.md and repeat complete batches.
The ROS contract tests create their own explicitly synthetic publisher and client.

## Acceptance and current limitations

D-01..D-10 are covered by new controlled tests: independent Dijkstra, blocked
corner, unknown/known barrier, differing profiles, directed return costs, oxygen,
replanning from current cell centre, stale maps, FAST/SAFE and three seeded cases.
There is a resource-feasible alternative-path case so an expensive fastest route
cannot trigger a false global rejection. Tests also cover snapshot invalidation
and bounds. Whole mission R01-R18 acceptance is still pending.

Profiles in config/planner_profiles.illustrative.json are not approved scientific
parameters. Only tentative speed/slope references came from Sandbox; energy,
oxygen, footprint and other values are invented illustrative assumptions. The
fresh CTX crop remains unverified orbital prior: loading it alone returns UNKNOWN.
Neither these tests nor its finite pixels prove EVA, flight or vehicle safety.

## Next dependency and takeover checklist

1. Daniel supplies public belief/sigma/profile masks with unique batch stamps,
   approved CRS/datum and three matching control points. Do not expose reference.
2. David supplies reviewed rates, budgets, uncertainty limits and mission criteria.
   Replace the illustrative profile file; the search engine stays unchanged.
3. Jesus confirms batch delivery/retry and connects MissionManager's current-pose
   requests to the service. MissionManager alone invalidates/authorizes active paths.
4. Jorge consumes authoritative decisions and reasons, not an independent planner.
5. Record consumer/E2E results with run ID and source hashes. Optional-task
   allocation and multi-objective mission policy belong to the mission front;
   this service evaluates one goal plus service and optional required return.

Takeover command: fetch origin, switch feat/planner, pull --ff-only, read this
file, MODEL.md and latest integration_log.md entry, then run the checks. Keep
incremental commits and mandatory AI/provenance disclosures.
