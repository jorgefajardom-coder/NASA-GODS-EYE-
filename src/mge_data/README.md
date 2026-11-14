# mge_data

Owner: Daniel. Status: **scaffold; operational implementation pending**.

| Layer | Responsibility |
| --- | --- |
| R | R03, R04 |
| F | F01: import and align orbital products |
| L | SourceRegistry, GeoTransform, TerrainTile, ManifestValidator |
| P | Python core in `mge_data/core.py`; ROS startup in `mge_data/node.py` |
| V&V | Guide acceptance cases remain pending; record actual runs under `evidence/` |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_data data_node`.
This only starts a warning-only node; it does not claim to provide the planned ROS services or topics.
`core.py` imports without ROS so future unit tests can run independently.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract and next work

Input: an exact product manifest, raster and NoData mask, explicit planetary CRS,
origin, native resolution, datum and SHA-256. Output (pending): public TerrainMeta,
prior `32FC1` elevations in meters and regional context. No reference arrays belong
in this API. `load_public_terrain` deliberately raises `NotImplementedError`.

Daniel's first tasks: fill the sample manifest from real MRO and MGS products,
normalize a small Jezero cutout, record three control points, and demonstrate
NoData handling with both the planner and web consumers. MOLA cannot be presented
as local rock-scale detail. Acceptance cases: individual guide T-01 through T-04,
T-07 and T-08; preserve actual commands and outputs in run evidence.
