# Optional public visual context — auxiliary schema 1.0.0

These optional layers describe the existing Jezero128m control (32x32 cells at
4m); they are separate from the canonical prior/belief/sigma/observed and
traversability contracts. They do not package or validate Bunsen512/1024.
The schema is an initial PR38 proposal, not an ICD freeze or science approval.

`data_node` publishes the following optional latched topics with the immutable
prior's header. `publish_aux_layers=false` disables them. The prior has the
same bytes, absolute elevations and datum as before this optional extension.

| Topic | Existing ROS type | Meaning |
|---|---|---|
| `/mge/terrain/aux/ctx_ortho` | `sensor_msgs/Image`, mono8 | Cell-aligned CTX DN; south-to-north array rows |
| `/mge/terrain/aux/surface_zones` | `nav_msgs/OccupancyGrid` | Estimated DN/slope visual category, not obstacle probability or a planner mask |
| `/mge/terrain/aux/geology_zones` | `nav_msgs/OccupancyGrid` | Coarse USGS SIM3464 geological unit color category |

The sidecar is required to interpret these native ROS messages: they carry no
new run/dataset/version/legend fields. Bind context to the exact public prior
SHA-256, frame, dataset, full grid and vertical datum from the validated sidecar;
do not join them to a belief batch by topic, arrival order or its map-version
stamp. `mapping_node` remains the sole canonical TerrainMeta publisher. These
topics are not consumed by mapping, planner, recorder or the ordinary web replay
in this cut. A ROS consumer test checks the actual provider's bytes and geometry;
it does not establish a new replay or navigation consumer.

`aux_layers_manifest.json` requires schema_version `1.0.0`, status `ready`,
classification `ESTIMATED_VISUAL_CONTEXT`, navigation_authorization `false`,
region_id, frame_id, row_orientation, CRS, vertical_datum,
aligned_terrain_npz_sha256, grid geometry and three path/hash records. Grid
contains rows/cols, resolution_m, origin_x_m/origin_y_m and planetocentric
latitude/east longitude. Latitude/longitude and horizontal grid origin do not
recenter elevations: height remains metres above the primary vertical datum.
Ready means the visual package is complete and internally consistent.

Every declared file must resolve inside the public bundle, never through an
external/evaluator symlink. NPZ, PNG and geology JSON hashes are mandatory.
Geology JSON is hashed after CRLF-to-LF normalization for Git checkout portability;
NPZ and PNG use their exact bytes. The loader validates the public-prior binding,
array names/dtypes/shapes, finite cell-centre axes, category legends, color codes
and NoData before publishing. An entirely absent optional bundle returns None;
a partial, corrupt, unbound or incompatible bundle is rejected. The message
helper independently rechecks alignment with its selected TerrainTile.

NPZ contains only ctx_ortho_dn:uint8, ctx_ortho_norm:float32,
ctx_ortho_valid_mask:bool, slope_deg:float32, geology_unit_code:int16,
geology_rviz_occupancy:int8, surface_zone_code:int8,
surface_zone_rviz_occupancy:int8, x_m:float32 and y_m:float32. Raster shape is
(rows,cols), x_m is (cols,), y_m is (rows,). Palette `-1/15/35/55/75/95` and
existing opaque category IDs are retained. They never mean canonical
traversability `-1/0/100`. PNG row0 is north; array row0 is south, explicitly.

The generator reuses the canonical public loader and requires its valid DEM
and SHA before any remote request or output creation. CLI grid overrides are
assertions of that same geometry; a new crop needs its own canonical public
terrain manifest. Missing/mismatched DEMs are never replaced with zeros.
NoData is kept unknown; prior sigma and observed coverage are not changed.

The surface categories are unvalidated visual proxies from estimated orbital
slope and local DN percentiles. DN is not calibrated reflectance. Brightness
does not identify geological facies; slope alone does not certify agent passage,
a confirmed obstacle or drone flight altitude. Illustrative human/rover screening
thresholds remain unapproved; there is no traversable_agents declaration.

Geology comes from [USGS SIM3464](https://doi.org/10.3133/sim3464), scale1:75,000.
Its reported relative positional accuracy against the controlled CTX DEM is
approximately100–200m, comparable to or larger than this control window. The
raster is regional context, not independently registered cell-level geology.
CTX image sources, native6m spacing, resampling and source hashes remain in the
manifest. The computational4m grid does not improve native resolution.

The reviewed bundle changes interpretation/contract metadata only: acquired
NPZ, PNG and geology JSON bytes and the acquisition timestamp are preserved.
AI-assisted processing and interpretation are declared in manifest metadata and
the project AI registers; public NASA/USGS values are not synthetic observations.
No scientific coefficients, mission authority, canonical ROS fields, raster/replay
versions, physical-safety approval or LIVE claim are changed.
