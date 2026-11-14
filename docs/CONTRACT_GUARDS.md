# Contract guard harness and acceptance boundary

The additive helpers in `src/mge_bringup/mge_bringup/contract_guard.py` are
executable boundary examples for ICD reconciliation. They do not subscribe to
ROS, fuse observations, estimate resources, select scientific tasks, authorize
routes or publish a physical stop. The existing producers and consumers remain
in their owners' branches. Passing these tests establishes harness behavior;
owner integration and mission acceptance remain pending.

## Checks provided

| Helper | Contract checked | Evidence |
| --- | --- | --- |
| `GridGeometry`, `enu_to_three` | SW origin, south-first row-major order, ENU/Three.js transform, explicit rejection of continuous XY poses | Three asymmetric synthetic control points and off-centre cases in `tests/contract/test_baseline_guards.py` |
| `ros_json` | Generated ROS objects or ROS-shaped trees; explicit NaN to null for non-human oxygen and typed TerrainMeta NoData; other nonfinite values rejected | ROS-shaped double/native array tests and strict JSON serialization; actual generated AgentState, RouteDecision, TerrainObservation and TerrainMeta checks in `tests/contract/test_generated_conversion.py` require a built Jazzy workspace |
| `IdempotencyLedger` | Run-scoped request/event/observation IDs; identical duplicate has no second effect; conflicting duplicate rejected; uint64 increasing event sequence | Duplicate, conflict, foreign-run and sequence tests |
| `SnapshotLedger` | Complete immutable batch, stamp/run/version/frame identity, shape and NoData mask consistency; old versions and retired runs rejected | Complete/incomplete, mixed layer identity, changed layer, reused stamp and NoData tests |
| `candidate_rejection` | Current run/map, echoed IDs, FEASIBLE gate, full return path, complete cost plus reserves; model agreement denied by default | All six route states, resource limits, numerical mismatch and return tests |
| `logical_stop_on_map_change` | Stale active route requires invalidation and logical stop | Map-update test; applying the stop in ROS remains Mission Manager/SimAdapter work |
| `request_candidate` | One consumer injection seam for a canonical PlanRoute-shaped response | Two deterministic MOCK providers with fields checked against `.msg`/`.srv`; real-provider hook skips until PR #2 is integrated |
| `assert_public_payload` | Nested explicit hidden-reference/evaluator/future-task keys and nonpublic roles rejected | Nested-field tests plus exact allowlist of complete snapshot fields |

The snapshot argument is a **test-side DTO**, not another wire schema. Its
`geometry` uses `GridGeometry` fields. It contains `run_id`, `dataset_id`,
`map_version`, `frame_id`, `stamp` and `layers`; layers contain identical
run/version/frame/stamp and flat south-first values. The complete three-agent
fixture requires belief, sigma and human/rover/drone masks. `None` represents
NoData within this harness only; actual `32FC1` encoding follows the ICD and
owner adapters. A single-agent ROS planner may require only its applicable mask.
CRS, datum, licensing, product hashes and georeferenced control points must also
be checked against Daniel's dataset manifest; this DTO does not replace it.

A duplicate observation is recognized here, but no observation is applied by
this harness. Mapping's footprint-only update and once-per-observation version
increment must be demonstrated with the real mapping producer. Layers received
before metadata and DDS delivery ordering require the real snapshot adapter.

## Resources and authority

`candidate_rejection` accepts already normalized ROS field names. Non-human
oxygen is JSON `null`, human oxygen is finite and nonnegative. It requires a
return and checks total outbound/service/return costs, service included in total
time, remaining reserves and an independently supplied science-model audit.
Generated `TerrainMeta.nodata_value=NaN` converts explicitly to JSON `null`;
a ROS-shaped dictionary requires `message_type="mge_interfaces/msg/TerrainMeta"`.
That type context applies only to its direct NoData field, never nested arbitrary
data; infinity and nonfinite elevations/resources still fail.
The numeric comparison uses relative tolerance `1e-5` and absolute tolerance
`1e-3`, matching the inspected mission audit at `cf292107277e1aaf130d6c0ecd33904a22638f4f`.
These are floating point reconciliation tolerances, not scientific uncertainty
or operational safety margins.

A caller must supply `model_agreed=True` only after David and Diego approve a
recorded comparison that Jesus can integrate. Store science/planner model IDs,
configuration hashes, map/dataset version, request ID, itinerary, service
activity/duration, independently recomputed costs, approval reference and
rejection reason with the run evidence. The helper does not authenticate an
approval or derive costs; an empty rejection reason does not authorize execution.
The Mission Manager remains the only route authority.

The planner at `34c515b6b86f73336844e8b3614c70b144574ec3` uses 3-D edge
length, direction-specific slope factors, per-distance energy and constant human
oxygen rate. Mission's `mge-science-1.0.0` at
`cf292107277e1aaf130d6c0ecd33904a22638f4f` uses activity/terrain-specific
human metabolic costs, rover tractive/auxiliary costs and drone power/time costs.
The proposed profile export cannot prove these formulations equivalent. Keep
`MODEL_NOT_AGREED`, non-approved profiles and operational feasibility blocked
until the agreed numerical matrix covers flat/uphill/downhill/zero-length,
service/waiting, each agent, round trip, reserves and rejection boundaries.

## Limits and reproducible checks

```sh
python -m pytest tests/contract/test_baseline_guards.py tests/integration/test_provider_substitution.py
```

The real-provider test is designed to exercise Diego's actual module through the
same consumer seam after it is integrated. On a scaffold checkout it explicitly
skips, with the reason recorded; it does not reimplement A* or present a second
test double as a real planner. Generated ROS compilation/service transport,
provider-exclusive launch profiles and an actual map-change stop still need
ROS 2 Jazzy evidence on Ubuntu 24.04.

The public-payload guard is defense in depth. It cannot recognize evaluator data
renamed as belief or hidden in arbitrary binary content. Keep evaluator assets
outside planner and public web roots, audit every allowlisted artifact and hash,
inspect build outputs and retain scientific provenance. No reference DEM is
included in this harness or its synthetic fixtures.
