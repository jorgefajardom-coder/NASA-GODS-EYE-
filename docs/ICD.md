# Interface Control Document - ICD-V1 draft

Status: scaffold contract, pending confirmation by Jesus, Daniel, Diego, Jorge and
David. Writing these definitions does not freeze the design or prove an operational
mission. Jesus owns integration; functional owners approve their fields and David
approves scientific assumptions. Based on the supplied general guide (pages 4-5)
and Jesus's integration guide (pages 1-3), dated 14 November 2026.

## Coordinates, units and time

- ROS `map` is local ENU: x east, y north, z up, all in metres. Define agent-local
  `odom` and `base_link` frames when a simulator supplies them.
- Three.js receives `(x_web, y_web, z_web) = (x_east, z_up, -y_north)` with no
  scientific height exaggeration. Planetary CRS, datum and grid registration must
  come from the terrain manifest; never assume terrestrial WGS84.
- `header.stamp` is simulation time when a simulation runs. Gazebo supplies
  `/clock`; consuming simulation nodes use `use_sim_time=true`. No clock is
  supplied by the current scaffold. Replay uses the recorded timestamps.
- Height, resolution and clearance use m; duration uses s; energy uses Wh; human
  oxygen uses L. These are simulated estimates and assumptions, not certified EVA
  limits. Non-human agents set `oxygen_applicable=false` and oxygen values to zero.
- ROS and JSON identifiers normalize the guide's uppercase unit suffixes to legal
  lowercase snake_case: `energy_est_wh`, `oxygen_est_l`, `reserve_wh`,
  `reserve_oxygen_l`. The physical units remain Wh and L.

## Identity, ordering and authority

`schema_version` identifies the wire contract (draft web envelope `1.0.0`).
`run_id` identifies one execution; `request_id` is idempotent within that run.
`observation_id` and `event_id` must be deduplicated before any state mutation.
`MissionEvent.sequence` increases within a run. `map_version` increases exactly
once per accepted observation; stale runs, invalid footprints and duplicate IDs
must not advance it. `route_id` identifies a route computed against
`map_version_used`; an older response must never replace a newer active route.

MissionManager alone owns the mission state and published active route. Planner
returns candidates; Mapping owns belief and its version; the web viewer renders
the authoritative decision. These are implementation requirements, not checks
enforced merely by defining a ROS message or a TypeScript interface.

## ROS message definitions

The exact fields and types are in `src/mge_interfaces/msg/`. All six messages
contain `std_msgs/Header`, `schema_version` and `run_id`.

| Message | Functional owner | Additional fields |
| --- | --- | --- |
| `TerrainMeta` | Daniel | `dataset_id`, `frame_id`, `origin_enu_m` (Point), `resolution_m`, `rows`, `cols`, `horizontal_crs`, `vertical_datum`, `nodata_value`, `nodata_mask_uri`, `sources[]`, `checksum_sha256`, `map_version` |
| `TerrainObservation` | Daniel / David | `observation_id`, `agent_id`, `prior_map_version`, `cell_indices[]`, `elevation_m[]`, `obstacle_state[]`, `sigma_m[]`, `source_kind` |
| `AgentState` | David | `agent_id`, `agent_kind`, `pose`, `velocity`, `state`, `timestamp_sim_s`, `time_remaining_s`, `energy_remaining_wh`, `oxygen_applicable`, `oxygen_remaining_l`, `confidence` |
| `MissionEvent` | David | `event_id`, `sequence`, `causality_id`, `event_type`, `task_id`, `agent_id`, `map_version`, `route_id`, `previous_state`, `new_state`, `reason_code` |
| `MissionState` | David / Jesus | `map_version`, `mission_state`, `primary_goal`, `base`, `active_task_id`, `active_agent_id`, `agents[]`, `route_id`, `reserve_wh`, `reserve_oxygen_l`, `mission_success`, `result_available`, `reason_code` |
| `RouteDecision` | Diego | `request_id`, `route_id`, `map_version_used`, `status`, `outbound_path`, `return_path`, `travel_time_s`, `energy_est_wh`, `oxygen_applicable`, `oxygen_est_l`, `min_clearance_m`, `reserve_wh`, `reserve_oxygen_l`, `reason_code` |

Observation arrays have identical length and refer to row-major indices in the
current grid. Validate bounds, finite values, nonnegative sigma, source kind and
obstacle semantics before applying a footprint. P0 observations use
`source_kind=SIMULATED`; they are not real camera reconstructions.
`MissionState.result_available=false` means no success/failure result exists;
numeric and boolean ROS defaults are not observations or evidence.

Agent kind values are lowercase `human`, `drone`, `rover`, matching Python and
configuration; ROS constant identifiers remain uppercase. Route statuses: `FEASIBLE`, `UNKNOWN`,
`NO_PATH`, `INSUFFICIENT_BUDGET`, `STALE_MAP`, `ERROR`. Only a feasible candidate
may be considered for execution after current-state and reserve checks.
`UNKNOWN` is distinct from `NO_PATH` and is never a verified corridor.

Mission states: `IDLE`, `PLANNING`, `READY`, `ACTIVE`, `REPLAN`, `RETURNING`,
`COMPLETE`, `BLOCKED`, `ABORTED`. State transitions and task precedences remain
MissionManager work; listing constants does not implement them.

## Topics and QoS

The table is the integration target; the starter nodes currently publish none of
these topics. Use matching producer/consumer QoS, explicitly configured by owners.

