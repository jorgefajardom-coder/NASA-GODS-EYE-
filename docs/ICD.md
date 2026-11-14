# ICD-ROS2-V1 — Interface Control Document

Status: **DRAFT, not frozen.** It becomes binding once Daniel, Diego, Jorge and
David confirm units, semantics and fields. After the freeze, no interface,
frame, unit, enum or meaning changes without updating this document, the
consumers, the contract test and the version.

The `.msg` / `.srv` files in `src/mge_interfaces` are the source of truth for
field names and types; this document records the conventions around them.

## 1. Frames, grid and units

- ROS frame `map`: local Cartesian frame, **x east, y north, z up**, metres.
  `odom` / `base_link` per agent when Gazebo is used.
- Planetary coordinates are transformed explicitly to `map`. Earth WGS84 is
  never assumed. `TerrainMeta` carries the CRS, the origin latitude/longitude
  and the vertical datum.
- Grid: `(origin_x_m, origin_y_m)` is the south-west corner of cell
  `(row 0, col 0)`; rows grow north, columns grow east; flat index
  `row * cols + col`. Cell centre:
  `x = origin_x_m + (col + 0.5) * resolution_m`,
  `y = origin_y_m + (row + 0.5) * resolution_m`.
  The same indexing applies to the `32FC1` rasters and to `OccupancyGrid`.
- Web (Three.js, Y up): `(x_web, y_web, z_web) = (x_east, z_up, -y_north)`.
- SI units, with the unit as field suffix: `_m`, `_s`, `_wh`, `_l`, `_deg`.
  ROS field names are lower case, so the guide's `energy_est_Wh` is
  `energy_est_wh`.
- Oxygen fields are `NaN` for agents that are not `HUMAN` in the canonical ROS
  wire definitions. The future gateway adapter must map non-applicable NaN to JSON
  `null` (never a JSON NaN token). This explicit conversion is not implemented yet.
- ROS wire kinds are uppercase `HUMAN`/`DRONE`/`ROVER`; pure Python/configuration
  may use lowercase. Adapters must map these intentionally and reject unknown
  values. Do not assume Python models are already the ROS wire representation.
- All consumption figures and thresholds are assumptions of a simulated
  mission, never certified limits.

## 2. Time and identifiers

- `/clock` from Gazebo when it runs, with `use_sim_time=true`. Mission headers use simulated time when a simulator is active. The separate
  static MOCK smoke publisher uses wall time by default only for graph inspection;
  its timestamps are not mission ETA or evidence of simulated dynamics.
- `run_id`: stable string per execution. Data from another run is dropped.
- `map_version`: integer, grows with every valid observation.
- `request_id`: idempotency key of a request; `event_id`, `observation_id`:
  unique, applying one twice has no effect.
- `route_id`: unique per route version. One route is in force at a time; an
  answer computed on an older `map_version` returns `STALE_MAP` or is dropped.
- `MissionEvent.seq`: strictly increasing within a run.

## 3. Channels

| Channel | Type | Direction | QoS |
|---|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo → ROS | default clock |
| `/mge/terrain/meta` | `mge_interfaces/msg/TerrainMeta` | DataProvider → all | reliable, transient_local |
| `/mge/terrain/prior` | `sensor_msgs/msg/Image` `32FC1`, m | DataProvider → Mapping | reliable, transient_local |
| `/mge/terrain/belief` | `sensor_msgs/msg/Image` `32FC1`, m | Mapping → Planner/UI | reliable, transient_local |
| `/mge/terrain/sigma` | `sensor_msgs/msg/Image` `32FC1`, m | Mapping → Planner/UI | reliable, transient_local |
| `/mge/terrain/traversability/{kind}` | `nav_msgs/msg/OccupancyGrid` | Mapping → Planner | reliable, transient_local |
| `/mge/observations` | `mge_interfaces/msg/TerrainObservation` | SimAdapter → Mapping | reliable |
| `/mge/agents/{id}/state` | `mge_interfaces/msg/AgentState` | SimAdapter → Mission | reliable |
| `/mge/mission/events` | `mge_interfaces/msg/MissionEvent` | Mission → Gateway/logs | reliable |
| `/mge/mission/state` | `mge_interfaces/msg/MissionState` | Mission → Gateway | reliable, transient_local |
| `/mge/planner/active_path` | `nav_msgs/msg/Path` | Mission → Gateway/Sim | reliable, transient_local |
| `/mge/planner/plan_route` | `mge_interfaces/srv/PlanRoute` | Mission → Planner | service |
| `/mge/mission/set_goal` | `mge_interfaces/srv/SetMissionGoal` | Gateway → Mission | service |

