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

- **Orbital prior vs. local observation:** Finite pixels in the MRO/CTX prior (`~nodata_mask`) are **estimated**, not locally verified ground observations. On initial load, `observed_mask` is all `False` and sigma remains 2.5 m. The legacy observed-only policy returns `-1`; the explicit illustrative D-EST-01 policy may admit a hypothetical proposal within its configured uncertainty/slope limits. A `0` mask never means locally verified or authorized passage. NoData and confirmed obstacles remain distinct; planner profiles apply independent constraints. See [reconciliation](audit_reconciliation.md).
- **No synthetic resolution claim:** Resampling 20 m MRO/CTX or 463 m MGS/MOLA onto a 4 m computational grid does not create sub-20 m native topographic detail.
- **Evaluator reference isolation:** MRO/HiRISE 1 m reference arrays remain isolated in `data/reference/` (gitignored) and are blocked by `mge_data.core.load_public_terrain`.
- **No physical safety certification:** Even 1 m orbital DTMs do not resolve decimeter-scale hazards, regolith cohesion, or EVA/rover mechanical safety.

The web's illustrative `demo` retains its separate crop: 3.4 km × 7.6 km of the
same CTX DTM on an 8 m display grid joining the Perseverance landing area with the
terrain north of it (`web/scripts/data/ctx_crop.json`; source file/hash in
`THIRD_PARTY_NOTICES.md`). A second illustrative world, `gale-demo`, uses a crop of
the same size from the MSL Gale crater DEM mosaic (8 m overview only) with the MRO
CTX Gale mosaic from Mars Trek. Both worlds mark real rover stops from NASA's MMGIS
waypoint layers (Perseverance M20: 226 stops, sol 13–708; Curiosity MSL: 166 stops,
sol 751–4462, thinned to ≥ 80 m), positions and identifiers only; the mission story
on top of them is simulated. Exact URLs and hashes are in `THIRD_PARTY_NOTICES.md`.
Recorded runs consume this package's own public raster attachment with geometry,
datum and versions validated. They must not borrow demo imagery/geology or
report its metrics as the 128 m experiment.

## Rock size model for drawn obstacles (15 November 2026)

The viewer's obstacle rocks (web/README.md, *Obstacle rocks*) follow the rock size-frequency law of Golombek, M. P., and Rapp, D. (1997), *Size-frequency distributions of rocks on Mars and Earth analog sites: Implications for future landed missions*, JGR Planets 102(E2), 4117-4129: cumulative fractional area F(D) = k exp(-q D), q = 1.79 + 0.152/k. The value k = 0.05 is illustrative, not a measurement of the crop. Because rocks of that law are mostly decimetre-sized and unreadable at the crop's scale, the main rock of each blocked cell is drawn from 1.5 m, the boulder size from which HiRISE rock counts for landing-site hazard maps (Golombek and colleagues) detect rocks; this enlargement is a display choice for usability. Nothing here reaches the planner, the mission or a recorded package.

## NASA reference resources reviewed for Jezero (14 November 2026)

The five mandatory resources in AGENTS.md section 10 were opened and checked for
what serves the Jezero mission viewer. Nothing below is imported yet unless stated;
each candidate still needs its exact file, licence, CRS and SHA-256 recorded as above.
The viewer lists them under Credits (`web/src/data/referenceSources.ts`).