| Topic | ROS type | Authority / consumer | Target QoS |
| --- | --- | --- | --- |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo -> simulation nodes | Clock-compatible policy agreed with simulator |
| `/mge/terrain/meta` | `mge_interfaces/msg/TerrainMeta` | Data -> all | Reliable, transient_local, keep last |
| `/mge/terrain/prior` | `sensor_msgs/msg/Image` | Data -> Mapping | Reliable, transient_local, keep last |
| `/mge/terrain/belief` | `sensor_msgs/msg/Image` | Mapping -> Planner / Gateway | Reliable, last consistent map |
| `/mge/terrain/sigma` | `sensor_msgs/msg/Image` | Mapping -> Planner / Gateway | Reliable, last consistent map |
| `/mge/terrain/traversability/{kind}` | `nav_msgs/msg/OccupancyGrid` | Mapping -> Planner | Reliable, last consistent map |
| `/mge/observations` | `mge_interfaces/msg/TerrainObservation` | Simulation -> Mapping | Reliable |
| `/mge/agents/{id}/state` | `mge_interfaces/msg/AgentState` | Simulation -> Mission | Reliable |
| `/mge/mission/events` | `mge_interfaces/msg/MissionEvent` | Mission -> Gateway / recorder | Reliable, ordered and deduplicated by consumer |
| `/mge/mission/state` | `mge_interfaces/msg/MissionState` | Mission -> Gateway | Reliable, transient_local, keep last |
| `/mge/planner/active_path` | `nav_msgs/msg/Path` | Mission -> Gateway / Simulation | Reliable, last authoritative route |

Terrain images use `32FC1` in metres with a separate NoData mask; occupancy values
are -1 unknown, 0 admissible and 100 prohibited. Native `Image`, `OccupancyGrid`
and `Path` lack custom run/version fields: producers and consumers must implement
an unambiguous association with metadata/state (including timestamps and frame)
before accepting them. That association is pending and must be tested rather than
assumed. High-rate camera topics, when added, use a compatible sensor-data profile.
`ros_gz_bridge` only translates supported native Gazebo/ROS types; no arbitrary
translation of `mge_interfaces` is implied. Actual Gazebo topic mappings are pending.

## ROS services

| Service | Request | Response |
| --- | --- | --- |
| `/mge/planner/plan_route` (`PlanRoute`) | Header, schema/run/request IDs, `agent_id`, `agent_kind`, `start`, `goal`, `base`, `cost_mode`, `map_version`, `time_available_s`, `energy_available_wh`, `oxygen_applicable`, `oxygen_available_l`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` | `decision`: `RouteDecision` |
| `/mge/mission/set_goal` (`SetMissionGoal`) | Header, schema/run/request IDs, `agent_id`, `map_version`, `goal`, `base`, the same time/energy/oxygen/reserve fields | Header, schema/run/request IDs, `accepted`, `reason_code` |

Pose fields use the common ENU map. Route cost modes are `FAST`, `SAFE`,
`EFFICIENT`; consumers must reject unsupported modes rather than silently switch.
Budget feasibility includes outbound travel, task, return and reserves separately
for each applicable resource. These service definitions are not running services yet.

## Web envelope and current endpoint behavior

`web/src/lib/contracts.ts` and `mge_gateway.api` share this envelope:

```json
{
  "schema_version": "1.0.0",
  "run_id": null,
  "mode": null,
  "map_version": null,
  "timestamp_sim_s": null,
  "status": "NOT_READY",
  "reason_code": "ROS_NOT_CONNECTED"
}
```

Active runs will use non-null `run_id`, integer map version, simulated time and
`mode=LIVE|REPLAY`. The null inactive envelope explicitly means no run is loaded;
it is not fabricated LIVE/REPLAY data. A snapshot error may echo the requested
`run_id` without claiming that the run exists. The web viewer currently sends no
API requests. `UnavailableResponse` permits `NOT_READY|ERROR`; the scaffold emits
`NOT_READY` with `ROS_NOT_CONNECTED`.

| Endpoint | Current implementation |
| --- | --- |
| `GET /api/health` | HTTP 200 with inactive envelope, `ros_connected=false`, `implementation_status=scaffold`; process health is not mission readiness |
| `GET /api/manifest` | HTTP 503 with inactive envelope |
| `GET /api/run/{run_id}/snapshot` | HTTP 503 with inactive envelope and requested run ID |
| `POST /api/mission/goal` | Accepts a JSON object for the draft surface; always HTTP 503; no command accepted or forwarded |
| `WS /api/events` | Accepts handshake, sends inactive envelope, closes with 1013 |

Operational goal validation, manifest/snapshot models, event serialization,
ROS-to-JSON adapters and reconnect/polling behavior remain unimplemented. Do not
infer these data shapes from the permissive starter POST body. Add typed models
and corresponding producer/consumer checks before enabling control.

## Reference separation, replay and validation gates

Only prior/belief/observed layers reach Planner and the normal web map. Hidden
evaluator reference data and future tasks must not be exposed through these
contracts. No real Mars raster, replay or benchmark is included in the scaffold.
Target replay layout is `run_id/manifest.json`, `timeline.jsonl`, `snapshot.json`
and referenced rasters. Replay uses recorded events without gateway or ROS and
must display REPLAY. GitHub Pages can host that static frontend; it cannot run ROS
or FastAPI. Remote LIVE requires a separately designed secured HTTPS/WSS service.

Before a contract freeze, build all eight ROS interfaces on Jazzy, validate unit
and frame alignment with Daniel and Jorge, and test stale responses, duplicate
events, clock consistency, service-to-route flow and replay without backend.
Current HTTP contract tests verify only the explicitly unavailable boundary.
Windows syntax/XML checks are not evidence of a successful ROS build.
Any interface change must update this ICD, affected producers/consumers and tests
together; record approval and results in `integration_log.md`.

The terrain file manifest has its own integer schema version `1`; it is distinct
from the ROS/web wire version `1.0.0`. Implemented adapters must explicitly map
the file metadata and pure Python observations to ROS fields before publishing.
