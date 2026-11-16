# ICD-ROS2-V1 — Interface Control Document

## Candidate scientific-cost migration: interface package 2.0.0

The operational cost fix over main `d13a4b3` adds the typed
`/mge/planner/register_context` service under
`mge-planning-cost-context-1.0.0`. Existing message and service fields retain
their exact definitions. The scientific PlanRoute server requires an immutable
registered request/activity context by default; old callers require explicit
legacy server opt-in. This changed prerequisite is a major semantic migration,
recorded as candidate baseline `2.0.0-rc.1`. The owner accepted the migration and
authorized PR50 integration after CI in [D-COST-03](decisions/2026-11-15-scientific-cost-context-migration.md).
This does not freeze every contract or approve profile coefficients.

The context binds all original PlanRoute fields, actual float64 XYZ, float32
resource/service values, model ID/source hash, profile-registry hash and ordered
remaining activities at the goal. Duplicate registration is idempotent;
conflicting or missing context fails closed. Both producer and consumer are
implemented together. Full semantics, failures, migration and verification are
in [operational scientific costs](scientific_cost_integration.md).
Gateway, replay and public-raster JSON versions remain unchanged. The historical
published rc.2 description below retains its original source scope.

Status: **contract reconciliation `1.0.0-rc.2`, published by PR28 at main9198b3d,
not frozen or scientifically approved.** Original audit input:
`main@6bcf208868e37b7e15e9189fac11de96e7414eff`; reviewed source `7f0ebaa`.
Remaining candidate/owner-review wording concerns semantic approval, not absence
of the merged F/E implementation. No ROS package or JSON/replay version is
bumped by this record. [Runtime-v1 validation](../evidence/audit-reconciliation-20261115/runtime-v1/README.md)
records the fresh F/E ROS consumer and ordinary-Chrome backend-off replay;
owner freeze, private-browser and scientific acceptance remain separate. See
[configuration and publication state](CONTRACT_BASELINE.md). It becomes binding
once Daniel, Diego, Jorge, David and Jesus confirm units, semantics and fields.
After the freeze, no interface,
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
- Terrain elevation and every authoritative `pose.position.z` / route Point.z
  use metres above the declared `vertical_datum`; the recorded ROS chain has no
  implicit local Z offset. AGL is a separate derived quantity, not a ROS pose.
  The execution boundary must preserve finite current XYZ and reject a route
  whose first point differs by more than the existing 1e-6 m model tolerance.
  It must not replace telemetry with surface height. Goal/base XY target
  semantics remain unchanged; a surface candidate is not a flight trajectory.
- A new labelled MOCK scene may explicitly initialize missing initial Z from
  its declared public-prior dataset/hash/datum. This is scenario construction,
  never an observation or an update to an existing pose. The parked drone is
  placed on that declared scene surface. Missing height without that declaration,
  NoData or incompatible explicit XYZ must fail before publishing agent state.
- Display sampling uses the actual rendered triangle and animated vertex buffer;
  visual draping/exaggeration must never alter recorded XYZ or mission authority.
- SI units, with the unit as field suffix: `_m`, `_s`, `_wh`, `_l`, `_deg`.
  ROS field names are lower case, so the guide's `energy_est_Wh` is
  `energy_est_wh`.
- Oxygen fields are `NaN` for agents that are not `HUMAN` in the canonical ROS
  wire definitions. Adapters must map non-applicable NaN to JSON `null`, never a JSON NaN token.
  The published gateway/recorder implement status- and agent-aware conversion.
  The ROS-backed HTTP boundary stays NOT_READY until a configured mission state arrives.
- Proposed quantitative clarification from the mission model: `_l` denotes dry
  ideal-gas-equivalent oxygen at 273.15 K and 101.325 kPa, not tank volume. This
  convention remains pending consumer confirmation; proposed profiles are not
  operational approval and a planner projection is not model agreement.
- ROS wire kinds are uppercase `HUMAN`/`DRONE`/`ROVER`; pure Python/configuration
  may use lowercase. Adapters must map these intentionally and reject unknown
  values. Do not assume Python models are already the ROS wire representation.
- All consumption figures and thresholds are assumptions of a simulated
  mission, never certified limits.

## 2. Time and identifiers

