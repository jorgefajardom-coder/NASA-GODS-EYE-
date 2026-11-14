# Canonical replay and deterministic viewer adaptation

Contract: recorder/web JSON **1.0.0**, ROS **ICD-ROS2-V1** unchanged.
The canonical recording is `manifest.json`, `timeline.jsonl`,
`snapshot.json`. The existing TypeScript viewer adapter remains Jorge's
production integration point. The additive Python helper is an offline
contract oracle/export helper; it neither replaces that adapter nor declares
mission acceptance.

## Inspected implementations and immutable fixture

- Gateway: `feat/integration` at
  `45a4590f8e8330a3896c170ec2c9ee272ae0b423`.
  Recorder and live WebSocket share records of type `terrain_meta|state|event`.
- Original viewer branch: `feature/web-replay-viewer` at
  `73f22dba432ed69c351699c1d712f5d515df4c78`.
- Verified viewer continuation: `feat/ux` at
  `d649e2e5632dddcf242f403abe0013be29d2f907` descends from that original
  viewer head. It contains the advanced scene and, since commit `89216fc`,
  `web/src/data/gatewayReplay.ts`, canonical JSONL loading and a saved-run
  selector. Vite serves/copies the original canonical sample from
  `data/sample/replay`; no second sample copy is needed under `web/public`.
  Preserve both the named original branch and the advanced continuation;
  confirm Jorge's intended PR head before changing the historical handoff.
- The compatibility fixture format remains `mge-web-0.1-draft`:
  `manifest.json`, `timeline.json`, `routes.json`, `rasters.json`.
  Canonical recorder input remains 1.0.0. See the current branch inventory in
  [CONTRACT_BASELINE.md](CONTRACT_BASELINE.md).
- Three byte-for-byte gateway fixture files are pinned under
  [tests/fixtures/replay](../tests/fixtures/replay/provenance.json), with source
  commit `d28f3e23f268d50c6c55f2b1f85a1cadbe9281ed`, paths and SHA-256
  digests. The fixture source stays immutable despite later branch advances.
  It contains MOCK straight-line routes, 16 records, 9 events and map versions
  1/2; these are not observations or verified planner results. The original
  source AI-use declaration identifies Claude Code (Anthropic); fixture
  preservation is declared in the project AI-use register. No images, video
  or audio are introduced.

## Offline oracle and compatibility export

[contract_replay.py](../src/mge_gateway/mge_gateway/contract_replay.py) exposes:

```python
from mge_gateway.contract_replay import read_package, to_viewer

manifest, records, snapshot = read_package("path/to/recorded/run")
converted = to_viewer(manifest, records, snapshot)
assert converted["status"] == "NOT_READY"  # recorder package lacks rasters
assert converted["reason_code"] == "PUBLIC_RASTERS_REQUIRED"
# Passing an explicit, validated public_rasters attachment enables READY.
# READY means serialization complete, never mission acceptance.
```

The oracle produces the four compatibility JSON objects as dictionary entries
`manifest`, `timeline`, `routes`, `rasters`. Persist them only when
`status=READY`; use strict JSON (`allow_nan=False`) and refuse overwrite.
`write_package` is an offline fixture encoder for recording round-trip tests,
not a replacement for Jesus's ROS recorder. Production browser loading stays
in Jorge's existing TypeScript adapter. Its conformance should be checked
against these fixture expectations, rather than implemented as another viewer,
planner or mission authority.

| Canonical data | Oracle/export adaptation |
| --- | --- |
| Outer recorded timestamp | Subtract manifest `time_start_sim_s` for frame/event replay offset; preserve source clock metadata |
| ROS message `header` | Flatten to `timestamp_sim_s`; retain `timestamp_source_s` for traceability |
| TerrainMeta header frame | `frame_id=map`; ENU values and row order unchanged |
| MissionState `active_route` | Preserve complete candidate only when nonempty authorized `route_id`; collect routes by ID |
| Empty default ROS route | Omit optional viewer `active_route`; never render numeric defaults as measured results |
| Agent/route resources | Preserve numbers and JSON null exactly; no model or parameter conversion |
| Canonical schema 1.0.0 | Compatibility manifest/timeline schema `mge-web-0.1-draft`; canonical inputs untouched |
| `recorded_from=LIVE` | Retain original field, derive `source_mode=MOCK` only from explicit MOCK terrain evidence; otherwise UNKNOWN |

The oracle labels the system-clock fixture **REPLAY / MOCK**. The current web
continuation already shows a REPLAY badge and a recorded MOCK disclaimer for
this sample; the LIVE link remains unavailable. Relative replay time does not
alter path costs, resource estimates, geometry or source timestamps. A wall
clock recording is not evidence of simulated dynamics. Mission state snapshots
may arrive before their matching events; event sequence and arrival time remain
separate concepts. Late events also remain in receipt order in `timeline.jsonl`
and the converted viewer timeline, with monotonic envelope timestamps and their
original source stamps intact. `snapshot.events` is the logical history sorted
by `seq`, so validators compare it against that sorted history rather than
requiring sequence-ordered arrival. Event IDs and positive uint64 sequences must
both be unique; duplicates and invalid sequences remain errors. This clarifies
existing JSON 1.0.0 behavior without changing fields or the ROS wire schema.
The oracle invents no future tasks/POIs/control points and
does not modify the scene/assets/layers/agents/timeline.

