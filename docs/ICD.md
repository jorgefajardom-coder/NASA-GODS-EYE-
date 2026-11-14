# ICD-ROS2-V1 — Interface Control Document

Status: **contract baseline `1.0.0-rc.1`, candidate, not frozen.** See
[configuration and publication state](CONTRACT_BASELINE.md). It becomes binding once Daniel, Diego, Jorge and
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
  wire definitions. Adapters must map non-applicable NaN to JSON `null`, never a JSON NaN token.
  This baseline tests that conversion; PR #3 implements its own ROS bridge.
  The main HTTP startup boundary remains unavailable until that producer is integrated.
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

The existing main `.msg`/`.srv` definitions (package `1.0.0`) are preserved as the
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
SetMissionGoal permits an empty run ID to mean the current run; adapters must
resolve it before recording or replay. Main still has startup placeholders; real
planning and mission services exist on the audited owner branches, respectively
PR #2 and `feat/mission`. Their code is preserved there, not replaced or merged
by this baseline. See the [implementation inventory](INTEGRATION_MATRIX.md).

MissionManager alone authorizes and publishes the active route. Only FEASIBLE
candidates may be considered after current-run/map and return-budget checks.
`MissionState.active_route` embeds the decision; an empty route ID means no route
is in force. Do not treat default numeric values as measurements or outcomes.
Native Image/OccupancyGrid/Path lack custom run/version fields: consumers need an
unambiguous association with metadata/state by frame, timestamp and run context.
The compatible planner protocol is metadata plus belief, sigma and the applicable
mask with exactly the same frame and (sec,nanosec) snapshot stamp. One stamp
identifies one run/map version for the process lifetime; reused stamps across
versions/runs, mutated duplicates and reactivation of retired runs are rejected.
Layers arriving before metadata are discarded by the planner; producers must
repeat complete batches because DDS cross-topic ordering is not guaranteed.
Changing geometry, CRS, datum, mask or raster requires a new version/stamp.
The planner's `snapshot_contract_confirmed` defaults false. Daniel/Jesus must
confirm the producer protocol before enabling it. Contract harness checks do
not implement native topic association or the real mapping publisher.

## 6. JSON, replay and display contract

The canonical JSON/replay schema stays `1.0.0` from the gateway at the pinned
integration SHA. It is independent of the unchanged ROS schema. Canonical files
are `manifest.json`, `timeline.jsonl`, `snapshot.json` plus explicitly associated
public rasters when available. [Replay contract](REPLAY_CONTRACT.md) defines
validation, timestamp/order rules, attachments and deterministic viewer conversion.
Jorge's `mge-web-0.1-draft` manifest/timeline.json/routes.json/rasters.json format
is an adapter target, not a second canonical producer contract. Preserve his
scene/assets/timeline and fixtures until consumer acceptance proves conversion.

Availability of implementations must be stated separately:

| Surface | Baseline on this cut | Existing branch work |
| --- | --- | --- |
| GET health | 200, inactive envelope, ROS disconnected | PR #3 ROS-backed health/store |
| GET manifest/snapshot | 503 NOT_READY | PR #3 active envelope, unknown run 404 |
| POST goal | 503, no accepted command | PR #3 forwarding, idempotency, 422 malformed input |
| WS events | inactive envelope then 1013 | PR #3 ordered store/event stream |
| Offline replay | validator and deterministic adapter | PR #3 recorder; Jorge legacy viewer |

Inactive identifiers, mode, map version and timestamp are null, status is
NOT_READY or ERROR, and reason_code explains the boundary. Main currently emits
ROS_NOT_CONNECTED; PR #3 uses NO_ACTIVE_RUN. Neither means a running mission.
Preserve canonical ROS names and kind casing. A transport `mode=LIVE` in the
existing gateway is not proof of validated live provenance: its MOCK sample
reports recorded_from LIVE. Display REPLAY for every recorded package and MOCK
for synthetic producers, including `REPLAY · MOCK` together. Reject incomplete
packages with NOT_READY; show ERROR with reasons for invalid ones. LIVE requires
an actual connected and validated real source. Simulation stays visibly labelled.
The additive web provenance helper tests these semantics; it is a handoff for
Jorge's existing UI, not a replacement UI or a claim it is already wired there.

No snapshot/raster join may use only the topic or file name. Bind run, dataset,
map version, geometry, frame, stamp and public-layer role. Current PR #3 recordings
lack raster arrays; the adapter must not borrow the different web dataset or
fabricate missing terrain. Full 3D replay is NOT_READY until aligned public
attachments exist. See [dataset delivery](DATASET_CONTRACT.md).

