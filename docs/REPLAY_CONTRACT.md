# Canonical replay and deterministic viewer adaptation

Contract: recorder/web JSON **1.0.0**, ROS **ICD-ROS2-V1** unchanged.
The canonical recording is `manifest.json`, `timeline.jsonl`,
`snapshot.json`. This document adds a tested adapter; it does not merge or
replace either owner's branch and does not declare mission acceptance.

## Inspected implementations and immutable fixture

- Gateway: `feat/integration` at
  `d28f3e23f268d50c6c55f2b1f85a1cadbe9281ed`.
  Recorder and live WebSocket share records of type `terrain_meta|state|event`.
- Viewer: `feature/web-replay-viewer` at
  `73f22dba432ed69c351699c1d712f5d515df4c78`. See the branch inventory in
  [CONTRACT_BASELINE.md](CONTRACT_BASELINE.md).
  Its `mge-web-0.1-draft` format remains a compatibility target:
  `manifest.json`, `timeline.json`, `routes.json`, `rasters.json`.
- Three byte-for-byte gateway fixture files are pinned under
  [tests/fixtures/replay](../tests/fixtures/replay/provenance.json), with full
  source commit, paths and SHA-256 digests. They contain MOCK straight-line
  routes, 16 records, 9 events and map versions 1/2; they are not observations
  or verified planner results. Original source AI-use declaration identifies
  Claude Code (Anthropic); preservation of this fixture is declared in the
  project AI-use register. No images, video or audio are introduced.

## Implemented adapter

[contract_replay.py](../src/mge_gateway/mge_gateway/contract_replay.py) exposes:

```python
from mge_gateway.contract_replay import read_package, to_viewer

manifest, records, snapshot = read_package("path/to/recorded/run")
converted = to_viewer(manifest, records, snapshot)
assert converted["status"] == "NOT_READY"  # existing recorder lacks rasters
assert converted["reason_code"] == "PUBLIC_RASTERS_REQUIRED"
# Passing an explicit, validated public_rasters attachment enables READY.
# READY means serialization complete, never mission acceptance.
```

The adapter produces the four legacy JSON objects as dictionary entries
`manifest`, `timeline`, `routes`, `rasters`. Persist them only when
`status=READY`; use strict JSON (`allow_nan=False`) and refuse overwrite.
`write_package` is an offline fixture encoder for recording round-trip
tests, not a replacement for Jesus's ROS recorder.

| Canonical data | Viewer adaptation |
| --- | --- |
| Outer recorded timestamp | Subtract manifest `time_start_sim_s` for frame/event replay offset; preserve source clock metadata |
| ROS message `header` | Flatten to `timestamp_sim_s`; retain `timestamp_source_s` for traceability |
| TerrainMeta header frame | `frame_id=map`; ENU values and row order unchanged |
| MissionState `active_route` | Preserve complete candidate only when nonempty authorized `route_id`; collect routes by ID |
| Empty default ROS route | Omit optional viewer `active_route`; never render numeric defaults as measured results |
| Agent/route resources | Preserve numbers and JSON null exactly; no model or parameter conversion |
| Canonical schema 1.0.0 | Compatibility manifest/timeline schema `mge-web-0.1-draft`; canonical inputs untouched |
| `recorded_from=LIVE` | Retain original field, derive `source_mode=MOCK` only from explicit MOCK terrain evidence; otherwise UNKNOWN |

The system-clock fixture is displayed as **REPLAY / MOCK**, never simulated
clock dynamics or verified LIVE. Relative replay time does not alter path costs,
resource estimates, geometry or source timestamps. Mission state snapshots may
arrive before their matching events; event sequence and arrival time remain
separate concepts. The adapter does not invent future tasks/POIs/control points.
It preserves the viewer's scene/assets/layers/agents/timeline implementation.

## Public raster attachment

The existing recorder records no rasters. Missing arrays produce NOT_READY
while state/routes/events remain convertible; no flat terrain is synthesized.
Daniel supplies one public attachment with:

- `schema_version: mge-public-rasters-1.0.0`;
- `run_id`, `dataset_id`, `rows`, `cols`;
- `terrain_geometry`: exact `dataset_id`, rows, cols, ENU origins, resolution,
  CRS, planetary origin latitude/longitude and vertical datum from TerrainMeta;
- `prior`: immutable row-major public heights, number or null per cell;
- `versions`: exact string keys for every recorded MissionState map version,
  each containing `belief`, nonnegative `sigma` and distinct in-bounds
  `observed` linear cell indices.

This is the adapter attachment representation, not a new ROS raster format or
replacement dataset manifest. Dataset provenance, hashes, licenses, NoData masks
and three georeferenced control points remain required by the dataset contract.
Version fallback to a nearest available raster is prohibited for integration.
Geometry changes need a new dataset/run adapter; two provisional crops cannot
be combined. The converter requires matching identity, geometry, dimensions and
all consumed versions. It rejects evaluator/reference keys recursively.

For compatibility with Jorge's required `RasterSet.reference` field, output
contains **only a cell-length all-null NoData array**, plus
`reference_available=false`. No evaluator values are accepted or exported.
The null array is absence of data, not a synthetic reference surface.

## Remaining viewer and recorder gates

Jorge must consume the converter output or port the same rules into the
existing adapter, visibly show REPLAY plus source MOCK/UNKNOWN, show NOT_READY
and ERROR reasons, and disable evaluator selection for public bundles.
The current TypeScript `TerrainMeta.nodata_value: number` must permit null
because the source ROS NaN becomes JSON null. Existing illustrative fixtures
must remain preserved until conversion is accepted, but their hidden synthetic
reference must not be published as a downloadable public resource. A query
parameter hiding an already downloaded reference is not isolation.

Jesus must record explicit source provenance (MOCK/SIMULATION/LIVE/UNKNOWN)
instead of relying on `recorded_from=LIVE`, and add public raster recording
without exposing evaluator data. No source metadata is silently rewritten.
A live connected process is insufficient evidence of a valid LIVE mission.

The 1.0.0 adapter is deliberately strict about shared run identity, monotonic
record clocks/map envelopes/state sequences, unique event IDs/sequences, route
identity and current map, final snapshot consistency and standard JSON.
An unsupported geometry change fails closed instead of resampling.

## Verification and limits

`python -m pytest tests/contract/test_replay_conversion.py` tests the original
pinned recording, deterministic conversion, exact coordinate/resource/ID
preservation, offline encoding/readback, no-overwrite, malformed tokens,
duplicates, stale routes, cross-run data, raster/version/geometry mixing and
reference isolation. The generated flat attachment exists only inside a test
as an explicitly MOCK fixture.

These are executable offline serialization/adapter checks. They do not prove
Jorge's unchanged UI has adopted the contract, that raster recording is
implemented, that a real planner accepted these routes, or that a mission ran.