`{kind}` is the lower-case agent kind (`human`, `drone`, `rover`).
OccupancyGrid values: `-1` unknown, `0` admissible, `100` forbidden. Unknown is
not free. The prior is immutable within a run; the belief is never the hidden
reference DEM. Publisher and subscriber declare the same QoS explicitly.
`mge_interfaces` types stay inside ROS; `ros_gz_bridge` is only used for types
it supports.

## 4. Enumerations

Enumerations are string constants defined in the messages, so the value seen
in `ros2 topic echo`, in logs and in the web JSON is the same.

- Route status: `FEASIBLE`, `UNKNOWN`, `NO_PATH`, `INSUFFICIENT_BUDGET`,
  `STALE_MAP`, `ERROR`. `UNKNOWN` does not mean `NO_PATH`.
- Route mode: `FAST`, `EFFICIENT`, `SAFE`.
- Mission state: `IDLE → PLANNING → READY → ACTIVE → REPLAN → RETURNING →
  COMPLETE`, plus `BLOCKED` / `ABORTED` with a reason.
- Task state: `DISCOVERED → ELIGIBLE → ASSIGNED → EXECUTING → DONE`, or
  `REJECTED` / `BLOCKED`.
- Agent kind: `HUMAN`, `DRONE`, `ROVER`.
- Observation source: `SIMULATED`.

## 5. Canonical wire fields

The existing integration-branch `.msg`/`.srv` definitions are preserved as the
canonical draft. Unlike the JSON envelope, ROS messages do **not** carry
`schema_version`; the ROS package/ICD versions identify their schema. All six
messages have `header` and `run_id`; not all service requests have a Header.

