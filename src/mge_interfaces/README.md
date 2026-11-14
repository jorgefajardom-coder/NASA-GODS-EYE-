# Shared ROS interfaces

Owner: Jesus (contract/integration), with Daniel, Diego and David approving their fields.

| R-F-L-P | Scope |
| --- | --- |
| R | R02, R05, R09, R13, R18; compatible typed producers and consumers |
| F | Define terrain, observations, agents, routes, mission events and goal requests |
| L | InterfaceRegistry |
| P | Six ROS messages and two services generated with rosidl |
| V&V | `colcon build --packages-select mge_interfaces`, then `ros2 interface show` for all eight types |

This is an **ICD-V1 draft**, not a team-approved freeze or an operational mission.
Use `map` with ENU axes and SI metres. Image terrain layers remain native
`sensor_msgs/Image` (`32FC1`); masks are separate. No evaluator-reference raster
is exposed in these interfaces. MissionManager alone publishes the active route.
All consumers must check run identity, map version, message status, array lengths
and frame consistency before acting. The schema alone does not enforce these checks.

ROS identifiers use lowercase suffixes (`energy_est_wh`, `oxygen_est_l`); their
units remain Wh and L. This normalizes the guide's uppercase unit suffixes to legal
ROS field names. `oxygen_applicable=false` and zero oxygen fields are required for
rover/drone profiles. A zero numeric default is not evidence of a measured value.

`MissionState.result_available=false` means `mission_success` is not a result.
Route statuses must be one of the six constants; only a feasible candidate can be
considered for execution, after MissionManager checks current state and reserves.
Changes require the shared ICD, consumers and contract tests to change together.

Package maintainer email is a deliberate placeholder (`team@example.invalid`);
the team must replace it with a confirmed contact. The repository license has not
yet been selected (`LicenseRef-UNSPECIFIED`); this is not a permission grant.
