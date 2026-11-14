# Data source register (Daniel)

No NASA datasets are included yet. Templates are not verified manifests.
Product selection, license, precise CRS/datum, crop and checksums are pending.

| Candidate from team guides | Role | Next action / limitation |
| --- | --- | --- |
| MRO / CTX: https://doi.org/10.5066/P906QQT8 | Prior | Record imported product, scale, license and SHA-256 |
| MRO / HiRISE: https://doi.org/10.5066/P9REJ9JN | Isolated evaluator reference | Orbital topography is not mobility ground truth |
| MGS / MOLA | Regional context/selection | Select exact product; no invented local rock detail |

For each file record mission, instrument, product/version, role, URL/DOI,
license/terms, native/output scale, resampling, datum, NoData, crop and SHA-256.
Follow the NASA resource hierarchy in AGENTS.md. `data/reference` is excluded
from distribution; enforce that boundary at runtime too. Supply three numeric
ENU/lat/lon control points to Jorge/Diego. Do not assume terrestrial WGS84 for
Mars. Resampling cannot create native resolution.

## NASA reference resources reviewed for Jezero (14 November 2026)

The five mandatory resources in AGENTS.md section 10 were opened and checked for
what serves the Jezero mission viewer. Nothing below is imported yet unless stated;
each candidate still needs its exact file, licence, CRS and SHA-256 recorded as above.
The viewer lists them under Credits (`web/src/data/referenceSources.ts`).

| Resource | What is useful for this project | Status |
| --- | --- | --- |
| [JPL Mars Trek](https://trek.nasa.gov/mars/) | WMTS layers over Jezero ([layer catalogue](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars)): **MRO CTX Jezero Mosaic, Controlled** `JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0`, 6 m, bbox 77.1605–77.6992°E, 18.2110–18.7212°N, PNG tiles, equirectangular (EPSG::104905). It comes from the same Mars 2020 TRN production as the CTX DTM crop the viewer uses (`soc_008`), so it can texture the terrain without re-registration. Also **MRO HiRISE Jezero Mosaic, Controlled** `JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd` (25 cm, 77.2229–77.5840°E, 18.3068–18.6693°N), the **Jezero NE Syrtis Midway** visible mosaic (HiRISE/CTX/HRSC) and a preliminary block-adjusted CTX mosaic. Tile template: `https://trek.nasa.gov/tiles/Mars/EQ/<layer>/1.0.0/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png`. | Candidate. HiRISE imagery reveals terrain at the evaluator's resolution, so like the HiRISE DTM it is evaluator-only. |
| [USGS-NASA Planetary Geologic Mapping Program](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars) | **SIM 3464**, Sun and Stack (2020), *Geologic map of Jezero crater and the Nili Planum region, Mars*, 1:75,000, [doi:10.3133/sim3464](https://doi.org/10.3133/sim3464), public domain. GIS: geodatabase with `GeoUnits_v1`, `GeoContacts`, `LinearFeatures`, `SurfaceFeatures`, `LocationFeatures`, `LandingEllipse`; Mars Transverse Mercator, central meridian 77.5°E, Mars 2000 sphere (R = 3396190 m). Built on a semi-controlled CTX mosaic: offsets of about 100–200 m against the controlled Mars 2020 CTX mosaic, so it must be re-registered before overlaying our crop. **SIM 3292**, Tanaka et al. (2014), global geologic map 1:20,000,000, [doi:10.3133/sim3292](https://doi.org/10.3133/sim3292), regional context only. | Candidate geology layer (SIM 3464). |
| [Curiosity's Proposed Path up Mount Sharp](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/) | Design reference for the route view: a planned traverse drawn over an orbital base map built from MRO HiRISE, CRISM and CTX (and Mars Express HRSC), with labelled science regions along it. Credit: NASA/JPL-Caltech/ESA/University of Arizona/JHUAPL/MSSS/USGS Astrogeology. | Design reference only; no data reused. |
| [NASA Worldview](https://worldview.earthdata.nasa.gov/) | Earth satellite imagery (MODIS, VIIRS, OCI, Landsat/Sentinel-2) with Earth place labels. It has no Mars layers. | Not applicable to Mars terrain. |
| [Mars Perseverance Raw Images](https://mars.nasa.gov/mars2020/multimedia/raw-images/) | Over one million raw images from Jezero. Public JSON feed used by the gallery: `https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&ver=1.2&num=<n>&page=<p>&order=sol+desc`, with per-image `sol`, `site`, `drive`, `camera.instrument` (Navcam, Hazcam, Mastcam-Z, …), CAHVORE camera model, mast azimuth/elevation and links to full-resolution files. Credit NASA/JPL-Caltech. Could show the real surface near a waypoint. | Candidate illustration. Raw images are not mobility ground truth and must not reach the agent's map. |