## 7. Mission, resources, positions and return

MissionManager alone owns scientific primary/secondary goals, reconnaissance ->
inspection -> sampling precedence, capability allocation, rejection reasons and
return priority. Planner computes candidate geometry/costs only; Gateway stores
and forwards authoritative state and never creates a second mission state.
One authorized active route exists for the primary agent at a time. Recheck
run/request/agent/mode/map identity, complete itinerary, resources and reserves
before authorization. On a changed map invalidate the old route immediately,
clear authorized route/path, emit the logical stop/replan reason and reject old
responses. An empty Path is a logical stop, not proof the executor stopped;
Jesus must validate acknowledgement with current agent state before execution.

The existing planner requires XY cell centres with 1e-6 m tolerance. Continuous
poses fail explicitly NON_CELL_CENTER; never silently round. A future connector
must check the swept geometry/public uncertainty and charge its time, energy and
oxygen before changing that policy. Surface z is belief elevation, not validated
drone flight altitude. EFFICIENT is an enum but current planner returns
ERROR/MODE_NOT_SUPPORTED. Search bounds and unverified terrain return UNKNOWN.

David's proposed science model `mge-science-1.0.0` governs scientific audit of
complete outbound + service + optional work + return itineraries. Diego's
MotionProfile model governs current search estimates. **They are not equivalent.**
Planner uses 3-D distance with directed slope multipliers, energy per metre and
constant human oxygen per second. Science human time uses horizontal distance
and absolute grade; metabolic power and positive climb govern energy/O2, while
rover traction/slip and drone activity powers have different equations. Exported
parameter projections do not establish agreement. The models remain
pending_model_agreement; operational authorization remains blocked until David,
Diego and Jesus record compatible behavior and an independent itinerary audit.

Shared inputs are agent kind/capabilities, public grid/grade limits, speed,
service durations, capacities and reserves with explicit SI units. Proposed
science oxygen litres mean equivalent dry O2 at 273.15 K and 101.325 kPa; this
clarification still needs consumer confirmation. Estimates are experimental,
never certified EVA or hardware limits. Record model ID/version, profile/config
SHA-256, projection version, approval state, dataset/run/map and code SHA in the
run manifest/evidence. Existing ROS types need no new fields: provenance belongs
in replay/config metadata keyed by run/request/route IDs.

Numerical agreement requires flat/uphill/downhill/zero/invalid vertical edges,
service and wait, human/rover/drone, complete return, budget boundaries and
sensitivity cases. Audit the full path once; do not sum overlapping round trips
for optional tasks. The boundary harness uses rel=1e-5/abs=1e-3 for transport
float rounding, not as scientific model equivalence. David must approve model
error bounds and conservatism using exact-source numerical results.

## 8. Data isolation, profiles and verification

Only immutable prior, public belief/sigma/observed/traversability reach planner
and ordinary web. The hidden evaluator reference and future task catalogue
must remain outside their filesystem mounts, JSON, web/public and final build.
The audited Jorge fixture bundles reference arrays with an evaluator toggle;
that is a publication blocker even though the toggle defaults off. Preserve
his branch work while removing/quarantining those values from public exports.
NoData padding for legacy shape compatibility is not evaluator truth.

Independent profiles are `mock`, `integration`, `simulation` and `live` in
`profile.launch.py`. Exactly one planner and one mission service provider may
run. MOCK uses deterministic interface-conforming producers; integration uses
real planner/mission with labelled simulated agents; simulation additionally
needs the real Gazebo backend. Live is unavailable. Launch requires explicit
owner-reviewed receipt/configuration and executable/service preflight; main
scaffolds cannot become approved providers merely by starting. See
[launch profile gates](LAUNCH_PROFILES.md). A service-availability race still
requires a dedicated ROS_DOMAIN_ID and a single launcher per run.

See [baseline test ledger](CONTRACT_BASELINE.md) for all twelve requested checks.
Generated interfaces must compile and be inspected on Ubuntu 24.04/Jazzy;
Gazebo Harmonic execution and actual producer replacement are separate pending
acceptances. No successful build, contract harness, MOCK or replay is a complete
mission demonstration. Freeze remains pending Daniel/Diego/Jorge/David/Jesus
review of units, snapshots, resources, event/reason vocabulary and consumer evidence.
