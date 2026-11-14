# Real MissionManager service handoff to integration

Owner: David. Integration/review: Jesus. This PR starts from the published
`feat/mission` revision `8f69f62bb65f6fdd0151580901b81c22049dfaed` and incorporates
main `8afc7bfda5a012bdfe0f27ba876aedbd555540b2`. It preserves the real manager,
science models, task logic, ROS adapter and existing tests. At that main revision,
`mission_node` was still a startup placeholder without a SetMissionGoal server;
starting it could not replace `mock_mission`. Publication is the reviewed PR
head; do not call this change integrated into main before it is merged.

Read [AGENTS.md](../AGENTS.md), [ICD](ICD.md),
[baseline](CONTRACT_BASELINE.md), [mission handoff](mission_handoff.md) and
[model conformance](planner_model_conformance.md). ROS .msg/.srv are unchanged.

## Replace the provider without replacing its consumer

`vertical_mock.launch.py` keeps `mission:=mock` by default. Select
`mission:=real` to launch `mge_mission/mission_node` instead of
`mge_sim/mock_mission`; the conditions are exclusive. The existing gateway
continues calling `/mge/mission/set_goal` with `mge_interfaces/srv/SetMissionGoal`,
and consuming MissionState/MissionEvent/active Path. `planner:=real` independently
selects the existing PlanRoute producer. There must be only one provider for
each canonical service in the ROS domain. The selector rejects an existing
mission service instead of creating a second authority.

This remains an integration harness with static MOCK agents and synthetic
terrain. The real MissionManager is real software; it does not turn those
providers into NASA measurements, Gazebo execution or a verified LIVE mission.
Gateway carries authoritative state; it must not invent a replacement manager.

| Launch argument | Real-node parameter / requirement |
| --- | --- |
| `run_id` | Explicit run identity shared by mission, agents, map and gateway |
| `mission_profiles_path` | Forwarded to `profiles_path`; science/profile registry, not the planner's JSON profile file |
| `mission_path` | Explicit approved or deliberately illustrative mission YAML |
| `allow_illustrative` | Default false; enable only for a labelled illustrative test |
| `base_enu_m` | Explicit optional ENU override; no silent pose snapping |
| `use_sim_time` | Must be true, with an existing external `/clock` publisher |
| `model_agreement_confirmed` | Default false; retain while numerical conformance is unresolved |
| `approved_model_id` | Default empty; an identifier does not establish model agreement |
| `profiles_file` | Existing planner configuration; distinct from mission science profiles |

The real selector checks configuration files, simulated time and service
exclusivity. It does not create a clock, approve science profiles or supply
execution/discovery evidence. Use one launcher per run and a dedicated
`ROS_DOMAIN_ID`; a service-availability race still requires operational control.

## Build and inspect on Ubuntu 24.04 / ROS 2 Jazzy

Run from this PR checkout, with development dependencies installed:

```sh
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=84
colcon build --symlink-install
source install/setup.bash
ros2 interface show mge_interfaces/srv/SetMissionGoal
ros2 interface show mge_interfaces/srv/PlanRoute
ros2 pkg executables mge_mission
```

Use a separate, reviewed simulation-time source in the same ROS domain. Verify
that it is publishing `/clock` before launching; the real mission requires an
actual received clock, and fails closed on a backwards clock reset. The ROS test
harness supplies a controlled synthetic clock for software checks. A wall-time
fallback is not authorized by this handoff.

The following command deliberately exercises the real service behind synthetic
providers without asserting scientific agreement:

```sh
ros2 launch mge_bringup vertical_mock.launch.py \
  mission:=real planner:=real use_sim_time:=true \
  run_id:=mission-real-contract \
  mission_profiles_path:="$PWD/config/scenario_demo.yaml" \
  mission_path:="$PWD/config/scenario_demo.yaml" \
  profiles_file:="$PWD/config/planner_profiles.illustrative.json" \
  allow_illustrative:=true \
  base_enu_m:='[2.5, 2.5, 0.0]' \
  model_agreement_confirmed:=false
```

`scenario_demo.yaml` contains deliberately illustrative profiles and mission
settings, so it can supply both mission paths for this test. Its original base
`[0,0,0]` and goal `[10,0,0]` are not centres of the synthetic five-metre grid.
The explicit base override matches `human_1` at `[2.5,2.5,0]`; use an explicit
cell-centred request goal such as `[12.5,2.5,0]`. Do not silently edit/snap scenario
coordinates. This override does not approve that scenario or make the planner
and science models equivalent. Without an external clock/configuration, startup
must remain unavailable rather than fall back to mock mission.

Inspect the graph and service ownership, then query authoritative state through
the existing gateway. Use a fresh request_id after fixing a rejected request:
idempotency preserves the first answer, including a boundary rejection.

```sh
ros2 service list -t
ros2 node list
ros2 topic echo /mge/mission/state --once
```

## Validation boundary and remaining delivery

Run mission/core checks and repository validation from the checkout root:

```sh
python -m pytest tests/mission
python scripts/check_repository.py
```

After building and sourcing Jazzy, run the generated ROS service checks:

```sh
python3 -m pytest tests/contract/test_mission_service.py tests/contract/test_planner_service.py
python3 -m pytest tests/contract/test_mission_launch.py tests/integration/test_vertical_mission.py
```

The mission ROS contract suite uses a controlled planner for isolated adapter
behavior. `test_mission_launch.py` checks launch conditions, parameter forwarding and
preflight rejection. `test_vertical_mission.py` exercises the combined real
mission/planner/gateway boundary with a deterministic test-only clock. These
selector and combined smoke tests must prove exclusive
mock/real selection and the actual MissionManager -> actual PlanRoute -> gateway
boundary with a controlled synthetic clock/map/agents. Expected current
scientific outcome is explicit `MODEL_NOT_AGREED`/BLOCKED with no authorized
route or active path; service availability is the integration deliverable.
Do not set model agreement true merely to obtain a feasible demonstration.
Record actual commands, source/configuration hashes, run IDs and results in the
PR validation record; distinguish controlled tests from executed mission evidence.

The published-snapshot conformance probe compared seven synthetic itineraries:
one agreed and six differed. It found human uphill energy underestimation under
the declared science model, among other activity/O2 differences. See
[conformance evidence](planner_model_conformance.md); retain these findings and
tolerances. David and Diego must reconcile the formulations, with Jesus
validating the consumer and deployment configuration, before operational route
authorization. No model flag, parameter projection or ID can substitute for this.

Still pending: Daniel's coherent public dataset and controls, real execution and
stop acknowledgement, ROS bindings for discovery/work/traversal evidence,
scientific profile approval, agreed resource estimates and an actual end-to-end
mission/benchmark. The [public evidence recorder](mission_recording.md) already
exists on the mission front; wire its typed inputs rather than fabricate them
from routes or reimplement another recorder/manager.