## Public raster attachment

The existing recorder records no rasters. In the strict oracle, missing arrays
produce NOT_READY while state/routes/events remain convertible; no flat terrain
is synthesized. Daniel supplies one public attachment with:

- `schema_version: mge-public-rasters-1.0.0`;
- `run_id`, `dataset_id`, `rows`, `cols`;
- `terrain_geometry`: exact `dataset_id`, rows, cols, ENU origins, resolution,
  CRS, planetary origin latitude/longitude and vertical datum from TerrainMeta;
- `prior`: immutable row-major public heights, number or null per cell;
- `versions`: exact string keys for every recorded MissionState map version,
  each containing `belief`, nonnegative `sigma` and distinct in-bounds
  `observed` linear cell indices.

This is the compatibility export attachment representation, not a new ROS
raster format or replacement dataset manifest. Dataset provenance, hashes,
licenses, NoData masks and three georeferenced control points remain required
by the dataset contract. Version fallback to a nearest available raster is
prohibited for integration. Geometry changes need a new dataset/run adapter;
two provisional crops cannot be combined. The oracle requires matching
identity, geometry, dimensions and all consumed versions. It rejects
evaluator/reference keys recursively.

For compatibility with Jorge's required `RasterSet.reference` field, output
contains **only a cell-length all-null NoData array**, plus
`reference_available=false`. No evaluator values are accepted or exported.
The null array is absence of data, not a synthetic reference surface.

The current TypeScript adapter has a separate illustrative behavior: it creates
zero-height prior/belief arrays when the dataset ID or source text matches
`flat`, with NoData uncertainty/reference. Preserve the existing MOCK display
while reconciling it; these generated display arrays are not recorded rasters
or observations. The next viewer PR must make this an explicit illustrative
MOCK rendering choice, rather than infer physical elevation from a name.
Data-bearing canonical replay acceptance still requires the actual public
raster attachment. The two behaviors are not declared equivalent.

## Remaining viewer and recorder gates

Jorge should harden the existing `gatewayReplay.ts` and
`replayAdapter.ts` against the oracle cases. The inspected adapter recognizes
a numeric start time and JSONL filename and checks replay mode, but does not
validate canonical schema/version, record/event counts, final `snapshot.json`,
nested agent/route run IDs, complete map/version association, stale active
routes or conflicting route identity. Filtering only outer record run IDs is
insufficient. Add those checks and preserve explicit NOT_READY/ERROR reasons.
The latest TypeScript `TerrainMeta.nodata_value` already permits null; no
additional type change is required for that field.

Evaluator isolation is still blocked on the advanced web branch: the demo
`web/public/replay/demo/rasters.json` contains **10,000 non-null evaluator
reference values**. `?evaluator=1` merely reveals a layer that is already
downloadable. Keep the illustrative fixture/history preserved, but remove
evaluator values from public build inputs and host evaluator assets in an
isolated process/mount before publication. Disable public evaluator selection.
The canonical MOCK recording's reference output is all NoData; that does not
resolve the separate demo leak.

Jesus must record explicit source provenance (MOCK/SIMULATION/LIVE/UNKNOWN)
instead of relying on `recorded_from=LIVE`, and add public raster recording
without exposing evaluator data. No source metadata is silently rewritten.
A live connected process is insufficient evidence of a valid LIVE mission.

A serializer defect remains on the inspected gateway branch:
`mge_gateway.store.to_json` maps **every NaN and infinity to null**, including
invalid pose, map and applicable resource values. JSON validity alone then
hides an invalid input. The strict boundary helper in
[contract_guard.py](../src/mge_bringup/mge_bringup/contract_guard.py) must be
adopted before that lossy conversion: permit NaN only for explicitly
non-applicable oxygen, NoData fields and status-conditioned unavailable route
metrics; reject infinities and other non-finite values. Applying validation
after broad null conversion cannot recover the original error. These helper
tests do not prove the existing gateway has adopted the stricter serializer.

The oracle is deliberately strict about shared run identity, monotonic record
clocks/map envelopes/state sequences, unique event IDs/sequences, route
identity/current map, final snapshot consistency and standard JSON. Unsupported
geometry changes fail closed instead of resampling.

## Verification and limits

`python -m pytest tests/contract/test_replay_conversion.py` tests the original
pinned recording, deterministic conversion, exact coordinate/resource/ID
preservation, offline encoding/readback, no-overwrite, malformed tokens,
duplicates, stale routes, cross-run data, raster/version/geometry mixing and
reference isolation. A recorder-to-oracle round trip additionally exercises a
late event, preserving source/arrival time and logical snapshot order; duplicate
sequences under distinct IDs and invalid uint64 values fail closed.
The generated flat attachment exists only inside a test
as an explicitly MOCK fixture.

The advanced web branch has existing `web/tests/gatewayReplay.test.ts` cases
for its canonical sample, recorded events, replanning, illustrative flat grid,
and foreign outer records. Their existence is separate from execution evidence
for this reconciliation. Extend these consumer tests for the stricter cases;
preserve the existing visual implementation and fixtures.

The Python checks establish offline serialization/oracle behavior. They do not
prove the advanced UI satisfies the stricter contract, that public raster
recording exists, that evaluator isolation is fixed, that a real planner
accepted the MOCK routes, or that a mission ran.
