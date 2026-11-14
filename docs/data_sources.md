# Data source register and planetary provenance (Daniel)

Status: **Validated public multi-mission Jezero package (`status: "ready"`)** in [manifest.json](../data/sample/manifest.json) and [provenance_details.json](../data/sample/provenance_details.json).

This package supersedes the provisional CTX prior that `feat/planner` processed
for its own tests ([processing provenance](planner_provenance.md),
`data/planner_provisional/manifest.json`). The two crops share the origin and
the 4 m grid but are separate artifacts: never combine them by version alone.
See the [resource-to-result register](nasa_traceability.md). An imported
orbital product is not a locally verified corridor.

## 1. Multi-mission NASA / USGS sources ingested

All three sources were acquired via bounded HTTP 206 partial-content reads (`scripts/prepare_jezero_terrain.py`) and reprojected onto a Mars-local Equirectangular ENU grid (`frame_id: "map"`, `x = east`, `y = north`, `z = up`) on the `Mars_2000_Sphere` (`R = 3,396,190 m`) centered at `18.45° N, 77.45° E` (`32 × 32` cells at `4.0 m`, southwest origin `(-64.0, -64.0) m`, `row_orientation: "south_to_north"`). No terrestrial `EPSG:4326` / `WGS84` datum is used.

| Mission / Instrument | Role | Official Product ID & Citation | Source URL / DOI | Native Scale | Output Grid & Resampling | Artifact & SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| **MRO / CTX** | `prior` | `JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0` — Fergason et al. (2020), USGS Astrogeology | [DOI 10.5066/P906QQT8](https://doi.org/10.5066/P906QQT8) / [AWS PDS S3 GeoTIFF](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif) | `20.0 m` | `4.0 m` (`32×32`), GDAL NoData-aware bilinear | `data/sample/terrain.npz` (`ab2e9c916e23d96c25f343213249eb906ca2685ff977006915f09883fe226d91`); native window `[851, 797, 14, 13]` (`94b480899c835014617a91873fbd9f4b3fb7e7a137a9cea4214e93f34c67667c`) |
| **MRO / HiRISE** | `evaluation_reference` (isolated) | `JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40` — Fergason et al. (2020), USGS Astrogeology | [DOI 10.5066/P9REJ9JN](https://doi.org/10.5066/P9REJ9JN) / [AWS PDS S3 GeoTIFF](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif) | `1.0 m` | `4.0 m` (`32×32`), GDAL NoData-aware bilinear | Isolated in `data/reference/jezero_hirise_reference.npz` (`7bb9c85f28806d99064dc6413b6b74f65e07a9f2b1ef613ba12cbb5ea4af5680`); native window `[13388, 12932, 142, 135]` (`35a51c2fee7fac4502feabfd10de6b64a258e81a1e82b83360157fd49d36ae52`) |
| **Mars Global Surveyor / MOLA** | `regional_context` | `Mars_MGS_MOLA_DEM_mosaic_global_463m` (`urn:nasa:pds:mgs_mola_topography_derived::1.0`) — Smith et al. (2001), NASA PDS / USGS | [AWS PDS S3 GeoTIFF](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif) | `463.0 m` (128 ppd) | `4.0 m` (`32×32` regional context layer), bilinear | `data/sample/mola_regional_context.npz` (`b2341a639891359a9f7184171b923b8a83852ef0f3edd28bfd5862b8158db9f6`); native window `[32947, 9152, 13, 13]` (`4ada42b69c85f92839df58a195d16f3f3726fe021c3a9b0b5f019145f676b526`) |

- **Terms and credits:** Public domain U.S. Government / NASA / USGS planetary archive data ([USGS Copyrights and Credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)).
- **Mandatory NASA reference portals consulted:** [JPL Mars Trek](https://trek.nasa.gov/mars/) and [USGS-NASA Planetary Geologic Mapping Program](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars).

## 2. Regional MGS / MOLA contribution and vertical datum registration

Unlike relying solely on the string `"MOLA"` in the MRO/CTX filename, this package ingests the separate **Mars Global Surveyor (MGS) Mars Orbiter Laser Altimeter (MOLA)** MEGDR global topography mosaic (`Mars_MGS_MOLA_DEM_mosaic_global_463m.tif`, PDS bundle `urn:nasa:pds:mgs_mola_topography_derived::1.0`):

1. **Study-area selection:** MGS/MOLA regional altimetry across the western Jezero Crater basin (`native_min_m = -2636.0 m`, `native_max_m = -2422.0 m`, `native_mean_m = -2550.84 m` in the surrounding 13×13 MOLA pixel sector) situates the `18.45° N, 77.45° E` study tile inside the western delta/crater-floor transition zone.
2. **Vertical registration check:** Within the `128 m × 128 m` local tile, the MGS/MOLA regional surface averages `-2561.40 m` while the higher-resolution 20 m MRO/CTX stereo DTM averages `-2571.46 m` (mean difference `-10.05 m`, max absolute difference `12.71 m`), confirming consistent registration to the Martian MOLA areoid (`DeltaGeoid`) without any terrestrial datum substitution.

## 3. Shared ENU / planetocentric control points

Four non-collinear cell-center control points are verified at load time by `GeoTransform.verify_control_points` and recorded in [terrain.yml](../config/terrain.yml) and [provenance_details.json](../data/sample/provenance_details.json). Two off-diagonal points (`cp_se_offdiag` at `row=5, col=26` and `cp_nw_offdiag` at `row=25, col=6`) ensure that any row/column (`x/y`) transpose or north/south flip is immediately rejected:

| Control Point ID | Grid `(row, col)` | `x_east_m` (m) | `y_north_m` (m) | CTX Prior `elevation_m` (m) | `lat_planetocentric_deg` (°N) | `lon_east_deg` (°E) |
| --- | --- | --- | --- | --- | --- | --- |
| `cp_sw_origin` | `(0, 0)` | `-62.0` | `-62.0` | `-2570.634765625` | `18.4489540225` | `77.4488973463` |
| `cp_se_offdiag` | `(5, 26)` | `+42.0` | `-42.0` | `-2569.0053710938` | `18.4492914346` | `77.4507469589` |
| `cp_nw_offdiag` | `(25, 6)` | `-38.0` | `+38.0` | `-2572.0356445312` | `18.4506410830` | `77.4493241800` |
| `cp_ne_corner` | `(31, 31)` | `+62.0` | `+62.0` | `-2573.8408203125` | `18.4510459775` | `77.4511026537` |

## 4. Scientific and operational limitations

- **Orbital prior vs. local observation:** Finite pixels in the MRO/CTX prior (`~nodata_mask`) are **not** locally verified ground observations. On initial load, `observed_mask` is all `False`, and `BeliefMap.traversability_grid()` marks unobserved cells as `-1` (`UNKNOWN`), never `0` (`FREE`).
- **No synthetic resolution claim:** Resampling 20 m MRO/CTX or 463 m MGS/MOLA onto a 4 m computational grid does not create sub-20 m native topographic detail.
- **Evaluator reference isolation:** MRO/HiRISE 1 m reference arrays remain isolated in `data/reference/` (gitignored) and are blocked by `mge_data.core.load_public_terrain`.
- **No physical safety certification:** Even 1 m orbital DTMs do not resolve decimeter-scale hazards, regolith cohesion, or EVA/rover mechanical safety.