| Resource | What is useful for this project | Status |
| --- | --- | --- |
| [JPL Mars Trek](https://trek.nasa.gov/mars/) | WMTS layers over Jezero ([layer catalogue](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars)): **MRO CTX Jezero Mosaic, Controlled** `JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0`, 6 m, bbox 77.1605–77.6992°E, 18.2110–18.7212°N, PNG tiles, equirectangular (EPSG::104905). It comes from the same Mars 2020 TRN production as the CTX DTM crop the viewer uses (`soc_008`), so it can texture the terrain without re-registration. Also **MRO HiRISE Jezero Mosaic, Controlled** `JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd` (25 cm, 77.2229–77.5840°E, 18.3068–18.6693°N), the **Jezero NE Syrtis Midway** visible mosaic (HiRISE/CTX/HRSC) and a preliminary block-adjusted CTX mosaic. Tile template: `https://trek.nasa.gov/tiles/Mars/EQ/<layer>/1.0.0/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png`. | **Used** (CTX orthomosaic): draped on the web demo terrain as `web/public/replay/demo/ctx_ortho.png`, see THIRD_PARTY_NOTICES.md. HiRISE imagery reveals terrain at the evaluator's resolution, so like the HiRISE DTM it is evaluator-only. |
| [USGS-NASA Planetary Geologic Mapping Program](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars) | **SIM 3464**, Sun and Stack (2020), *Geologic map of Jezero crater and the Nili Planum region, Mars*, 1:75,000, [doi:10.3133/sim3464](https://doi.org/10.3133/sim3464), public domain. GIS: geodatabase with `GeoUnits_v1`, `GeoContacts`, `LinearFeatures`, `SurfaceFeatures`, `LocationFeatures`, `LandingEllipse`; Mars Transverse Mercator, central meridian 77.5°E, Mars 2000 sphere (R = 3396190 m). Built on a semi-controlled CTX mosaic: offsets of about 100–200 m against the controlled Mars 2020 CTX mosaic, so it must be re-registered before overlaying our crop. **SIM 3292**, Tanaka et al. (2014), global geologic map 1:20,000,000, [doi:10.3133/sim3292](https://doi.org/10.3133/sim3292), regional context only. | **Used** (SIM 3464): four units of the demo crop in the web viewer's Ground layers tab (`web/public/replay/demo/geology.json`, see THIRD_PARTY_NOTICES.md); boundaries not re-registered. The `jezero_mvp` crop's units (`data/sample/geology.json`, all of it on `Nle`) are also published as `web/public/geology/jezero_mvp.json` for recorded runs on that dataset, where they set the drawing style of obstacle rocks (display only). |
| [Curiosity's Proposed Path up Mount Sharp](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/) | Design reference for the route view: a planned traverse drawn over an orbital base map built from MRO HiRISE, CRISM and CTX (and Mars Express HRSC), with labelled science regions along it. Credit: NASA/JPL-Caltech/ESA/University of Arizona/JHUAPL/MSSS/USGS Astrogeology. | Design reference only; no data from this page is reused. The web's separate Gale world (`gale-demo`) draws Curiosity's real stops from NASA's MMGIS MSL waypoints instead (see THIRD_PARTY_NOTICES.md). |
| [NASA Worldview](https://worldview.earthdata.nasa.gov/) | Earth satellite imagery (MODIS, VIIRS, OCI, Landsat/Sentinel-2) with Earth place labels. It has no Mars layers. | Not applicable to Mars terrain. |
| [Mars Perseverance Raw Images](https://mars.nasa.gov/mars2020/multimedia/raw-images/) | Over one million raw images from Jezero. Public JSON feed used by the gallery: `https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&ver=1.2&num=<n>&page=<p>&order=sol+desc`, with per-image `sol`, `site`, `drive`, `camera.instrument` (Navcam, Hazcam, Mastcam-Z, …), CAHVORE camera model, mast azimuth/elevation and links to full-resolution files. Credit NASA/JPL-Caltech. Could show the real surface near a waypoint. | **Used on request** (web viewer, `web/src/lib/perseveranceRaw.ts`, `rawImagesStore.ts`): the newest images in the Atmos tab, the images of a real rover stop when the astronaut stands on it, and the stop images shown by the *Photo tour* button. They are read from the feed only after the person's action, never stored or bundled; photo directions derived from `camera_vector` are approximate. The Gale world reads Curiosity's feed the same way, matched by sol only. Raw images are not mobility ground truth and must not reach the agent's map. |
