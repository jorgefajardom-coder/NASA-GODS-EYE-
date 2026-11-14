# Continuous recovery and recorded replay handoff

Source inputs: main `5ab1387`, Jorge's PR19 `9ef42ff` (web tree identical to
`82f9108`). This correction retains that PR's original history. The pull request
targets main and depends on PR19; it does not merge PR19 or approve its unrelated
visual changes. The correction commits isolate recovery and replay validation.

## Baselines and behavior

ROS ICD-ROS2-V1/package 1.0.0, gateway/replay 1.0.0, public rasters
`mge-public-rasters-1.0.0`, baseline review 1.0.0-rc.1 (not frozen).
No message/service fields, units, enums or raster layouts change. Strict web
validation implements the existing Python oracle's package contract.

The default planner still rejects continuous starts. Experimental recovery uses
`allow_continuous_starts:=true` in `vertical_mock.launch.py`. Human/rover starts
retain exact XYZ and need a directed, profile-bounded connector to the containing
cell centre, with full swept geometry and resource costs. Centred starts retain
strict height consistency; goals/base stay centred; drone extension is unavailable.
The opt-in does not approve physical terrain contact or scientific coefficients.

The kinematic MOCK launch requires fresh map-frame primary AgentState feedback
after invalidation: HALTED/IDLE, finite XYZ and zero linear/angular velocity.
While waiting it discards pending answers and cancels retries; missing feedback
blocks with STOP_ACK_TIMEOUT. Planning freezes that pose, debits observed resource
consumption from the original goal allocation and retains reserve requirements.
Changed pose during search or a candidate with another start cannot be authorized.

The web file loader requires the closing snapshot. It rejects wrong record/event
counts, conflicting route content under one route ID, raster versions without
recorded TerrainMeta, mismatched final state/history and evaluator content. Late
events, states lagging map delivery and pre-map version0 remain valid. The legacy
flat MOCK fallback is still visibly illustrative, never recorded terrain.

## Consumer validation

Run the repository Python/static suites and web test/build commands. On Ubuntu
24.04/Jazzy build all packages, inspect the six messages/two services and run:

```sh
python -m pytest tests/contract/test_mission_launch.py tests/contract/test_mock_recovery.py tests/integration/test_vertical_execution.py -q
python -m pytest tests/contract tests/mission tests/unit tests/contracts/test_gateway.py -q
python -m pytest tests/integration -q
```

Use a dedicated ROS_DOMAIN_ID and retain each run under a fresh evidence path.
The actual execution fixture prepares public Jezero initial heights explicitly,
publishes labelled SIMULATED observations and passes the experimental opt-in.
Acceptance requires acknowledged stop, exact stopped XYZ in the new v3 route,
independently checked 3-D costs/reserves, reauthorized motion, return and an
offline package that converts READY. No assertion treats a candidate as motion.

From web, set `MGE_REPLAY_PACKAGE` to the exact closed recorder package directory
and run `npm test`, followed by `npm run build`. The optional external-package
case verifies unchanged frames/events/prior and exact per-version rasters;
autocontained corruption regressions always run in CI.

Validation results and the tested source commit are recorded in the PR. Local
raw logs/JUnit and closed packages stay under ignored `.local/`; past failed
evidence is preserved. No evaluator reference belongs in the public package.

Local validation before publication: Windows 961 passed/20 environment skips;
web 160 passed including the newly recovered recorder package, and build passed.
Jazzy built 8 packages and inspected 6 messages/2 services; the focused recovery
selection passed 31 cases, contract/mission/unit/gateway passed 686 with one
optional external-snapshot skip. Full integration passed 46 cases and exposed
one missing insufficient-budget diagnostic; after preserving the complete failed
RouteDecision, its full MOCK vertical and recovery contracts passed 18 cases.
The final PR CI must rerun the complete combined source. Earlier failures remain
in `.local/recovery-validation-1/`; the recovered package ends READY on map3
with a feasible route and recorded return, not scientific mission COMPLETE.

## Remaining real acceptance

Jesus reviews the MOCK stop/authorization loop and Jorge the existing consumer.
David/Diego retain review of the bounded continuous model and resource agreement.
The real scientific MissionManager's model gates are unchanged. This cut does
not implement D-EST-01, independent rover/drone tasks, physical/Gazebo validation
or a three-role COMPLETE mission. Next deliverable is reviewed integration of
these corrections and the same-run consumer proof, followed by those open tasks.