- `/clock` from Gazebo when it runs, with `use_sim_time=true`. Mission headers use simulated time when a simulator is active.
  Per [D-CLK-01](decisions/2026-11-15-simulation-time-source.md), a run has exactly one
  time base: either every MGE node uses `use_sim_time=true` against exactly one
  external, advancing `/clock` (Gazebo's, bridged unidirectionally), or the whole
  run is a wall-clock MOCK run recorded as `clock_source: system`. Launches fail
  `NOT_READY` (no or frozen clock) or `PROVIDER_COLLISION` (two clocks) before
  any provider starts; no node fabricates a clock. Mission time, ETAs and
  `time_remaining_s` debit follow that base. Steady-clock timers (stop/brake watchdog,
  odometry freshness, mirror throttling, mission polling) are deliberate liveness exceptions and never
  stamp messages or debit resources. Pausing Gazebo pauses mission time. The separate
  static MOCK smoke publisher uses wall time by default only for graph inspection;
  its timestamps are not mission ETA or evidence of simulated dynamics.
- `run_id`: stable string per execution. Data from another run is dropped.
- `map_version`: integer, grows with every valid observation.
- `request_id`: idempotency key of a request; `event_id`, `observation_id`:
  unique, applying one twice has no effect.
- `route_id`: unique per route version. One route is in force at a time; an
  answer computed on an older `map_version` returns `STALE_MAP` or is dropped.
- `MissionEvent.seq`: allocated strictly increasing within a run; positive uint64,
  unique independently of event ID. Transport delivery may arrive out of order.
  Retain late events and sort by sequence only when reconstructing logical history.

## 3. Channels

| Channel | Type | Direction | QoS |
|---|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo → ROS | default clock |
| `/mge/terrain/meta` | `mge_interfaces/msg/TerrainMeta` | Mapping → all | reliable, transient_local |
| `/mge/terrain/prior` | `sensor_msgs/msg/Image` `32FC1`, m | DataProvider → Mapping | reliable, transient_local |
| `/mge/terrain/belief` | `sensor_msgs/msg/Image` `32FC1`, m | Mapping → Planner/UI | reliable, transient_local |
| `/mge/terrain/sigma` | `sensor_msgs/msg/Image` `32FC1`, m | Mapping → Planner/UI | reliable, transient_local |
| `/mge/terrain/observed` | `sensor_msgs/msg/Image` `mono8`, 1 observed / 0 not | Mapping → Recorder/UI | reliable, transient_local |
| `/mge/terrain/traversability/{kind}` | `nav_msgs/msg/OccupancyGrid` | Mapping → Planner | reliable, transient_local |
| `/mge/observations` | `mge_interfaces/msg/TerrainObservation` | SimAdapter → Mapping | reliable |
| `/mge/agents/{id}/state` | `mge_interfaces/msg/AgentState` | SimAdapter → Mission | reliable |
| `/mge/mission/events` | `mge_interfaces/msg/MissionEvent` | Mission → Gateway/logs | reliable |
| `/mge/mission/state` | `mge_interfaces/msg/MissionState` | Mission → Gateway | reliable, transient_local |
| `/mge/planner/active_path` | `nav_msgs/msg/Path` | Mission → Gateway/Sim | reliable, transient_local |
| `/mge/planner/plan_route` | `mge_interfaces/srv/PlanRoute` | Mission → Planner | service |
| `/mge/mission/set_goal` | `mge_interfaces/srv/SetMissionGoal` | Gateway → Mission | service |

`{kind}` is the lower-case agent kind (`human`, `drone`, `rover`).
Metadata has exactly one publisher per run: the node that owns `map_version`
(`mapping_node`, or `mock_terrain` in the mock vertical), because metadata is
part of the stamped batch of section 5. `data_node` publishes the prior only.
OccupancyGrid values: `-1` unknown, `0` admissible, `100` forbidden. Unknown is
not free. `observed` marks the cells an applied local observation covered; it
is coverage, not knowledge: an observed cell stays unknown (`-1`) when it is
NoData or its sigma is too high. It travels in the stamped batch of section 5,
after sigma, so the recorder can associate it with its map version; the planner
does not subscribe to it. The observed topic and public-raster recording are
published on main without custom message-field changes. The candidate exploration
and observation semantics below still need producer/consumer owner review. The
prior is immutable within a run; the belief is never the hidden
reference DEM. Publisher and subscriber declare the same QoS explicitly.

**D-EST-01 experimental candidate in this rc.2 worktree:**
The [accepted scope](decisions/2026-11-14-estimated-terrain-planning.md) permits
hypothetical routes over valid orbital estimates without a blanket observation
prerequisite. Mapping startup remains legacy `observed_only` unless an explicit
`exploration_policy_file` is supplied. The illustrative file
`config/exploration_policy.illustrative.json` uses schema
`mge-exploration-policy-1.0.0`, policy ID `estimated-prior-illustrative-01`, mode
`estimated_or_observed` and per-kind max sigma 3 m. Its policy ID/schema/mode,
candidate-only meaning and exact file SHA-256 are appended to TerrainMeta.sources.

Under this explicit policy, mask 0 means proposal-admissible under the declared
limits; it does not assert local observation, verification or authorized passage.
`observed` remains coverage. NoData, confirmed obstacles, finite uncertainty,
slope/footprint and the planner's independent profile remain enforced. An
independent profile capped at sigma 1 m may reject the unchanged 2.5 m prior even
when mapping admits estimates up to 3 m. Missing/invalid selected policy is an
explicit startup error; policy absence preserves the legacy mode. Numeric wire
codes and JSON/ROS schemas are unchanged. Candidate semantics and target-platform
consumer acceptance need Daniel/Diego/Jesus review, with David's threshold and
inspection/stop/resource review; new ROS validation is not claimed here.
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
and constants remain in the ROS definitions. Nonempty parallel observation arrays must
match the cell-index length; an omitted optional sigma/obstacle vector follows
the explicit adapter rules below. Indices are row-major grid cells. Reject invalid bounds,
non-finite elevations, invalid sigma and stale runs; deduplicate applied observation
IDs before changing belief. Non-human oxygen NaN is the explicit non-applicable sentinel. The integrated
planner also emits NaN unavailable metrics on non-FEASIBLE RouteDecision; typed
status-conditioned serialization maps only those unavailable fields to null.
Never replace invalid FEASIBLE metrics or infinities with null silently. An accepted observation changes its footprint and increments the
map version once. Mapping implements these checks; the candidate causal rules
below add causal freshness protection with fresh consumer proof in runtime-v1.

| Service | Request fields | Response fields |
| --- | --- | --- |
| `PlanRoute` | `run_id`, `request_id`, `agent_id`, `agent_kind`, `start`, `goal`, `return_to`, `require_return`, `mode`, `map_version`, `service_time_s`, `time_budget_s`, `energy_budget_wh`, `oxygen_budget_l`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` | `decision` (`RouteDecision`) |
| `SetMissionGoal` | `request_id`, `run_id`, `primary_agent_id`, `base`, `goal`, `mode`, `time_budget_s`, `energy_budget_wh`, `oxygen_budget_l`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` | `accepted`, `request_id`, `run_id`, `mission_state`, `reason_code`, `detail` |

### Observation conversion and causal fusion (candidate F)

The mapping adapter requires frame `map`, nonnegative int32 seconds and
nanoseconds in `[0, 1e9)`. Invalid times are rejected without clamping. It keeps
SIMULATED source identity, current `base_map_version` and the received footprint.
For a new ID, base version must equal current belief version; a stale or future
base is rejected. The stamp must be no earlier than the globally last accepted
observation, including across disjoint footprints. Equal timestamps may apply
distinct current-base observations. This is a conservative global high-water
mark for accepted observations, not a claim that a delayed measurement was
retaken. Reobserve against the new base instead of relabelling stale data.

ROS ordering uses the exact integer key `sec*1e9 + nanosec` throughout fusion;
descriptive float seconds never decide freshness. This prevents an older FREE
measurement from erasing a newer obstacle when large-epoch float seconds collide.
Pure Python callers may supply the exact nanosecond key; seconds-only legacy
input is explicitly quantized to nearest nanosecond, ties to even, with checked
range/consistency. The internal key adds no ROS field or replay format.

An already-applied observation ID is a no-op without another version increment
or clock/cell mutation. Reject invalid footprint/NoData/source/run/conversion
inputs atomically. The legacy optional empty sigma vector uses its explicit
configured fallback. An empty obstacle vector carries no new obstacle evidence;
UNKNOWN `-1` or omitted obstacle data cannot clear an existing confirmed `100`.
Only explicit current, nonolder FREE `0` evidence may supersede that obstacle.
All accepted updates remain inside the footprint and increment the version once.

These rules are implemented as an rc.2 candidate with contract/core tests.
The current ROS integration results must be recorded separately before review;
older recovery CI cannot establish these new fusion semantics.

Service positions and RouteDecision paths are `geometry_msgs/Point` values in
`map`, not Pose or nav_msgs/Path. The active-path topic remains `nav_msgs/Path`.
SetMissionGoal permits an empty run ID to mean the current run; resolve it
before events/replay. Main already integrates the real MissionNode beside the
real planner and gateway; original owner implementation/history is retained. The real manager
replaces mock_mission by configuration; it must never share the mission service
or state/path publishers with the MOCK provider. Missing configuration/clock
or unapproved models remain explicit rejection reasons, not MOCK fallback.

MissionManager alone authorizes and publishes the active route. Only FEASIBLE
candidates may be considered after current-run/map and return-budget checks.
For FEASIBLE decisions, applicable numeric estimates must be finite. The
published planner uses NaN for unavailable cost/clearance/reserve fields on
non-FEASIBLE decisions; mission represents these as None and preserves the
original status/reason. Unavailable diagnostics are never activated routes or
measured zeros. No wire field is changed by this clarification.

The published planner stamps a FEASIBLE response with its map batch timestamp.
Mission associates it with the captured map/run/version and independently audits
the request, current pose and resources; newer agent telemetry does not require
a newer map stamp. Failure stamp zero can express unavailable context, while
run/frame and future-time guards still apply. Consumer confirmation remains
part of the draft ICD freeze.

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
Missing profiles keep planner results UNKNOWN/PROFILE_NOT_READY; illustrative
profiles require explicit allow_illustrative_profiles. Changes during search
invalidate the snapshot token and discard stale candidates. Rejected immutable
batches require a fresh version/stamp. `snapshot_contract_confirmed` defaults
false. Daniel/Jesus confirm the producer protocol before enabling it. Main's
mapping publisher and planner implement native stamped-batch association;
current candidate acceptance still requires the actual consumer tests.

## 6. JSON, replay and display contract

The canonical JSON/replay schema stays `1.0.0` from the published gateway. It is independent of the unchanged ROS schema. Canonical files
are `manifest.json`, `timeline.jsonl`, `snapshot.json` plus explicitly associated
public rasters when available. [Replay contract](REPLAY_CONTRACT.md) defines
validation, timestamp/order rules, attachments and deterministic viewer conversion.
Jorge's `mge-web-0.1-draft` manifest/timeline.json/routes.json/rasters.json format
is an adapter target, not a second canonical producer contract. Preserve his
scene/assets/timeline and fixtures until consumer acceptance proves conversion.

The ROS-backed gateway and recorder below are implemented on main. Until a
mission state arrives, inactive identifiers, mode, map version and timestamp
are null with status NOT_READY and reason NO_ACTIVE_RUN. No running process
alone establishes a mission.
Preserve canonical ROS names and kind casing. A transport `mode=LIVE` in the
existing gateway is not proof of validated live provenance: its MOCK sample
reports recorded_from LIVE. Display REPLAY for every recorded package and MOCK
for synthetic producers, including `REPLAY · MOCK` together. Reject incomplete
packages with NOT_READY; show ERROR with reasons for invalid ones. LIVE requires
an actual connected and validated real source. Simulation stays visibly labelled.
The existing viewer/adapter retain explicit replay/source labels. Consumer and
browser evidence must establish the labels for each exported package.

No snapshot/raster join may use only the topic or file name. Bind run, dataset,
map version, geometry, frame, stamp and public-layer role. Main's recorder writes
public raster attachments and the viewer consumes them with the closing snapshot.
The adapter cannot borrow another dataset or fabricate absent terrain. A missing
required attachment remains NOT_READY. See [dataset delivery](DATASET_CONTRACT.md).

### 6.1 HTTP gateway


Served by `mge_gateway`. It binds to `127.0.0.1` by default and holds no
planning or mission logic. Every JSON response and WebSocket message is an
envelope with `schema_version` (`"1.0.0"`; it applies to JSON, not to the ROS
wire messages), `run_id`, `mode` (`LIVE` | `REPLAY`), `map_version` and
`timestamp_sim_s`, plus the payload. Payloads use the ROS
field names unchanged. Output follows the typed non-finite rules of section 5:
NaN becomes `null` only for `TerrainMeta.nodata_value`, oxygen of an agent that
is not `HUMAN` (`AgentState.oxygen_remaining_l`, and `oxygen_est_l` /
`reserve_oxygen_l` of its route) and the seven metrics of a `RouteDecision`
whose status is not `FEASIBLE`. Any other NaN, and every infinity, rejects the
whole message: the gateway and the recorder drop it, log the field path and keep
the last valid state. A `FEASIBLE` route with a NaN metric is therefore never
shown. The route's agent kind is read from `MissionState.agents`.

| Route | Payload |
|---|---|
| `GET /api/health` | `status` (`READY`), `ros_connected`, `terrain_meta_received` |
| `GET /api/manifest` | `source_mode`, `terrain_meta`, `agents` (`agent_id`, `agent_kind`), `endpoints` |
| `GET /api/run/{run_id}/snapshot` | `mission_state`, `terrain_meta`, `events` (all so far) |
| `GET /api/run/{run_id}/events?after_seq=N` | `events` with `seq > N`; polling fallback |
| `POST /api/mission/goal` | Body: `request_id` (optional), `primary_agent_id`, `base`, `goal`, `mode`, budgets and reserves. Answer: the `SetMissionGoal` response fields |
| `WS /api/events?after_seq=N` | Backlog of events with `seq > N`, then the current state, then live messages |

- `source_mode` (`MOCK` | `SIMULATION` | `UNKNOWN`) says who produces the data
  of the run. It is separate from `mode`, which only says whether the data is
  arriving now (`LIVE`) or was recorded (`REPLAY`). The launcher declares it
  through the `source_mode` parameter (default `UNKNOWN`); terrain metadata
  that says MOCK (dataset ID or a source entry) always yields `MOCK`. `LIVE` is
  reserved for a validated real source and cannot be declared: the node refuses
  to start with `NOT_READY: LIVE_BACKEND_UNAVAILABLE`. The field is an optional
  addition to JSON `1.0.0`; a client that does not find it must show `UNKNOWN`.
- WebSocket messages carry `type`: `"event"` with an `event` object
  (`MissionEvent`), `"state"` with a `state` object (`MissionState`), or
  `"terrain_meta"` with a `terrain_meta` object (`TerrainMeta`) when a newer
  map version of the run arrives (the same type a timeline record uses, section 7;
  an optional addition to JSON `1.0.0`, so a client may ignore it). Each event is
  sent once per connection, even when it is both in the backlog and live. A
  client that falls more than 1000 messages behind is closed with code 1013 and
  resumes with `after_seq`.
- **No active run.** Until a mission state of the configured run has been
  received, the gateway invents no run, map, clock or mode. It answers with
  the inactive envelope below: `GET /api/health` with HTTP 200 plus
  `ros_connected: false`; manifest, snapshot, events and `POST` with HTTP 503
  (snapshot and events echo the requested run ID without claiming it exists);
  the WebSocket sends it once and closes with code 1013. A running process
  alone is never `LIVE`. `web/src/lib/contracts.ts` types this as
  `UnavailableResponse`.

  ```json
  {
    "schema_version": "1.0.0",
    "run_id": null,
    "mode": null,
    "map_version": null,
    "timestamp_sim_s": null,
    "status": "NOT_READY",
    "reason_code": "NO_ACTIVE_RUN"
  }
  ```

- An unknown `run_id` answers `404`. A malformed body answers `422`. A goal
  the mission refuses answers `200` with `accepted: false` and a
  `reason_code`. If the mission service does not answer, the reply is `503`
  with the inactive envelope, `status: "ERROR"` and
  `reason_code: "MISSION_SERVICE_UNAVAILABLE"`.
- Base/goal coordinates must be finite. Explicit resource budgets/reserves must
  be finite, nonnegative and fit the ROS float32 fields. Invalid values answer
  `422` before any ROS request is sent. Omitted oxygen retains the existing
  internal NaN sentinel; mission still checks applicability to the selected agent.
  Validation-error details are JSON-safe: a non-finite rejected input is rendered
  as `null` in the error payload, retaining the field location and error type.
- Repeating a `request_id` returns the first answer and creates no events.
- A planning failure is not an HTTP error: the goal is accepted, the mission
  goes to `BLOCKED`, and `mission_state.active_route` carries the `status`,
  `reason_code` and `detail`, with empty paths and an empty `route_id`.
- If the environment variable `MGE_CONTROL_TOKEN` is set, `POST` requires
  `Authorization: Bearer <token>`. Set it before binding to anything other
  than localhost.
- Allowed browser origins come from the `cors_origins` parameter
  (default `http://localhost:5173`).

`tests/contracts/test_gateway.py` checks this contract without ROS;
`tests/integration` checks the ROS-to-HTTP flow against MOCK producers.

### 6.2 Recorded packages

A recorded run is a directory of static files that a web client reads with
plain HTTP `GET`, with no gateway and no ROS graph. It is written by the
`replay_recorder` node (`record:=true` on the launch file).

| File | Content |
|---|---|
| `<run_id>/manifest.json` | Envelope plus `recorded_from`, `source_mode`, `clock_source`, `time_start_sim_s`, `record_count`, `event_count`, `terrain_meta`, `agents`, `files` |
| `<run_id>/timeline.jsonl` | One record per line, in arrival order |
| `<run_id>/snapshot.json` | Final state, same shape as `GET /api/run/{run_id}/snapshot` |
| `<run_id>/public_rasters.json` | Optional. Public prior and, per recorded map version, belief, sigma and observed cells (`mge-public-rasters-1.0.0`, docs/REPLAY_CONTRACT.md) |

- Every file and every record says `mode: "REPLAY"`. A client must show
  `REPLAY` for this data and must not present it as a live computation.
- `recorded_from: "LIVE"` only says the records came off a running graph.
  `source_mode` says who produced them, with the rules of section 6.1; show
  `REPLAY · MOCK` or `REPLAY · SIMULATION` accordingly. Packages recorded
  before the field existed (the pinned sample included) lack it; their source
  is then read from the terrain metadata, or is `UNKNOWN`. `check_replay`
  rejects a package that says `LIVE`, or anything but `MOCK` over MOCK terrain.
- A timeline record has the shape of a WebSocket message: the envelope,
  `type` (`event` | `state` | `terrain_meta`) and an object of that name, so
  live messages and replay records can share one handler.
- `timestamp_sim_s` is the running maximum of accepted message stamps, so it
  never decreases along the arrival-ordered file. Each payload retains its
  original `header.stamp`, including for late messages. Replay time is
  `timestamp_sim_s - time_start_sim_s`.
- `clock_source` is `sim` when the run used `/clock` and `system` when no
  simulator was running; in that case the stamps are wall-clock seconds.
- Events and states travel on different topics, so a state may be recorded
  slightly before the event that caused it. Late events are retained in arrival
  order; reconstruct the logical history by `seq`, as in `snapshot.events`.
  Event IDs and positive uint64 sequences must both be unique within a run.
  The store rejects conflicting/reused sequences, and the offline validator
  detects them in altered packages without rejecting valid late deliveries.
- A mission state identical to the previous one, apart from stamps, is not
  recorded again. Duplicates, older states and data of another run are
  dropped, as in the gateway.
- An existing run directory is never overwritten.
- `public_rasters.json` appears, and `files.public_rasters` names it, once the
  run has published the prior and one complete batch (metadata, belief, sigma,
  observed under one stamp). A version whose batch never completes is absent,
  never interpolated; the offline oracle then refuses the package. Only public
  topics are recorded; NoData cells are `null`.
- `ros2 run mge_gateway check_replay <dir>` validates a package offline,
  including the raster attachment when the manifest names it.

`data/sample/replay/mock-vertical-001` is a sample package recorded from the
mock vertical (goal, route, simulated observation, replan). It contains mock
data only.

The recorder writes the public raster attachment and the web loader reads it
plus the closing snapshot. Strict conversion checks identities, counts, versions,
route immutability and closing history; recorded non-flat Jezero packages are
supported. The candidate highlights `recorded-recovery-001` while preserving its
recorder run ID and exact files. The scripted demo remains a distinct illustrative
example. GitHub Pages serves static web/replay; ROS and FastAPI require a separate
host. Source MOCK/replay and a final READY state remain distinct from a validated
LIVE or scientific COMPLETE mission.

Build all eight ROS definitions on Jazzy, run the imported ROS contract checks,
and then verify grid/frame alignment, stale responses, duplicate observations,
clock consistency, service-to-route flow and replay without backend. Writing
these types and passing static checks is not evidence of an E2E mission or
physical safety. Preserve commands, run IDs and outcomes in evidence records.
Interface changes update this ICD, consumers, tests and versions together.

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

**Default compatibility and published experimental recovery:**
The default planner requires XY cell centres with 1e-6 m tolerance and rejects
continuous starts with NON_CELL_CENTER. Main also contains the explicit
experimental connector/recovery integrated through PR12/PR21; it never silently
rounds telemetry. EFFICIENT remains ERROR/MODE_NOT_SUPPORTED. Search effort and
unresolved terrain may return UNKNOWN. Surface z does not certify drone altitude.

### Opted-in ground-start connector — published implementation, owner gates retained

Python `allow_continuous_start=False` and ROS/launch
`allow_continuous_starts=false` remain the defaults. An explicitly selected
experimental recovery retains the supplied continuous human/rover XYZ through
a validated connector. This software implementation and its recorded MOCK
consumer evidence do not approve scientific coefficients, physical safety or
contract freeze. See [continuous recovery](mission_replay_recovery.md).

- With the opt-in, human/rover START only may be continuous;
  goals/bases stay centred. Required return from a continuous start needs an
  explicit centred base; drone continuous starts remain unsupported.
- Connect only to the containing cell centre. No nearest-free-cell escape or
  uncosted snapping is permitted. The full segment stays in its convex cell,
  admissible under the selected public-map policy and independent profile.
  Swept footprint checks include forbidden/unknown/NoData/sigma cells, agent radius
  plus localization allowance, map bounds, blocked corner contact and directed
  slope/step limits. At least five distance samples (spacing <= resolution/4), minus half sample spacing and obstacle
  square circumradius conservatively bound clearance BETWEEN samples, not only at
  endpoints. See [MODEL.md](../src/mge_planning/MODEL.md) for proof boundaries.
- Connector 3-D distance, time, energy and human oxygen use the existing profile
  equations and initialize the first A* label BEFORE budget/reserve pruning.
  Completed travel is not charged again. Two-dimensional input adopts belief z.
  Centred three-dimensional human/rover starts must match belief z within 1e-6 m.
  An explicitly opted-in continuous start retains its supplied XYZ, including the
  interpolated height of an executed route. Its directed connection to the
  containing cell centre must satisfy the profile's step/slope bounds, swept
  footprint and uncertainty checks; all 3-D costs are charged. An impossible
  supplied height returns ERROR/INVALID_START_Z, without projecting telemetry.
  Unknown or inadmissible terrain cannot establish a valid height. This strict
  model-consistency tolerance is proposed, not a localization accuracy claim.
  Single-cell attachment and conservative bounds can reject physically possible
  starts; subcell relief, dynamics, physical safety and drone flight are unvalidated.
- No fields, names, types, units or enums change. The first outbound Point may be
  off-centre; the second is its attachment centre. Consumers must preserve both.
  Existing cost fields include that segment. start_connector metadata is Python-only.
- Affected consumers: MissionManager/current-pose request generation, executor/
  supervisor path following, gateway/replay serializers and viewer route display.
  Published recovery evidence covers the actual MOCK executor/planner/recorder
  stop/replan/resume/return path. The older [PR12 review audit](pr12_review_corrections.md)
  preserves historical failures; [the recovery handoff](mission_replay_recovery.md)
  identifies the later software cut. Three-role scientific mission acceptance
  remains pending; rc.2 F/E consumer proof is recorded in runtime-v1.
- F03.4 is a ROS-independent recommendation policy, not MissionManager authority.
  A contingency RETURN candidate uses goal=base, require_return=False, service=0
  and outbound_path for that one leg. Contingency may abandon unfinished SERVICE
  as well as OUTBOUND after a proven primary failure. Mission must explicitly adopt it and preserve
  RETURN context. KEEP on an irrelevant map update never overrides the mandatory
  MissionManager map-version invalidation gate above. Supervisor owns physical stop.

**Jesus review required:** confirm current-pose and snapshot association, path
consumers, RETURN-context transport, authorization/invalidation and stop feedback;
run the combined real consumer tests before approving any baseline extension.
**David review required:** approve terrain/profile assumptions, uncertainty margins,
resource/service accounting and conservative treatment; numerical science/search
model agreement remains pending. Neither unit tests nor this merge approve it.
The current scientific-model blocks and all other main agreements below are retained.

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
run manifest/evidence. Current types remain unchanged in this cut. The existing
service cannot distinguish equal-duration activities or carry the complete waiting/
remaining-service/model context; the [context/evidence proposal](audit_cost_execution_gaps.md)
records the justified additive interface decision still required with all consumers.
Neither provenance text nor a model-agreement flag supplies that missing binding.

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
Main's public replay/build excludes reference arrays; evaluator loading is
restricted to the separate development-only/private source. Earlier rc.1
publication findings describe the older fixture/history. Continue auditing final
bundles and network loads; a hidden toggle alone never isolates public data.
NoData padding for legacy shape compatibility is not evaluator truth.

Independent profiles are `mock`, `integration`, `simulation` and `live` in
`profile.launch.py`. Exactly one planner and one mission service provider may
run. MOCK uses deterministic interface-conforming producers; integration uses
real planner/mission with labelled simulated agents; simulation additionally
needs the real Gazebo backend. Live is unavailable. Launch requires explicit
owner-reviewed receipt/configuration and executable/service preflight. Published
provider implementations do not acquire approval merely by starting. The legacy
profile receipt still identifies baseline 1.0.0-rc.1; this rc.2 record does not
silently upgrade receipts or promote illustrative models. See
[launch profile gates](LAUNCH_PROFILES.md). A service-availability race still
requires a dedicated ROS_DOMAIN_ID and a single launcher per run.

See [baseline test ledger](CONTRACT_BASELINE.md) for all twelve requested checks.
Generated interfaces must compile and be inspected on Ubuntu 24.04/Jazzy;
Gazebo Harmonic execution and actual producer replacement are separate pending
acceptances. No successful build, contract harness, MOCK or replay is a complete
mission demonstration. Freeze remains pending Daniel/Diego/Jorge/David/Jesus
review of units, snapshots, resources, event/reason vocabulary and consumer evidence.

## Current audit and historical evidence

This rc.2 audit uses published main `6bcf208` and the refreshed owner refs in
[the source lock](contract_baseline.json). Main includes the recorder's public
rasters, strict web package/snapshot consumer, continuous MOCK recovery and
later owner science/data contributions. The rc.1 audit at `004b3b2`, integration
`45a4590` and UX `d649e2e` is historical; its missing-raster/public-reference/
scaffold statements are superseded by those integrations.

The PR28 cut publishes causal observation protection and explicit
estimated-terrain policy, and highlights an exact recorder package. Its fresh
ROS/browser results are captured in runtime-v1. Published callback
scheduling/readiness corrections address earlier starvation cases; bounded
SEARCH_LIMIT remains inconclusive and full-terrain latency is not certified.

The [new exact-main cost comparison](../evidence/audit-reconciliation-20261115/cost/README.md)
retains one agreement and six disagreements with authorization BLOCKED. Typed
activity/context/progress, opportunistic work, three-role execution and scientific
success remain open in [the cost/execution proposal](audit_cost_execution_gaps.md).
No replay, proposed policy, passed build or model diagnostic closes those gates.

## Mission provider substitution cut

The mission-service handoff publishes the existing real MissionManager without
new message/service fields, alternate science policy or a replacement planner.
The vertical launch selects mission:=mock|real exclusively; real selection
requires explicit science/mission configuration, use_sim_time=true and an
external /clock. Illustrative opt-in does not approve models. The real manager
retains profile approval, MODEL_NOT_AGREED/MODEL_MISMATCH, current run/map/pose,
return reserve, idempotency and logical stop checks. The mock provider remains
available for explicitly labelled contract tests. See
[configuration and consumer proof](mission_integration_handoff.md).


## Optional auxiliary visual-context topics (PR38 candidate)

See [auxiliary schema1.0.0](AUXILIARY_LAYERS.md) for the optional immutable CTX
DN and categorical display layers from data_node. Their OccupancyGrid values
are color codes, never canonical traversability or navigation authorization.
They remain separate from the stamped belief batch and require the sidecar
prior-hash/full-georeference binding. No canonical message/service field or
raster/replay version changes; scientific and consumer review remain pending.