| Message | Fields beyond `header` and `run_id` |
| --- | --- |
| `TerrainMeta` | `dataset_id`, `map_version`, `origin_x_m`, `origin_y_m`, `resolution_m`, `rows`, `cols`, `crs`, `origin_lat_deg`, `origin_lon_deg`, `vertical_datum`, `nodata_value`, `sources[]`, `checksum_sha256` |
| `TerrainObservation` | `observation_id`, `agent_id`, `base_map_version`, `source_kind`, `cell_indices[]`, `elevation_m[]`, `sigma_m[]`, `obstacle[]` |
| `AgentState` | `agent_id`, `agent_kind`, `pose`, `velocity`, `mode`, `time_remaining_s`, `energy_remaining_wh`, `oxygen_remaining_l`, `confidence` |
| `MissionEvent` | `event_id`, `seq`, `causality_id`, `event_type`, `task_id`, `agent_id`, `map_version`, `route_id`, `previous_state`, `new_state`, `reason_code`, `detail` |
| `MissionState` | `last_event_seq`, `mission_state`, `reason_code`, `base`, `primary_goal`, `primary_agent_id`, `active_task_id`, `active_task_kind`, `active_task_state`, `map_version`, `route_id`, `active_route`, `agents[]` |
| `RouteDecision` | `request_id`, `route_id`, `agent_id`, `mode`, `map_version_used`, `status`, `reason_code`, `detail`, `outbound_path[]`, `return_path[]`, `travel_time_s`, `energy_est_wh`, `oxygen_est_l`, `min_clearance_m`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` |

Map versions are `uint32`; event sequences are `uint64`. The metadata origin and
resolution are `float64`; resource estimates are `float32`. Exact generated types
and constants remain in the ROS definitions. Parallel observation arrays must
have equal length; indices are row-major grid cells. Reject invalid bounds,
non-finite elevations, invalid sigma, stale runs and duplicate observation IDs
before changing belief. Non-human oxygen NaN is the explicit exception to finite
resource values. An accepted observation changes its footprint and increments the
map version once. Defining fields does not implement these checks.

| Service | Request fields | Response fields |
| --- | --- | --- |
| `PlanRoute` | `run_id`, `request_id`, `agent_id`, `agent_kind`, `start`, `goal`, `return_to`, `require_return`, `mode`, `map_version`, `service_time_s`, `time_budget_s`, `energy_budget_wh`, `oxygen_budget_l`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` | `decision` (`RouteDecision`) |
| `SetMissionGoal` | `request_id`, `run_id`, `primary_agent_id`, `base`, `goal`, `mode`, `time_budget_s`, `energy_budget_wh`, `oxygen_budget_l`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` | `accepted`, `request_id`, `run_id`, `mission_state`, `reason_code`, `detail` |

Service positions and RouteDecision paths are `geometry_msgs/Point` values in
`map`, not Pose or nav_msgs/Path. The active-path topic remains `nav_msgs/Path`.
SetMissionGoal permits an empty run ID to mean the current run; the eventual
adapter must resolve that before crossing into stored events or replay. Current
The planning service is implemented on feat/planner; the mission service remains
unimplemented. The planner returns candidates only and never publishes active_path.

MissionManager alone authorizes and publishes the active route. Only FEASIBLE
candidates may be considered after current-run/map and return-budget checks.
`MissionState.active_route` embeds the decision; an empty route ID means no route
is in force. Do not treat default numeric values as measurements or outcomes.
Native Image/OccupancyGrid/Path lack custom run/version fields: consumers need an
unambiguous association with metadata/state by frame, timestamp and run context.
The strict planner batch protocol below defines that association; producers must
confirm and implement it. It cannot be assumed from a topic name.

## 6. Web contract and current availability behavior

The implemented gateway surface and `web/src/lib/contracts.ts` share the following
inactive envelope (`schema_version` applies to JSON, not the ROS wire messages):

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

Null means that no active run/map/clock is loaded. Only a real loaded run may
show `mode=LIVE|REPLAY`; process availability alone does not establish either.
A snapshot error may echo a requested run ID without claiming that run exists.
`UnavailableResponse` permits `NOT_READY|ERROR`; the scaffold emits NOT_READY.

| Endpoint | Current behavior |
| --- | --- |
| `GET /api/health` | HTTP 200, inactive envelope, `ros_connected=false`, `implementation_status=scaffold` |
| `GET /api/manifest` | HTTP 503, inactive envelope |
| `GET /api/run/{run_id}/snapshot` | HTTP 503, inactive envelope with requested run ID |
| `POST /api/mission/goal` | Accepts a JSON object at the draft surface; always HTTP 503, no command accepted or forwarded |
| `WS /api/events` | Accepts, sends inactive envelope, closes with 1013 |

The web scaffold sends no API requests and renders no fabricated terrain, route
or results. Operational manifest/snapshot/goal models, ROS executor, serializer,
event recorder and polling/reconnect logic are pending. Do not infer operational
goal fields from the permissive starter JSON body. Typed adapters must preserve
ROS field names, convert non-human oxygen NaN to JSON null, and map kind casing.
Before enabling control, validate request IDs, active run/map, resource assumptions
and supported cost modes. Bind control locally until a secured remote deployment
with authentication, origin restrictions and HTTPS/WSS is explicitly designed.

The gateway remains unavailable even if the independent static MOCK publisher is
running; there is no ROS-to-HTTP state flow yet. Tests in
`tests/contracts/test_gateway.py` verify this truthful unavailable boundary only.

## 7. Reference separation, replay and verification gates

Only prior/belief/observed layers reach Planner and the normal web map; the hidden
evaluator reference and future tasks never enter these contracts. Prior is
immutable within a run. Simulated observations use source SIMULATED, not a claim
of real perception. No real Mars data, mission benchmark or complete replay is
included by this scaffold.

Target replay layout is `run_id/manifest.json`, `timeline.jsonl`, `snapshot.json`
and referenced rasters. Offline playback must consume recorded events without
new ROS state and display REPLAY. GitHub Pages serves static web/replay only;
ROS and FastAPI require a separate host for remote LIVE operation.

Build all eight ROS definitions on Jazzy, run the imported ROS contract checks,
and then verify grid/frame alignment, stale responses, duplicate observations,
clock consistency, service-to-route flow and replay without backend. Writing
these types and passing static checks is not evidence of an E2E mission or
physical safety. Preserve commands, run IDs and outcomes in evidence records.
Interface changes update this ICD, consumers, tests and versions together.

## Planner batch protocol and implementation boundary

The existing message/service definitions are unchanged. The planner requires
metadata followed by belief, sigma and the applicable traversability mask with
the exact same frame and `(sec,nanosec)` snapshot stamp. One stamp must identify
only one run/map version for the lifetime of the process. Stamp reuse across
runs or versions is rejected; old runs cannot reactivate after a run switch.
Repeated packets are allowed only when identical. Changing a layer, CRS, datum,
NoData or grid geometry requires a new map version and unique stamp.

Native layers received before their matching metadata are discarded. Producers
must repeat the coherent batch until consumers receive all layers; publishing
metadata first does not guarantee delivery order across DDS topics. Metadata
and static layers use reliable/transient_local QoS. No reference DEM is subscribed.

`snapshot_contract_confirmed` defaults false. Integration must explicitly enable
it after confirming the producer protocol; otherwise PlanRoute returns UNKNOWN.
`profiles_file` must contain approved explicit motion parameters, or illustrative
profiles require `allow_illustrative_profiles=true`. Missing/incomplete data or
profiles never produce an executable candidate. The snapshot token includes
layer revision and rejection state; changes during search discard the candidate
with STALE_MAP. A rejected immutable batch needs a fresh version to recover.

P0 positions must be exact XY cell centres (1e-6 m tolerance). Continuous poses
are rejected as NON_CELL_CENTER, since a connector cannot be silently teleported
or left out of resource costs. Output z is public belief surface elevation, not
validated drone altitude or physical locomotion. MissionManager remains responsible
for current-route authorization, observation-triggered invalidation and new requests
from the current admissible pose. See planner_handoff.md and the planning MODEL.md.

EFFICIENT returns ERROR/MODE_NOT_SUPPORTED. Search limits return UNKNOWN/SEARCH_LIMIT,
including when SAFE cannot prove its maximal conservative bottleneck. Orbital
prior validity is not observation: the included CTX loader marks all cells unknown.

## 8. Open points for the freeze meeting

1. Row order of the `32FC1` rasters: this draft uses row 0 = south so that
   rasters and `OccupancyGrid` share one index. GeoTIFF sources are usually
   north-up (row 0 = north), so the data provider flips on load. (Daniel)
2. Paths are `geometry_msgs/Point[]` in `RouteDecision`; `nav_msgs/Path` is
   used only on `/mge/planner/active_path`. (Diego)
3. `MissionState` embeds the full `RouteDecision` and `AgentState[]` so a
   single message is a complete snapshot. (David)
4. Oxygen unit: litres, as `_l`. (David)
5. Event type and reason code vocabularies. (David)
6. `ROS_DOMAIN_ID` for team rehearsals; `scripts/dev.sh` defaults to 42.
