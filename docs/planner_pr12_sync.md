# PR12 historical local synchronization audit

This records the earlier uncommitted synchronization cut. The owner later
authorized a local merge commit after the PR12 corrections and fixture review;
see [current audit and commit cut](pr12_review_corrections.md). The source SHAs,
test outcomes and no-commit statements below remain historical evidence.

Source planner branch: 0215b724e375e1256aaf689573e52fda04ebacae.
Fetched main / merge target: 4b72d309a4ff3d87650289b8367044cff16b915f.
The user subsequently requested NO commit and NO push. The merge remains local
and uncommitted; these results do not make the remote PR mergeable until an
explicitly authorized commit and push occur.

## Preserved behavior and resolution (before PR12 review fixes)

README and mandatory AI declarations were combined, preserving both contributions.
The ICD merged automatically: all main mission/timestamp/typed-serialization gates
and the explicitly unapproved continuous-start extension remain. No ROS wire types,
mission implementation or production planner changes were made.
Subsequent authorized planner review corrections are documented separately in
[PR12 review corrections](pr12_review_corrections.md); statements in this section
describe only the earlier synchronization, not those later source changes.

Main adds tests/__init__.py and pytest importlib discovery. The only technical
resolution changes the F03.4 test helper import from test_d07_twenty_metres to
 tests.planning.test_d07_twenty_metres. All assertions are preserved. The initial
collection error is recorded in tmp/pr12-sync-full.xml; the corrected runs follow.

## Executed checks

- Native Windows full suite: 788 passed, 16 skipped, 1 existing Starlette/httpx
  warning, 9.23 s. JUnit: tmp/pr12-sync-full-r2.xml.
- Planning, mission, contract and integration selection: 604 passed, 16 skipped,
  10.60 s. JUnit: tmp/pr12-sync-consumers.xml.
- Windows omissions: 12 ROS-dependent modules, 3 unsupported symlink fixtures,
  1 explicitly materialized external planner snapshot unavailable.
- Web: 84 tests passed; production build passed.
- Jazzy Ubuntu 24.04: all 8 packages built; 6 messages and 2 services inspected.
  Contracts/mission/unit suite: 504 passed, 1 missing external snapshot skipped,
  21.50 s. JUnit: tmp/pr12-jazzy-tests.xml.
- HTTP/WS test dependencies were installed in tmp/pr12-linux-venv with access to
  existing ROS system packages; the system Python installation was not modified.
  The extended ROS CI-equivalent run finished: 604 passed, 1 failed, 1 skipped
  (missing external snapshot), 1 existing warning, 119.61 s. JUnit: tmp/pr12-ros-ci.xml.
  The replay-only repeat failed again: tmp/pr12-replay-repeat.xml (15.31 s).

## Integration/science limits

MissionManager independently audits requests/poses/resources and preserves
MODEL_NOT_AGREED / MODEL_MISMATCH. Keeping these expected rejection paths is not
a behavioral regression or an authorization to turn off science gates. ReplanPolicy
remains ROS-independent; its proposals and RETURN phase need explicit mission
wiring/authorization. Physical stop acknowledgement, full-mission execution,
scientific model agreement and approval by Jesus/David remain pending.

No operational, LIVE, physical-navigation or approved-scientific capability is
inferred from the software tests. This local synchronization does not resolve
these scientific/ownership decisions or change the remote PR description.

## Blocking replay result: integration owner review required

`tests/integration/test_replay_package.py::test_recorded_run_is_readable_without_backend`
failed in both executions. First run: snapshot READY with last_event_seq=4, but
only events 1..3 recorded; MISSION_STATE_CHANGED sequence 4 was absent. Repeat:
check_package reported 6 timeline records while manifest declared 5, plus snapshot
history inconsistency. This suggests recording/shutdown synchronization; it is
not demonstrated to be solely a fixture or solely a production recorder defect.
The relevant recorder, writer, validator and integration test match main exactly.
No integration-owner source or assertion was weakened to obtain a green result.

Jesus should decide whether to strengthen bounded final-event/snapshot readiness
in the fixture, guarantee recorder draining/atomic final snapshots on shutdown,
and/or reject incomplete closure in the validator. Both actual failure packages
and JUnit reports remain under ignored tmp. No operational capability is inferred.
Real MissionManager authority/model-blocking and real planner route/replan tests
passed in that same run; this does not resolve model agreement or physical safety.

The user explicitly withdrew commit authorization during validation. No merge
commit or push is performed. Source HEAD remains 0215b724; target remains 4b72d309.
