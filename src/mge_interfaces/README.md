# Shared ROS interfaces

Owner: Jesus (contract/integration), with Daniel, Diego and David confirming
functional semantics. This package preserves the team's existing ICD-ROS2-V1
wire definitions from the integration branch; no duplicate schema is introduced.

| R-F-L-P | Scope |
| --- | --- |
| R | R02, R05, R09, R13, R18; typed producers and consumers |
| F | Terrain, observations, agents, routes, mission events and goal requests |
| L | InterfaceRegistry |
| P | Six ROS messages and two services generated with rosidl |
| V&V | Build interfaces and run `tests/contract/test_interfaces.py` after sourcing the workspace |

This is a draft pending team confirmation. See `docs/ICD.md` for every field,
frame, topic, service and guard. ROS types carry run IDs but do not include the
web envelope's `schema_version`. Non-human oxygen uses NaN in ROS; the future JSON
adapter must map it to null rather than emitting invalid JSON NaN.

Use local ENU metres, row 0 at the south-west, and lower-case unit suffixes
`_wh`/`_l`. MissionManager owns the active route; Path candidates do not certify
safety. These types alone do not validate frame, version, budget or source.
Native image layers must be unambiguously associated with their run/map metadata.
The hidden evaluator raster must never be supplied to Planner.

Package versions and MIT metadata from the existing integration work are
preserved. The maintainer contact remains a placeholder pending team confirmation.
The repository-level licensing decision and third-party asset licenses still need
review; do not infer a license for external data from package metadata.
