# Exclusive launch profiles

`ros2 launch mge_bringup profile.launch.py profile:=mock run_id:=<unique-id>
approval_receipt:=<reviewed-json>` selects exactly one provider per role.
Join that command on one shell line. Ubuntu 24.04/Jazzy is required. The launch
is deliberately NOT_READY on the current scaffold without an owner-reviewed
receipt and the selected implementation executables. No approval is supplied
by this baseline. Inventory selection tests are not graph/execution acceptance.

| Profile | Planner / mission | Data / agents | Remaining gate |
| --- | --- | --- | --- |
| mock | mge_sim mock_planner / mock_mission | mock_terrain / mock_agents | PR #3 providers and Jesus integration review; visibly MOCK |
| integration | mge_planning planning_node / mge_mission mission_node | real data_node + mapping_node / mock_agents | owner configuration, model/data approval, external running /clock |
| simulation | same real services | real data/mapping / sim_node | real Gazebo Harmonic backend and running /clock, same approvals |
| live | unavailable | unavailable | LIVE_BACKEND_UNAVAILABLE |

The gateway executable is common; it consumes mission authority and does not
become a mission provider. Never run vertical_mock.launch.py alongside a real
planner/mission on the same domain. Use a dedicated ROS_DOMAIN_ID and a single
launcher for each run. The service collision preflight is a fail-closed graph
check, not a distributed mutex; racing launchers remain prohibited. A /clock
topic must exist for integration/simulation; MissionNode separately requires
actual advancing clock messages. Topic existence alone is not clock validation.

Receipt fields: baseline_version=1.0.0-rc.1; providers is an exact role ->
{package, executable, kind} inventory from profile_providers; integration_approved
must be true only after Jesus review. For integration/simulation, science_approved,
resource_model_agreed, dataset_approved and snapshot_contract_confirmed must all
be true after actual evidence. Booleans record owner decisions; they do not
create that evidence or automatically identify a scaffold as REAL.

The receipt's optional parameters map passes dictionaries per provider role.
Real profiles require planner scientific_profiles_path matching the mission's
profiles_path, snapshot_contract_confirmed=true and no legacy cost opt-in;
mission profiles_path, mission_path, model_agreement_confirmed=true and
approved_model_id. Other owner parameters (terrain manifest, base/tolerances,
service assumptions, agents_file, gateway host) pass through unchanged. The
launcher owns run_id/use_sim_time and the gateway's source_mode, and rejects
overrides. source_mode is MOCK when any selected provider is MOCK (mock and
integration profiles) and SIMULATION otherwise; it is never LIVE. Configuration files
must exist and their validity/approval is checked by their real producer; record
their SHA-256 and source/model IDs in run evidence. Do not infer resource inputs
from mock defaults or invent approvals to activate a profile.

Synthetic receipt dictionaries in test_configuration.py only test selection and
parameter forwarding. A launch with no receipt fails NOT_READY before creating
providers. Main now has the real planner from externally merged PR #2, but still has
placeholder data/mapping/mission/sim nodes;
a build or executable's presence is not producer readiness. Keep approvals false
until those actual modules are integrated and tested with one unchanged consumer.
