# Diego's planner handoff

F-TERRAIN-02 is LOCAL ONLY on the terrain experiment branch. See
planner_terrain_mobility_f02.md and evidence/planner-terrain-f02:76 new synthetic
cases and full1344 passed/22 skipped. Unmodified A* runs on an explicit complete
fine synthetic surface; original step/slope/resource gates remain. Only its
returned filtered evaluation_grid can be used for subsequent policy checks.
Measured/orbital runtime providers, physical evidence and owner approvals remain
blocked. No ROS activation, frozen-delivery change or publication.

MVP-PL-01 local validation over d81407de: actual scientific Python A* candidates
are now exercised against the unchanged real MissionManager in twelve synthetic
consumer cases. FAST/SAFE, explicit inspect, directed return, remaining resources,
map invalidation, continuous restart, stale identities, model gates and bounded
failures are covered. See planner_mvp_pl01.md and evidence/planner-mvp-pl01-local.
Fetched main7ad6050 contains PR33; no new Python/ROS consumer changes were found,
and no merge or frozen-baseline/runtime activation was performed. The owner
reports Jesus/David's C2 technical review closed; scientific parameter approval,
ROS context transport, full role execution and organizer endorsement remain
separate. Test-local illustrative admission does not approve production profiles.
Current results: new12, planning465 and Windows full1236 passed/22 skipped;
native Jazzy1117 passed/1 skipped, existing selected ROS integrations8 passed.
Eight packages/interfaces checked; repository and web checks passed. Native
pytest7.4.4 and Node24.18.1 deviate from declared/pinned versions; exact outcomes,
initial environment failures and remaining CI/mission gates are recorded in JSON.

Local final C2 audit: rejected scientific context/resource snapshots no longer
lower the admitted availability bound. Correcting inputs retains invalidation;
real admitted decreases still block replenishment. Default-limit cold-request
benchmark (80 samples) is in planner_f033c2_final_audit.md and its evidence folder.
Public Jezero remains UNKNOWN (sigma2.5 vs profile1); known D-07 search is feasible
but scientific h=0 expands408 versus28 labels. No runtime activation/publication.

Local F03.3-C2 continuation over PR33 source ffea8c2: ScientificContext is an
explicit Python-only opt-in, default legacy behavior preserved. Scientific costs
now participate in the actual search, connector and fixed goal-work transition,
with h=0 and unchanged FAST/SAFE/resource/geometry bounds. Policy takes an explicit
current pending context and preserves F03.3-A's latched monotonic resource guard.
See planner_f033c2_local.md and evidence/planner-f033c2-local. No push or PR update,
ROS activation, coefficient change, mission approval or submission readiness is
implied. Jesus/David retain dependency/context/science review and organizer gates.

F03.3 availability-guard review cut: based ONLY on published main0339bbd.
Local audit documents/disclosures were hash-backed up under ignored
tmp/f033-guard-backup, main was incorporated by fast-forward (no new commit),
and both local audit declarations and main disclosures were retained.
ReplanPolicy now rejects unexplained increases in remaining time, energy or
human O2 before a search or route adoption. It retains the lower admitted bound
through duplicate/stale events, reserve exhaustion and authorized route changes.
It never debits consumption; reserves and all existing phase/service/progress
checks remain. Corrected input keeps invalidation until a different externally
authorized route is supplied. A new mission needs a new policy instance; no
automatic reset or replenishment is supported. MissionManager/ROS/science models
are unchanged. See MODEL.md, planner_f033_resource_audit.md and the new guard
evidence for tests and caller/restart limitations. This working tree is not
committed or published.

Branch: **feat/planner**. Continue here; do not restart from the original scaffold.
Integration review: Jesus. Scientific profiles/mission acceptance: David.

Last computational run: code commit `6e4984d`, recorded in
[evidence](../evidence/planner-p0-20261114/README.md). 154 local tests passed;
ROS-only modules run in Jazzy CI. Read the latest PR checks before integrating.

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

Continuous human/rover starts now have a checked and costed connector to their
containing cell centre; see MODEL.md and tests/planning/test_continuous_start.py.
The first outbound point is the actual start, followed by the graph centre.
Goals/bases remain centred, and return from a continuous start requires an explicit
centred base. Replanning still needs an external request: no automatic event,
corridor or hysteresis policy was added. The historical 154-test evidence above
predates this extension; it must not be cited as verification of the new code.

Local verification of the continuous-start working tree on 14 November 2026
(Python 3.12.3): full pytest suite 184 passed, 2 ROS modules skipped, 0 failures;
114 planning cases include 30 new connector cases. Repository static checks passed.
The existing Starlette/httpx deprecation warning remains. Web tests: 2 passed;
web build unavailable because frontend dependencies (tsc) are not installed.
ROS compilation/service execution and mission E2E remain unverified here.

Profiles in config/planner_profiles.illustrative.json are not approved scientific
parameters. Speed/slope are tentative references recorded in
[data provenance](planner_provenance.md); energy, oxygen, footprint and other
values are invented illustrative assumptions. The
fresh CTX crop remains unverified orbital prior: loading it alone returns UNKNOWN.
Neither these tests nor its finite pixels prove EVA, flight or vehicle safety.

## Next dependency and takeover checklist

### D-07: explicit request after 20 metres

`tests/planning/test_d07_twenty_metres.py` closes the literal D-07 scenario at the
pure Python integration level for human and rover profiles. Its deterministic
9x18 flat grid has 3 m cells; the initial route runs from (4.5,13.5,0) to
(43.5,13.5,0), with return to the explicit original base. The test walks the
initial polyline for exactly 20 m and interpolates the last segment, yielding
(24.5,13.5,0), not a cell centre. It then blocks pending cell (row 4, col 10),
increments map_version from 1 to 2 and explicitly requests a new route.

