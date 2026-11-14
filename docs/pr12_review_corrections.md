# PR12 technical-review correction audit

Review: [all ten observations, comment 6882884265](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/pull/12#issuecomment-6882884265).
Date: 2026-11-14. Branch: feat/planner. HEAD before/after edits remains
0215b724e375e1256aaf689573e52fda04ebacae; the uncommitted merge target is
4b72d309a4ff3d87650289b8367044cff16b915f. F03.4 commit 2d9f416 is preserved.
No commit, push, PR creation or merge into main is performed. This is a review
candidate, not an approved contract or operational acceptance.

The ground-Z fixture follow-up at the end of this document supersedes the two
height-consumer blockers below. The preceding test counts remain the preserved
pre-fixture-correction record; do not substitute them for the follow-up results.

## Authorized local merge commit cut (2026-11-14)

The owner subsequently authorized one LOCAL merge commit with parents 0215b724
and 4b72d309, including the ten review corrections and ground-Z test fixtures.
The historical uncommitted status below and in raw validation reports describes
the tested source cut. The resulting commit is identified by Git history; source
hashes remain the evidence link without embedding a circular self-commit ID.
Commit preparation evidence includes the complete included-file inventory.
The fresh Windows suite again passed 843 tests with 16 omissions; web tests and
build were rerun. ROS outcomes below are the preserved executions on identical
source hashes, not a new ROS execution during commit preparation.
Replay is still failed and outside this correction; accepting this local commit
does not approve integration, freeze contracts or authorize motion. Fixture-only
changes still need Jesus's review; scientific/tolerance decisions remain David's.
Production simulation, mission, gateway and ROS definitions match the main merge
parent. No push, PR creation or merge into main is authorized by this cut.

## Reproduction and resolution of each observation

The pre-correction core/replan files were materialized from 0215b724 under ignored
tmp/before_planning, imported under a separate package name and probed without
changing current sources. Results: evidence/planner-pr12-review-20261114/before.json.
The planner production files are unchanged between that HEAD and the merged main
input, so these probes isolate the reviewed defects after synchronization too.
Inputs are small synthetic public grids and illustrative profiles, not NASA
measurements. The local probe script remains tmp/pr12_before_probe.py.

Each R-number below maps to tests/planning/test_pr12_review.py. Existing policy,
continuous-start and D-07 regressions remain enabled, with explicit opt-in where
they exercise the experimental extension.

| Review | Reproduced symptom and cause | Correction | Regression evidence |
| --- | --- | --- | --- |
| R1: dimensions / target height | SERVICE with a 2-D goal raised ValueError from math.dist; full 3-D comparison also mixed target annotations with surface height. | Goal/base arrival and leg-end comparisons use XY; live pose is still 3-D. | test_r1_goal_and_base_are_horizontal_targets: human/rover, SERVICE/RETURN, 2-D/3-D targets on z=5 terrain (8 cases). |
| R2: initial z | On flat z=5 terrain, supplied z=0 gave FEASIBLE at a centre and NO_PATH off-centre. The centre discarded z while the connector used it as altitude. | _start_z_mismatch applies one known-ground consistency rule: explicit z must match within 1e-6 m; otherwise ERROR/INVALID_START_Z. Two-dimensional starts infer belief z. No projection, and unknown/inadmissible cells retain terrain diagnostics. | test_r2_ground_z_rejection_is_uniform_and_never_path_impossibility (4 human/rover centre/continuous cases), plus existing unknown/sigma/NoData regressions. |
| R3: stuck candidate start | A 0.1 m local height update produced UNKNOWN/CANDIDATE_START_MISMATCH even while stationary. The candidate used new surface z but state retained old z. | Incoherent pose yields latched UNKNOWN/INVALID_START_Z before search. A coherent pose triggers surface revalidation; candidate horizontal identity is checked separately. No XY/Z teleportation to escape stale telemetry. | test_r3_stationary_height_change_requires_coherent_pose_then_recovers, human/rover; exact new start retained and authorization still invalid. |
| R4: permanent search-limit cache | Forced SEARCH_LIMIT followed by a TICK at 10 s made only one planner call and stayed AWAITING_ROUTE_AUTHORIZATION. | Retain a retry context; default two retries after the initial attempt, separated by min_interval_s. Exhaustion explicitly stops. Changed context can start a new bounded attempt; safety validation/DANGER precedes scheduling. | test_r4_search_limit_retries_are_delayed_bounded_and_recover (recovery/exhaustion), test_r4_danger_bypasses_waiting_search_retry. SEARCH_LIMIT is injected deterministically; actual core limit tests remain separate. |
| R5: opt-in contract | Default Python planning accepted an off-centre start; service inspection showed no separate extension gate. | Python allow_continuous_start=False and ROS startup allow_continuous_starts=false. The independent policy explicitly opts in; no shared field changes. | test_r5_core_baseline_rejects_continuous_start_without_opt_in; actual Jazzy test_ros_continuous_start_extension_requires_explicit_opt_in checks disabled/enabled service starts. |
| R6: unfinished SERVICE fallback | A primary service+return budget failure returned STOP_REQUIRED/BUDGET_EXCEEDED in SERVICE without trying affordable direct return. | Existing contingency path also applies during unfinished SERVICE after NO_PATH/INSUFFICIENT_BUDGET; same pose/map/remaining resources, zero abandoned service. | test_r6_service_can_be_abandoned_to_fund_contingency_return, human/rover: primary fails, direct base fits, exact future costs, unchanged budget, RETURN proposal. Existing OUTBOUND detour/no-escape/unknown cases remain. |
| R7: depleted reserves | Constructing live availability below energy reserve raised ValueError, preventing a safe policy decision. This is a valid ResourceBudget admission invariant. | New RemainingResources type represents finite nonnegative live availability. Policy checks immutable reserve values and each resource before conversion; below reserve yields explicit STOP_REQUIRED without a planner request. ResourceBudget is unchanged. | test_r7_depleted_live_resources_stop_before_creating_search_budget (human time/energy/O2; rover time/energy) and test_r7_admissible_live_resources_convert_without_debits. |
| R8: repeated work | Six evaluations performed six raster hashes and seven geometry builds including search. | Snapshot-identity hash reuse plus bounded GeometryCache shared by policy and planner; distinct snapshots are rehashed and same-version changed content invalidates. Profile/optimistic variants have separate entries. | test_r8_cache_reuses_hash_and_geometry_and_rechecks_distinct_same_version: same six evaluations now one hash/build; test_r8_geometry_cache_does_not_reuse_a_different_profile_or_snapshot. Counts are not a latency benchmark. |
| R9: clearance disagreement | An edge at exactly zero obstacle bound was accepted by the core but CORRIDOR_BLOCKED in policy. Graph code clamped negative margins. | Shared _segment_clearance for edges/connectors/policy, strict rejection of nonpositive obstacle bounds; vectorized stationary-point bound follows the same rule. Boundary tangency remains allowed. No FAST/SAFE algorithm changes. | test_r9_one_clearance_rule_rejects_exact_zero_obstacle_margin and test_r9_stationary_path_uses_same_strict_obstacle_contact_rule. The broader reviewer-reported random search was not rerun or claimed reproduced. |
| R10: stale deferred deviation | A deferred deviation launched CORRIDOR_DEVIATION at 10 s even after the pose recovered. | Drop the conditional pending deviation when below exit threshold; keep task notifications until processed. | test_r10_deferred_deviation_is_dropped_but_task_notification_is_retained; updated existing spatial/temporal hysteresis regression. |

## Executed validation before the ground-Z fixture follow-up

Final command results and source hashes are recorded in
evidence/planner-pr12-review-20261114/validation.json and its JUnit files.
No skipped test is a pass. Earlier synchronization results are historical in
[planner_pr12_sync.md](planner_pr12_sync.md).

| Completed check | Exact result |
| --- | --- |
| Windows complete Python suite | 819 passed, 0 failed, 16 skipped; one existing Starlette/httpx deprecation warning. Includes all 228 planner cases. |
| D-07 + F03.4 + review regressions | 114 passed: 9 D-07, 74 existing policy, 31 review cases. |
| Jazzy contracts / mission / unit | 506 passed, 0 failed, 1 skipped. Includes both actual ROS continuous-start gate cases. |
| Extended ROS CI / real consumers | 604 passed, 3 failed, 1 skipped; one existing Starlette/httpx warning. |
| Build and interfaces | All 8 ROS packages built; 6 messages and 2 services inspected. |
| Web | 84 passed; TypeScript/Vite production build passed. |
| Repository and whitespace | check_repository.py and staged/unstaged git diff --check passed after evidence creation. No unmerged index entries or conflict markers remain. |

Windows omissions: twelve ROS-dependent modules, three symlink-privilege cases,
one explicitly materialized external planner snapshot absent. Jazzy omits only
that external snapshot. Node used 24.18.1, npm 11.16.0; .nvmrc pins 24.18.0, so
this is not an exact patch-version reproduction of the web CI. Dependencies were
already available; none were added during these corrections.

### Historical blocking integration results before the fixture follow-up

1. test_recorded_run_is_readable_without_backend (test_replay_package.py):
   timeline has 6 records while manifest declares 5, plus snapshot-history
   inconsistency. The test uses the MOCK planner, so current core/node changes
   cannot cause its route calculation. This repeats the pre-correction failure.
   Recorder, validator and integration fixture match origin/main unchanged.
2. test_planner_routes_inside_the_observed_block (test_terrain_batch.py):
   ERROR/INVALID_START_Z rather than FEASIBLE. This is a new compatibility failure
   caused by the strict uniform guard, not an environment/dependency skip.
3. test_simulated_observation_replans_on_the_new_map_version
   (test_vertical_terrain.py): BLOCKED/INVALID_START_Z after the map update.
   Also a new compatibility failure from the uniform guard.

The two real-terrain consumers send legacy ground start z=0 while belief height
differs. They and their assertions are unchanged. These failures are retained,
not reclassified as expected passes. Integration must not be approved or the
merge committed on this result.

Jesus/David must choose a coherent contract before resolving those failures:
retain strict supplied-pose z and make producers provide a matching, known-ground
pose with reviewed tolerance; or define an explicit uniform surface-projection
interpretation for z, including provenance, safety limits and consumers. A
projection is not permission for an unmodelled physical vertical motion. No
unilateral consumer change, special-case z=0 bypass or silent projection is added.

The three real-MissionManager transport cases did pass in this same run:
test_real_mission_is_the_only_goal_and_route_authority,
test_actual_planner_candidate_is_blocked_without_model_agreement and
test_changed_payload_cannot_reuse_real_mission_request_id. This is actual manager
and actual planner with MOCK terrain/agents and an unapproved model, so the expected
scientific outcome is blocked. It does not establish an accepted cost-agreed
mission or F03.4 event wiring. No missing ROS dependency remains in these runs.

Commands use fresh ignored basetemp paths and preserve JUnit XML:

```sh
python -m pytest tests/planning/test_pr12_review.py tests/planning/test_replan_policy.py tests/planning/test_d07_twenty_metres.py -q -p no:cacheprovider --basetemp=tmp/pr12-review-focused --junitxml=tmp/pr12-review-focused.xml
python -m pytest -q -p no:cacheprovider --basetemp=tmp/pr12-review-final-full --junitxml=tmp/pr12-review-final-full.xml
python scripts/check_repository.py
git diff --check
# web, existing dependencies and pinned major Node 24:
npm test
npm run build
```

Jazzy Ubuntu 24.04 uses /opt/ros/jazzy and the existing isolated HTTP-test venv,
colcon --symlink-install with build/install/log paths under tmp, then sources
the install. It inspects six messages and two services and executes:

```sh
python3 -m pytest tests/contract tests/mission tests/unit -q -p no:cacheprovider --basetemp=tmp/pr12-review-jazzy-tests --junitxml=tmp/pr12-review-jazzy-tests.xml
tmp/pr12-linux-venv/bin/python -m pytest tests/contract tests/mission tests/unit tests/contracts/test_gateway.py tests/integration -q -p no:cacheprovider --basetemp=tmp/pr12-review-ros-ci --junitxml=tmp/pr12-review-ros-ci.xml
```

The local scripts tmp/pr12-review-ros-checks.sh and tmp/pr12-review-ros-ci.sh
capture sourcing, paths and environment. WSL initially failed before execution
with HCS/ERROR_NO_SYSTEM_RESOURCES; a later plain startup succeeded, followed by
an eight-package build and real ROS checks. No system restart, process killing,
global installation or weakened guard was used.

## Integration and science decisions still required

- Jesus: approve continuous-start opt-in semantics, strict known-ground z and
  coherent pose association. A DEM update with unchanged telemetry intentionally
  invalidates rather than projecting the agent. Decide RETURN phase transport,
  service abandonment, retry ticks/adoption and physical stop acknowledgement.
  MissionManager, not this policy, owns authorization/phase transitions.
- David: approve z/model interpretation, tolerance, uncertainty/radius assumptions,
  budgets/reserve semantics and retry/corridor thresholds. MODEL_NOT_AGREED and
  MODEL_MISMATCH remain intact; existing search and science models are not declared
  equivalent. No approved operational mission is established here.
- Immutable TerrainGrid arrays must remain read-only. The fast path does not
  defend against a caller deliberately resetting NumPy flags and mutating the
  same object. Distinct snapshots are fingerprinted even at the same map version.
- Full pending-route validation remains synchronous and proportional to segments.
  The cache does not establish 200x200 throughput, deadlines or physical clearance.
- ROS wire definitions and MissionManager implementation are unchanged. F03.4 is
  still a pure Python candidate policy, not wired to real mission events. Core and
  service tests demonstrate software behavior, not motion, Gazebo or LIVE acceptance.
- Replay closure failed twice before these corrections on main-owned code; the
  current run is reported separately. Recorder/fixture/validator ownership remains
  with Jesus; no integration assertion is relaxed to obtain a green run.

Mandatory AI generation/use declarations are in AI_USAGE.md and ai_usage.json;
no optional AI authorship or co-authorship is introduced.

## Files changed by these corrections

- Runtime: src/mge_planning/mge_planning/core.py, replan.py and node.py.
- Tests: tests/planning/test_pr12_review.py, test_continuous_start.py,
  test_d07_twenty_metres.py, test_kernel_guards.py, test_replan_policy.py;
  tests/contract/test_planner_service.py. Existing acceptance cases explicitly
  opt in; no integration assertions were changed.
- Documentation: README.md planner summary only; src/mge_planning/README.md and
  MODEL.md; docs/ICD.md proposed extension only; docs/replan_policy.md,
  planner_handoff.md, planner_pr12_sync.md and this audit.
- Required disclosures: docs/AI_USAGE.md and docs/ai_usage.json.
- Actual review evidence: evidence/planner-pr12-review-20261114.

The additional staged paths in git status are incoming main changes from the
uncommitted merge, not edits to other owners made by this correction. In
particular src/mge_mission and src/mge_interfaces match origin/main exactly.
tests/integration also matched main at the preceding review cut; the authorized
ground-Z fixture-only changes below are now proposed for Jesus's review.
.vscode remains untracked and untouched; .venv, tmp and web
build output are ignored. There are no unmerged index entries, but MERGE_HEAD
still exists: the synchronization has not been committed or published.

## Ground-Z fixture follow-up (2026-11-14)

Scope: the owner authorized correcting simulated initial conditions and test
request preparation, not changing production providers, MissionManager or wire
semantics. The prior ten corrections and strict INVALID_START_Z guard are
unchanged. This is a cross-module test proposal for Jesus (integration owner),
with David retaining scientific/model approval. No new synchronization, commit,
push or merge completion is performed.

### Root causes and vertical frame

- tests/integration/test_terrain_batch.py, Probe.plan(): the loop assigned only
  Point.x/y, leaving Point.z at the generated ROS default 0.0. This is a newly
  created synthetic rover request, not a measured rover altitude.
- tests/integration/test_vertical_terrain.py, Stack.__init__(): the launch used
  src/mge_bringup/config/agents_jezero.yaml, whose explicitly labelled placeholder
  HUMAN/ROVER entries omit z_m. src/mge_sim/mge_sim/mock_agents.py,
  MockAgents.publish(), uses a.get('z_m', 0.0). MockMission.request_plan() correctly
  forwards AgentState.pose.position as start; it is not the source of the error.
  These are static MOCK poses; the provider explicitly claims no locomotion or
  perception. Neither that provider nor either mission implementation is patched.

The public loader/data_node/mapping_node retain the same raster elevations,
row-major south-to-north order, 4 m cells and origin (-64,-64), in map (east,
north, up; metres). data/sample/manifest.json declares MOLA topography /
DeltaGeoid (Mars 2000 Sphere, R=3396190 m), with no Earth datum conversion.
No local z offset is defined or subtracted by this fixture. At row12/col12 the
public value is -2571.199462890625 m; row13/col12 is -2571.32958984375 m.
A ROS-default 0.0 is thus inconsistent with this declared ground scene. A real
z=0 is not inherently missing or invalid: the new regressions accept it on a
zero-height surface and preserve/reject it explicitly on an incompatible one.

### Minimal test-only correction

1. Probe.plan() now prepares new synthetic points from a coherent batch's known
   rover mask and finite belief height at the requested XY. Unknown-map tests
   supply z=0 explicitly, preserving UNKNOWN rather than fabricating a height.
   The known-map ROS test first confirms that explicit incompatible z=0 still
   returns ERROR/INVALID_START_Z, then checks the valid start height and route.
2. Stack builds a temporary agents_file for this one test run, using the existing
   launch argument. Only absent z_m values for HUMAN/ROVER are initialized;
   explicit z values, XY, drone entries and resource budgets are preserved.
   Base/goal annotations use the same declared scene surface. The checked-in YAML
   and the production MockAgents and launch implementation remain unchanged.
3. tests/integration/ground_fixture.py defines the fixture's initial SIMULATED
   scene using exactly the same prior-repeating observations that this test later
   sends. It reuses public loading and fuse_observation, making only that explicit
   observation footprint known in the private TEST scene. It is not a projection
   of physical telemetry and does not infer a height from an unobserved belief.
   The real ROS mapping node still begins unobserved at version1 and returns
   UNKNOWN until it receives those observations. The test checks that sensor
   values and scene values agree; no hidden evaluator raster is accessed.

simulated_ground_point accepts XY initial conditions only, refusing existing XYZ
poses, unknown/forbidden cells, NoData and invalid uncertainty. It preserves XY,
does not search for another cell and never changes an explicitly supplied z.
This is an initialization helper for the labelled static MOCK scene, not a
production terrain-following policy. It is not a validated surface estimate or a
scientific observation of Mars.

### Changed files and regression coverage

- tests/integration/ground_fixture.py (new): strict known-scene initial positions,
  copied fixture configuration and explicit SIMULATED scene preparation.
- tests/integration/test_terrain_batch.py: synthetic request preparation and
  stronger valid/invalid-z assertions in the original rover acceptance case.
- tests/integration/test_vertical_terrain.py: temporary agents_file, consistent
  base/goal annotations, observation/scene equality and exact starting-z assertion.
- tests/planning/test_simulated_ground_initialization.py (new): 24 ROS-free cases,
  including human/rover, centred/continuous starts, valid and incompatible z,
  valid zero-height ground, unknown finite prior, NoData, sigma, forbidden cells,
  stale pose after a map-height update, coherent new initialization, no mutation
  of an existing pose/configuration, and public datum/footprint checks.
- This audit, docs/planner_handoff.md and mandatory AI_USAGE.md / ai_usage.json.
- New evidence directory: evidence/planner-pr12-ground-z-20261114. Previous
  evidence/planner-pr12-review-20261114 outputs are preserved, not overwritten.

All planner runtime files retain their preceding audited hashes. Continuous
starts stay opt-in and disabled by default in the ROS service. Shared ROS types,
MissionManager, recorder, manifest/snapshot writers and replay test assertions
are unchanged. This fixture patch does not approve any production interpretation
of missing z or change agent telemetry when a map height changes.

### Follow-up validation and remaining decisions

Executed results and source fingerprints are recorded in the new evidence
validation.json and JUnit files. Unexecuted/omitted checks are not passes.
The Windows full suite passed 843 cases with 16 omissions and one existing
Starlette/httpx warning. D-07/F03.4/PR12/Z regressions: 138 passed, including all
24 new Z cases. Initial WSL attempts failed before executing tests with
HCS/ERROR_NO_SYSTEM_RESOURCES. The owner explicitly authorized a temporary
.wslconfig (3 GiB RAM, 4 GiB swap at D:\\Temp\\mge-pr12-wsl-swap.vhdx).
WSL then started; neither repository nor distribution storage was moved.
The complete two-file ROS fixture scenario passed 11 tests, including both
original height failures, the unknown-map rejection and unchanged recorded
package consistency assertions. The temporary .wslconfig was removed after its
hash was verified; the unique swap file was removed after distributions stopped
and exclusive file access was verified. Both paths are confirmed absent,
restoring their original state. No distribution was stopped by this cleanup.
The prior failed ROS startup attempts are not passes.

| Follow-up check | Actual result |
| --- | --- |
| New ROS-free ground initialization regressions | 24 passed, 0 failed/skipped. |
| D-07 + F03.4 + PR12 + new ground-Z | 138 passed (9 + 74 + 31 + 24); no failures/omissions. |
| Complete Windows Python suite | 843 passed, 0 failed, 16 skipped; includes 252 planner cases and 284 Python mission cases. |
| Two complete ROS terrain fixture modules | 11 passed, 0 failed/skipped, including both original Z failures. |
| Jazzy contracts / mission / unit | 506 passed, 0 failed, 1 external planner-snapshot omission. |
| Extended ROS CI / real MissionManager consumers | 606 passed, 1 failed (replay only), 1 external snapshot omission. |
| Build and interface inspection | All 8 packages built; 6 messages and 2 services inspected. |
| Repository and whitespace | check_repository.py and staged/unstaged diff --check passed. |

The full runs are overlapping selections, not additive independent test counts.
Windows omissions remain 12 ROS-dependent modules, 3 unavailable symlink
privileges and 1 absent external snapshot. Full Windows/extended ROS retain the
existing Starlette/httpx warning. Web source is unchanged; its prior 84-test/build
result is historical, not a new web execution in this fixture-only follow-up.

Status of the three original failures in the extended ROS run:

- test_planner_routes_inside_the_observed_block: PASSED. Also verifies rejection
  of explicit incompatible zero and the exact nonzero surface starting z.
- test_simulated_observation_replans_on_the_new_map_version: PASSED. Replans on
  version2 from the initialized static MOCK pose; the first map remains UNKNOWN.
- test_recorded_run_is_readable_without_backend: FAILED again, with timeline6
  vs manifest5 and snapshot-history inconsistency, matching the preceding failure.
  Recorder/writers, validator and that replay fixture remain identical to main.
  The complete run has no additional failed case. This does not close replay or
  establish that it is solely a fixture defect; Jesus must diagnose closure.

All three actual-MissionManager transport cases passed again, including sole
authority, blocking a real planner candidate without model agreement and rejecting
changed payload reuse. They use MOCK terrain/agents and do not establish an
accepted cost-agreed mission. The standalone ROS service also retains both
default-off/explicit-opt-in continuous-start checks. No production guard changed.

Reproduce after sourcing the existing Jazzy workspace and HTTP-test environment
with fresh basetemp/output names (the two terrain modules have ordered scenarios):

```sh
python -m pytest tests/planning/test_simulated_ground_initialization.py -q
python -m pytest tests/planning/test_d07_twenty_metres.py tests/planning/test_replan_policy.py tests/planning/test_pr12_review.py tests/planning/test_simulated_ground_initialization.py -q
python -m pytest -q
python3 -m pytest tests/integration/test_terrain_batch.py tests/integration/test_vertical_terrain.py -q
python3 -m pytest tests/contract tests/mission tests/unit -q
python3 -m pytest tests/contract tests/mission tests/unit tests/contracts/test_gateway.py tests/integration -q
python scripts/check_repository.py
git diff --check
git diff --cached --check
```

Exact local commands, JUnit, source hashes, temporary environment authorization
and restoration are in evidence/planner-pr12-ground-z-20261114. The executable
local scripts tmp/pr12-ground-ros-focused.sh, pr12-ground-ros-checks.sh and
pr12-ground-ros-ci.sh preserve paths/environment. They are ignored, not delivery
code. A future ROS run may need fresh host resources; no persistent WSL setting
was left in place.

Jesus: review these fixture-only changes and the unchanged replay closure defect;
no external notification or PR comment is posted automatically. David: retain
review of strict production z tolerance/datum association and scientific models.
Actual agent localization, Gazebo terrain placement, dynamic pose updates after
changed map heights and F03.4-to-MissionManager wiring remain separate acceptance.
No automatic physical projection, operational readiness or approved model is
established by initializing this static test scene.
