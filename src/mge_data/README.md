# mge_data

Owner: Daniel. **Implemented public terrain loader and ROS prior publisher.**
The earlier scaffold description is superseded by the implementation in main.
Scientific mission and physical traversal acceptance remain separate.

| Layer | Responsibility |
| --- | --- |
| R | R03, R04 |
| F | F01: import and align orbital products |
| L | SourceRegistry, GeoTransform, TerrainTile, ManifestValidator |
| P | Python core in `mge_data/core.py`; ROS startup in `mge_data/node.py` |
| V&V | Guide acceptance cases remain pending; record actual runs under `evidence/` |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_data data_node`.
The node publishes `/mge/terrain/prior` (`32FC1`). Mapping alone owns metadata,
version and the repeated coherent belief/sigma/observed/kind-mask batch.
`core.py` imports without ROS for ordinary Python tests.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract and next work

Input: an exact product manifest, raster and NoData mask, explicit planetary CRS,
origin, native resolution, datum and SHA-256. `load_public_terrain()` validates
hashes, shape, units, planetary CRS/datum, NoData and non-collinear controls;
returns public terrain and regional context; and refuses evaluator-reference
arrays. See [source records](../../docs/data_sources.md),
[manifest](../../data/sample/manifest.json) and
[processing provenance](../../data/sample/provenance_details.json).

The current `jezero_mvp` package is 128 m square, 32×32 at 4 m computational
spacing, ENU around 18.45°N/77.45°E. CTX supplies the 20 m native prior;
separately ingested MGS/MOLA supplies 463 m regional context. Neither resampling
adds native detail. HiRISE is evaluator-only. Initial sigma is 2.5 m and local
observed coverage is zero. The viewer's 2 km illustrative scene is distinct.

Verification: `python -m pytest tests/contracts/test_data_manifest.py
tests/mapping tests/contract/test_dataset.py`; ROS consumers include
`tests/integration/test_vertical_terrain.py`. See the
[current reconciliation](../../docs/audit_reconciliation.md) for exact evidence,
D-EST-01 candidate planning and remaining owner review. Imported orbital data
and a successful MOCK replay do not certify traversal or scientific completion.