Illustrative speed 2 m/s and energy rate 0.5 Wh/m consume 10 s and 10 Wh during
the prefix; the human oxygen rate 0.2 L/s consumes 2 L. These are test assumptions,
not approved scientific rates. Remaining availability subtracts ONLY this prefix;
reserves are unchanged and service is still pending. The new result includes
the 1 m connector, outbound detour, 4 s service and full return. Independent
polyline costing verifies totals and conservation across both planning requests.
An independent whole-segment intersection check against the inflated obstacle
square covers connector, outbound and return. The outbound cannot visit the old
origin or reduce x below the current pose in this scenario; only the return ends
at the base. Repeated requests preserve paths/route IDs, and old map versions
are rejected. Negative tests cover a full barrier and separate remaining time,
energy and human oxygen shortages, despite the original mission being feasible.

Reproduce locally (use fresh output paths to preserve previous evidence):

```sh
python -m pytest tests/planning/test_d07_twenty_metres.py -q -p no:cacheprovider --basetemp=tmp/d07-20m-focused-NEW --junitxml=tmp/d07-20m-focused-NEW.xml
python -m pytest -q -p no:cacheprovider --basetemp=tmp/d07-20m-full-NEW --junitxml=tmp/d07-20m-full-NEW.xml
python scripts/check_repository.py
```

Create the ignored `tmp` parent first on a fresh checkout. Each focused-test
temporary directory contains d07.json with the grid definition, both requests,
initial route, travelled prefix, consumed resources and final result. JUnit
records executed assertions. These are synthetic computational acceptance cases;
movement is polyline interpolation, not dynamics, perception, ROS/Gazebo or a
LIVE mission. D-07 alone does not establish F03.4. A ROS-independent event policy
is now implemented in replan.py; see [policy documentation](replan_policy.md).
MissionManager authorization and integration with actual pose/resources,
supervisor feedback and coherent published map snapshots remain pending.

Local execution on 14 November 2026, Python 3.12.3: focused D-07 tests 9 passed;
full Python suite 193 passed, 2 ROS modules skipped, 0 failures, with the existing
Starlette/httpx deprecation warning. Static repository checks passed. No production
planner code or ROS contracts changed for this acceptance extension.

### Team handoffs

F03.4 consumers must pass authoritative phase/cursor/remaining resources, preserve
candidate_phase=RETURN for single-leg base requests, and explicitly adopt new
routes. The policy never changes MissionManager state or commands physical stops.
During OUTBOUND or unfinished SERVICE, a failed primary mission (NO_PATH/INSUFFICIENT_BUDGET) now triggers
an automatic direct-base contingency evaluation with zero service and unchanged
remaining resources/reserves. primary_request/primary_candidate retain its cause.
Mission must authorize the feasible fallback and enact RETURN; see the policy
documentation for no-escape, unknown and immediate-stop semantics.
Audit guards: OUTBOUND cannot debit any original service; premature completion
returns UNKNOWN/OUTBOUND_SERVICE_MISMATCH without a search. EVENT_MAP_MISMATCH
always invalidates the active authorization, even on an otherwise unaffected path.

PR12 review follow-up: continuous starts are opt-in, disabled by default in both
the core and ROS service. Explicit ground z is checked uniformly against known
cell height; incoherent telemetry invalidates until corrected rather than being
projected. XY goal/base checks support 2-D and 3-D targets. RemainingResources
represents depleted live telemetry without weakening ResourceBudget; reserve
violations stop before search. SEARCH_LIMIT retries are delayed and bounded;
recovered deviations do not leave stale deferred searches. The graph, connector
and policy share clearance/contact rules and immutable-snapshot geometry caches.
See [all ten findings and current evidence](pr12_review_corrections.md). These
changes do not approve models or wire the policy into MissionManager.

Ground-Z integration follow-up: only the two affected integration fixtures now
prepare explicit static simulated ground positions in the public terrain's
existing vertical datum. Known rover request points use the coherent batch;
the vertical initializes a temporary agents_file from its declared SIMULATED
scene, preserving explicit z, XY, drones and budgets. ROS belief remains unknown
until observation. No runtime provider, mission, wire or INVALID_START_Z guard
is changed. The new ground_fixture helper is test-only, requires known scene
data and is not a telemetry projection or production missing-z convention.
Jesus reviews the cross-module fixture proposal and replay closure separately;
David retains scientific/datum/tolerance approval. See the audit's follow-up
section and evidence/planner-pr12-ground-z-20261114 for exact execution results.

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

Delivery revalidation against published main `b5dc681` (fast-forward, no new
commit): the intervening changes affect web/Pages and disclosures, not planner
code or cost models. Planning 309 passed; focused F03.3/F03.4/D-07 123 passed;
Windows suite 1025 passed / 20 skipped. Web 170 passed / 1 skipped; build passed.
Fresh Jazzy validation is blocked before execution by WSL
`HCS/ERROR_NO_SYSTEM_RESOURCES`; the earlier 946 passed / 1 skipped result is
historical, with unchanged guarded-source hashes, not a new integration pass.
See `evidence/planner-f033-delivery-20261114/validation.json` for the delivery cut.

This module-review cut is not submission readiness. Before final submission,
Jesus (David backup) must record local-organizer notification and endorsement,
allowing at least four hours or the longer requested local review lead time.
