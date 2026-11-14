# PR12 remote reconciliation and publication cut

## Final main synchronization

The owner authorized updating and merging PR12 after green validation. Reconcile
planner `a959d25` with main `3a9032b`, which includes PR17's callback scheduling,
replay corrections and MOCK executor. Preserve both histories and all mandatory
disclosures; the only manual conflicts are disclosure additions. The planner's
default-off continuous-start gate and main's separate map/service callback groups
are both retained. ROS messages, services and baseline versions are unchanged.

On this combined source, Windows Python validation passed 935 tests with 19
environment/optional-input skips and one existing Starlette/httpx deprecation
warning. ROS consumer validation runs in PR CI before merging. Historical replay
failures below remain evidence of earlier source cuts, not current failures;
software checks do not establish general recorder reliability or a LIVE mission.
Profiles, datum/tolerance, physical stop feedback and F03.4 mission wiring retain
their existing owner-review gates. The final PR description records the tested
head, CI run and consumer outcomes. Next deliverable: the reviewed merge to main.

2026-11-14. Branch: feat/planner. Owner-authorized normal merges and publication
to existing PR12; no force-push, history rewrite or merge to main.

## Preserved histories

Local reviewed source: 072608222b961644bd3d48549baced349be97131.
Remote planner: 38ad69215eaa4925c95f35b5355cbae9bec25bb2.
Their merge: 4cda3a5, retaining both parents. Remote reserve/request-goal/path
guards and all 14 added regressions remain alongside bounded retries, ground-z
guards, service opt-in, geometry cache and SERVICE contingency return. The code
conflict moved PHASE_ROLLBACK earlier while preserving _map_snapshot assignment.
No safety guard was discarded.

Fetched main: 7c16cd8. Includes David's mission/scenario work and scoped
experimental approvals, Jesus's public-raster recording and CI naming. Retain
these contributions without broadening operational/scientific approval.
Main's production mission, mapping, simulation, gateway and ROS definitions are
unchanged by planner edits. Ground-Z initialization remains test-fixture-only,
pending Jesus's review. Main's observed-mask/raster assertions are preserved.
Continuous starts remain disabled by default in the ROS service.

## Conflict resolutions

Remote planner: README, AI_USAGE, ai_usage.json, replan_policy.md and replan.py.
Retain the fuller tested capability summary, union mandatory disclosures and
both policy additions. Main: AI_USAGE and ai_usage.json; retain both sides.
No ROS field, type, unit or contract approval is changed here.

## Validation and limits

Exact counts, hashes and JUnit are in
evidence/planner-pr12-publish-20261114/validation.json. Preserve earlier evidence;
overlapping test selections are not additive, and omitted tests are not passes.
Run Python3.12 pytest tests/planning and full suite; existing Jazzy Ubuntu24.04
colcon build under tmp; inspect six messages/two services; pytest tests/contract,
tests/mission, tests/unit, tests/contracts/test_gateway.py and tests/integration;
check_repository.py; staged/unstaged diff --check; npm test and npm run build.
Local scripts tmp/pr12-publish-ros-checks.sh and pr12-publish-ros-ci.sh capture
environment and paths. No dependency installation or persistent WSL change.

Previous replay closure failures remain in historical audits. The CURRENT outcome
is recorded separately after integrating Jesus's implementation unchanged; no
assertion is weakened. Scenario software checks do not establish physical/LIVE
mission acceptance or universal recorder reliability.

Jesus owns integration/fixture/recorder review. David retains scope, datum,
tolerance and model decisions. F03.4 event/phase/resources wiring to mission and
supervisor remains pending; recommendations never authorize movement. .vscode
stays untracked; environments, tmp and build products are excluded.

## Completed results and publication gate

Planning266 passed; Windows924 passed/17 skipped; Jazzy contracts575 passed/1 skipped; extended ROS675 passed/2 failed/1 skipped. Web84 passed and build passed; eight ROS packages built. Both Z cases and actual MissionManager consumers passed.

Replay remains blocked: snapshot-not-yet-present and initial IDLE state0 inside a map1 envelope (STALE_STATE). Detached main ROS comparison:6 passed/1 failed (missing final event). Its raster case passed in that timing; a separate deterministic reproduction with exact main ReplayWriter/oracle and captured initial messages reproduced STALE_STATE before any planner invocation. These are main integration defects, not suppressed or repaired by this branch. Evidence preserves all failures, the baseline and reproduction. Overall ROS CI is not green; Jesus retains the fixes. The owner-authorized publication gate accepts satisfactory planner checks with identified independent integration blockers.

Final concurrency refresh found documentation-only main70cd2e5 (D-EST-01). Retain the accepted estimated-terrain scope and explicit coordinated-implementation/ICD review gate. This publication does not implement that new policy or claim it already supported. All tested source hashes match after the refresh. Prior unknown-first fixture behavior is historical/current implementation, superseded as a target scope by D-EST-01.
