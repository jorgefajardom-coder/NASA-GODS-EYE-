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

- `/clock` from Gazebo when it runs, with `use_sim_time=true`. Mission headers use simulated time when a simulator is active. The separate
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
does not subscribe to it. This topic is a proposed additive change (no message
or field changes) pending Daniel's producer review and Jorge's consumer review. The prior is immutable within a run; the belief is never the hidden
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
before changing belief. Non-human oxygen NaN is the explicit non-applicable sentinel. The integrated
planner also emits NaN unavailable metrics on non-FEASIBLE RouteDecision; typed
status-conditioned serialization maps only those unavailable fields to null.
Never replace invalid FEASIBLE metrics or infinities with null silently. An accepted observation changes its footprint and increments the
map version once. Defining fields does not implement these checks.

| Service | Request fields | Response fields |
| --- | --- | --- |
| `PlanRoute` | `run_id`, `request_id`, `agent_id`, `agent_kind`, `start`, `goal`, `return_to`, `require_return`, `mode`, `map_version`, `service_time_s`, `time_budget_s`, `energy_budget_wh`, `oxygen_budget_l`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` | `decision` (`RouteDecision`) |
| `SetMissionGoal` | `request_id`, `run_id`, `primary_agent_id`, `base`, `goal`, `mode`, `time_budget_s`, `energy_budget_wh`, `oxygen_budget_l`, `reserve_time_s`, `reserve_wh`, `reserve_oxygen_l` | `accepted`, `request_id`, `run_id`, `mission_state`, `reason_code`, `detail` |

Service positions and RouteDecision paths are `geometry_msgs/Point` values in
`map`, not Pose or nav_msgs/Path. The active-path topic remains `nav_msgs/Path`.
SetMissionGoal permits an empty run ID to mean the current run; resolve it
before events/replay. This candidate integrates the real MissionNode from
feat/mission at8f69f62 beside main's real planner and gateway. The real manager
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
The planner's Missing profiles keep planner results UNKNOWN/PROFILE_NOT_READY; illustrative
profiles require explicit allow_illustrative_profiles. Changes during search
invalidate the snapshot token and discard stale candidates. Rejected immutable
batches require a fresh version/stamp. `snapshot_contract_confirmed` defaults false. Daniel/Jesus must
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

The ROS-backed gateway and recorder below are implemented in PR #3. Until a
mission state arrives, inactive identifiers, mode, map version and timestamp
are null with status NOT_READY and reason NO_ACTIVE_RUN. No running process
alone establishes a mission.
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
  (`MissionEvent`) or `"state"` with a `state` object (`MissionState`).
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

The recorder writes the public raster attachment; the viewer does not read it
yet (it still rejects non-flat terrain packages), which is Jorge's next step. GitHub Pages serves
static web/replay only; ROS and FastAPI require a separate host. Transport
availability never establishes validated LIVE mission provenance.

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

## Latest concurrent integration observations

Final audit incorporates main `004b3b2` (PR #2 merged by Jesus), integration
`45a4590` and the advanced web continuation `feat/ux` at `d649e2e`.
`feature/web-replay-viewer` at `73f22db` is its verified ancestor; the newer UX
branch is no longer the old scaffold. Preserve both histories and latest work.
Jesus already has a real-planner/MOCK-mission vertical with coherent synthetic
batches; Jorge already has a gateway replay adapter/run selector. Harden those
existing consumers against these contracts, rather than reimplementing them.

The new web adapter synthesizes flat 0m arrays from a name/source containing
"flat". Such a display may only be an explicit illustrative MOCK fallback,
never recorded terrain or scientific observation. Canonical strict replay still
returns NOT_READY without actual matching public raster attachments. The new
web consumer must validate snapshot/counts/identities/versions and duplicate
route content. The demo still publishes 10,000 evaluator reference values;
that final-bundle isolation blocker remains unresolved.

Integration-owner observations report callback starvation with 1Hz repeated
batches on grids >=60x60, default2s SEARCH_LIMIT on long queries, and short-budget
searches returning UNKNOWN/SEARCH_LIMIT before proving insufficiency. Preserve
UNKNOWN semantics and validate latency/load before asserting resource proof.
The current mock mission/terrain do not implement full scientific audit,
conflicting-request payload checks or real footprint fusion. Their tests are
integration harness evidence only. Latest source/evidence is in the matrix.

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
