# Third-party notices

Third-party assets distributed with this repository. Their licences apply to
the assets only, not to the project's own code.

## Astronaut 3D model

"Animated Astronaut Character in Space Suit Loop" (https://skfb.ly/o9nHu) by LasquetiSpice is licensed under Creative Commons Attribution (http://creativecommons.org/licenses/by/4.0/).

- File: `web/public/assets/models/astronaut.glb`
- Source: https://sketchfab.com/3d-models/animated-astronaut-character-in-space-suit-loop-8fe5c8d3365e4d87bb7bc253d53a64e1
- Downloaded variant: GLB, 1K textures (21.7 MB).
- Modifications: materials converted from `KHR_materials_pbrSpecularGlossiness`
  to metallic-roughness with glTF Transform (`gltf-transform metalrough`),
  because current Three.js no longer supports the original extension. Geometry,
  skeleton, textures and animation clips (`wave`, `floating`, `idle`,
  `moon_walk`) are unchanged. At runtime the viewer scales the model and uses
  only `idle` and `moon_walk`.

## Terrain data

Mars 2020 Terrain Relative Navigation CTX DTM mosaic, USGS Astrogeology Science Center / NASA.

- Source file: `JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif`
  (9,662,387 bytes, SHA-256 `16a1aa66c3f48c1bca252795827db7b417876217aff0f5e1aff18027fab2327b`).
- Product page: https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_ctx_dtm_mosaic
- DOI of the CTX DTM product family: https://doi.org/10.5066/P906QQT8
- `web/public/replay/demo/context.json`: the same file over a 20 km square centred on the crop, each 100 m cell the mean of 5 × 5 bilinear samples (box average), made by `web/scripts/extract-ctx-context.mjs` after checking the file's SHA-256. Context surroundings only.
- The full file is not stored in this repository. `web/scripts/data/ctx_crop.json` holds a
  3.4 km × 7.6 km crop (425 × 950 cells of 8 m, interpolated from the 20 m source) joining the Perseverance landing area with the terrain north of it, resampled by `web/scripts/extract-ctx-crop.mjs`
  onto a local tangent ENU grid. The resampling adds no resolution.
- The crop is provisional: it was made by the frontend until the data owner delivers the
  processed package.
- Licence terms were not verified here; see the product page. Credit: NASA/USGS.

## Fonts

Bundled locally through `@fontsource` (no CDN). All are licensed under the SIL Open Font
License 1.1 (https://openfontlicense.org); the licence texts ship in `web/public/licenses/`.

- Rajdhani. Copyright (c) 2014 Indian Type Foundry.
- Barlow Condensed. Copyright 2017 The Barlow Project Authors.
- IBM Plex Mono. Copyright 2017 IBM Corp.

## Terrain image

MRO CTX Jezero orthomosaic, controlled (Mars 2020 Terrain Relative Navigation), NASA/JPL-Caltech/MSSS/USGS, served by JPL Mars Trek.

- WMTS layer: `JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0` (https://trek.nasa.gov/mars/), native 6 m, same `soc_008` production as the CTX DTM above.
- `web/public/replay/demo/ctx_ortho.png`: 680 × 1520 px over the crop (5 m/px), made by `web/scripts/extract-ctx-ortho.mjs` from the level-13 tiles that cover it (28) (tiles SHA-256 `7ab42c4a7898af7ee2d40656eb8f280cd367941ee14b0b2415834f91f8278322`). Bilinear resampling onto the crop's ENU grid and a 1st–99th percentile contrast stretch; no detail is added. The viewer tints the panchromatic image for display.
- `web/public/replay/demo/context_ortho.png`: 500 × 500 px over a 20 km square centred on the crop (40 m/px), made by the same script from nine level-10 tiles (tiles SHA-256 `8c6b109a500eb3f7e1c1714ef95d6052f375611718c3e857d691787c09493da1`), same resampling and contrast stretch. Context surroundings only.
- Usage terms not verified here: NASA planetary data, see the Mars Trek and USGS product pages.

## Link preview image

"Global Color Views of Mars" (PIA00407), Viking Orbiter global color mosaic, NASA/JPL/USGS, NASA Photojournal (https://science.nasa.gov/photojournal/global-color-views-of-mars/).

- `web/public/assets/brand/og-image.png`: the 6787 × 6787 px JPEG (SHA-256 `fc62a86416794444988338e55591d23290e1de2c7c32f3613b872caa8413ea2f`) scaled to 560 px and centred on black in a 1200 × 630 card with Pillow; no text, no detail added. Colors are as published (NASA notes they are adjusted for visibility, not natural color).
- Usage terms: NASA imagery is generally not copyrighted; see NASA's media usage guidelines (https://www.nasa.gov/nasa-brand-center/images-and-media/). No NASA logo or mark is used.

## Star catalogue and Mars sky model

Yale Bright Star Catalogue, 5th revised edition (Hoffleit & Warren 1991), ASCII BSC5 as distributed by the SAO/Harvard Telescope Data Center (http://tdc-www.harvard.edu/catalogs/bsc5.html; same layout as CDS catalogue V/50).

- `web/public/assets/sky/bright_stars.json`: the 2887 stars with V ≤ 5.5 (J2000 right ascension and declination, V magnitude, B−V), copied by `web/scripts/extract_bright_stars.py` from `bsc5.dat.gz` (SHA-256 `0471ced07fc241e625613baa689b2fa5f4b59fd733f731003e57d2d436036cdb`). No values are computed or changed.
- Mars orientation: IAU/WGCCRE 2009 rotation model (Archinal et al. 2011, Celest. Mech. Dyn. Astr. 109, 101). Sun position: Mars24 algorithm (NASA GISS; Allison & McEwen 2000, Planet. Space Sci. 48, 215).
- Usage terms not verified here: the BSC5 is a long-standing freely distributed astronomical catalogue; cite Hoffleit & Warren (1991).

## Geologic units

Sun, V., and Stack, K., 2020, Geologic map of Jezero crater and the Nili Planum region, Mars: U.S. Geological Survey Scientific Investigations Map 3464, scale 1:75,000, https://doi.org/10.3133/sim3464 (data release https://doi.org/10.5066/P9CZYIO7). USGS publication, public domain.

- `web/public/replay/demo/geology.json`: unit attributes (name, symbol, description, additional characteristics, interpretation) and polygons of the units that intersect the demo crop, read from the USGS ArcGIS feature service `Jezero_FeatureServiceFromPro/FeatureServer/8` by `web/scripts/extract-geology.mjs`, reprojected from Mars Transverse Mercator (77.5°E) to the crop's ENU frame and clipped to it. Text is unchanged; display colours are the viewer's own.
- The map was drawn on a semi-controlled CTX mosaic and has offsets of about 100–200 m against the controlled Mars 2020 CTX terrain. It is not re-registered, and the viewer labels boundaries as approximate.

## Rover and drone 3D models

Official 3D models by NASA/JPL-Caltech: "Mars Perseverance Rover, 3D Model" (https://science.nasa.gov/resource/mars-perseverance-rover-3d-model/) and "Mars Ingenuity Helicopter, 3D Model" (https://science.nasa.gov/resource/mars-ingenuity-helicopter-3d-model/).

- Files: `web/public/assets/models/rover.glb`, `web/public/assets/models/drone.glb`.
- Modifications: all agency branding on the textures (logos, flag, mission plaques, perforated agency names, commemorative and brand text) was painted out with the surrounding plain surface, as the competition rules forbid NASA branding in the delivery; the rover was decimated to about 35 % and textures limited to 512 px; the rover was turned to face +X. Marks the Blender pass missed (the rover's stowed-helicopter blade sheet and the drone's blade roughness map) were then removed by `web/scripts/strip-glb-branding.mjs`. Details and checksums in `web/scripts/blender/README.md`.
- Use of NASA imagery and models follows NASA's media usage guidelines; no NASA endorsement is implied.

## Mars weather and radiation context

- File: `web/public/replay/demo/atmosphere.json` (built by `web/scripts/extract-atmosphere.mjs`).
- Mars 2020 Perseverance MEDA and MSL Curiosity REMS daily weather summaries from the NASA Mars weather feed (https://mars.nasa.gov/rss/api/?feed=weather&feedtype=json&category=mars2020 and `category=msl`), credit NASA/JPL-Caltech/CAB(CSIC-INTA). CAB provides these summaries for outreach purposes; the science data is archived at PDS. Values are copied (Jezero) or grouped into medians per 15° of solar longitude (Gale).
- MSL RAD surface dose rates from Hassler, D. M., et al. (2014), Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover, Science 343, 1244797, https://doi.org/10.1126/science.1244797 (published values only).

## Gale crater terrain (Curiosity world)

MSL Gale crater DEM mosaic, 1 m, v3 (MRO HiRISE and CTX stereo), USGS Astrogeology Science Center / NASA.

- Source: https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif (3.7 GB; its MD5 as published, `bc4cbabf8b06d24f3b25400f0468933b`, is also recorded in `web/scripts/data/gale/ctx_crop.json`). Only the 8 m overview in the `.ovr` file is read, by range requests (about 1.7 MB); the full file is not stored.
- `web/scripts/data/gale/ctx_crop.json`: the 3.4 km × 7.6 km crop (425 × 950 cells of 8 m, cubic resampling of the overview) made by `web/scripts/extract-gale-crop.mjs`. The 8 m cells add no detail. Licence terms were not verified here; see the USGS product page.
- `web/public/replay/gale-demo/ctx_ortho.png`: 340 × 760 px (10 m/px) from the JPL Mars Trek layer `Gale_CTX_BlockAdj_dd` (MRO CTX Gale crater mosaic, NASA/JPL-Caltech/MSSS), level-12 tiles SHA-256 `d219b220a363b4b68f9f855376b8fd91d1c4954f97ea13b5b67a945f474ebe89`, made by `web/scripts/extract-ctx-ortho.mjs` with a 1st to 99th percentile contrast stretch.
- Curiosity stops: `web/scripts/data/gale/rover_waypoints.json` and `web/public/replay/gale-demo/rover_stops.json`, from NASA's MMGIS MSL waypoints (https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json), thinned to at least 80 m apart, positions and identifiers only. Curiosity raw images are read from NASA's public feed only when the person asks.

## Perseverance rover stops

Mars 2020 Perseverance waypoints (MMGIS M20 layer), NASA/JPL-Caltech, https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json.

- `web/scripts/data/rover_waypoints.json` and `web/public/replay/demo/rover_stops.json`: the 226 stops (sol 13 to 708) that fall inside the demo crop, with sol, site, drive, latitude and longitude, converted to the crop's local frame by `web/scripts/extract-rover-waypoints.mjs`. The file records the SHA-256 of the feed it was read from. Positions and identifiers only; no image is stored.
- The viewer asks NASA's public raw-images feed for the images of a stop only when the person presses the load button; images are shown from NASA's servers, credit NASA/JPL-Caltech, and are never stored or bundled.
- Usage terms not verified here: NASA mission data, see https://mars.nasa.gov/mars2020/multimedia/raw-images/.

## Zone scenes: Gusev, Elysium/InSight, Meridiani/Endeavour, Valles Marineris

Terrain, imagery and rover stops of the four scenes built after Jezero and Gale. DEM files were downloaded whole from JPL Mars Trek (`https://trek.nasa.gov/mars/TrekWS/rest/cat/data/stream?uuid=<item>`) and cropped by `web/scripts/extract-dem-crop.mjs` to 3.4 km × 7.6 km at 8 m (finer sources box averaged to 8 m, coarser ones resampled without resolution gain); only the crops are stored, in `web/scripts/data/<zone>/dem_crop.json`, and they become each scene's `rasters.json`. Imagery: `web/scripts/extract-ctx-ortho.mjs` (level-12 tiles, 10 m/px, 1st to 99th percentile stretch) into `web/public/replay/<zone>-demo/ctx_ortho.png`, which is also the zone's selector card.

- Gusev (`gusev-demo`): DEM `CLH_DEM_Mosaic_HiRISE_CTX_HRSC_GCS_MARS_07-10-2018.tif` (MRO HiRISE, DEM Columbia Hills, preliminary; Trek item 3c084606-ea38-4b30-86ff-18b9935c8cca), 2,365,020,753 bytes, SHA-256 `8a42cb6f6fe912f46b955317f7e410f68c8bfa70bc1d758f88f0874c33cf8660`, crop centred at 14.5819° S, 175.502° E. Imagery `CLH_Visible_Mosaic_HiRISE_CTX_HRSC_GCS_MARS_07-10-2018`, tiles SHA-256 `b8bb548d8872758369a57723831e11f03138e1c1536ca50e592a8d70bcf40511`, image SHA-256 `0ae0724b41641deadb72d2ead898c317eb8b3b66b6213dc52ccfcbe5de100d2e`. Credit NASA/JPL-Caltech/USGS/University of Arizona and ESA/DLR/FU Berlin (HRSC).
- Elysium Planitia (`insight-demo`): DEM `InSight_HiRISE_CTX_HRSC_dem_mosaic_50pix_sigma5_exp3.tif` (Trek item 34ec247b-59e4-4515-b04b-b6d433ae9342), 59,846,912 bytes, SHA-256 `7d2fde9eab6ffb0111a79e7403a9af4d9314a1dc54485b95c1e67175116f630e`, 20 m, crop centred on the lander at 4.502° N, 135.623° E. Imagery `InSightCTXMosaic_112917`, tiles SHA-256 `f4951573e533db52e86f27843375d7d890d012b012b4e281a97461162e89beab`, image SHA-256 `2c67b8011eacb480e3d92490add80c1a31fe2942255aa49097083de47dedabbf`. Credit NASA/JPL-Caltech/MSSS/USGS.
- Meridiani Planum (`meridiani-demo`): DEM `DEM_1m_Endeavour_Crater_isis3_2017-04-14.tif` (Trek item 01e2fd47-4e4d-493f-9c2f-7e36e905b871), 703,735,672 bytes, SHA-256 `9732dfc953fcf5d70743f7435ba96b6222c9e43d7639430d044047c5fda85649`, 1 m, crop centred at 2.2679° S, 5.369° W on Endeavour's west rim (8,977 of 403,750 cells NoData at the DEM edge). Imagery `S_Meridiani_Sinus_Planium_CTX_BlockAdj_dd`, tiles SHA-256 `6f6bfa7739a1b5860884659acba2101fb8c9baac14c74437950435c50cc9d250`, image SHA-256 `501a4db2f62babc03ff83f5f420ef6f3845a78614e341bc58af6fd222cef3a62`. Credit NASA/JPL-Caltech/University of Arizona, NASA/JPL-Caltech/MSSS.
- Valles Marineris (`melas-demo`): DEM `CTX_DEM_11S291E_24mp_B19_017187_1685_B19_016976_1685.tif` (Trek item 24505ca1-b555-4500-9f06-34a3a7e714ba), 29,161,694 bytes, SHA-256 `f2f95a1133e3e231675f055c4d2273a36a34d785c1f2f3e8e889e2a2bb087d6a`, 24 m, crop centred at 12.8716° S, 69.0574° W (chosen as a complete window with about 1.5 km of relief). Imagery `CTX_Ortho_11S291E_6mp_B19_017187_1685`, tiles SHA-256 `f0425a6fb307c72969692b3dfd6d06151644614f5da145a2f120bfa97713e365`, image SHA-256 `3cdc60a3eabc35da2221e99e5db7b6ef0e88ea24ab95a59e4f9118ce2d398cd2`. Credit NASA/JPL-Caltech/MSSS/USGS.
- Spirit and Opportunity stops: PDS Geosciences Node (Washington University in St. Louis) interpolated traverse tables, https://an.rsl.wustl.edu/mera/AN/pages/mer/mer_traverse.htm. `MERA_traverse.csv` (Spirit, sols 1 to 2209), SHA-256 `fe55559872d2f556409c12793b4025437881bb24170b3a8ecfa8ed0b078390f5`: 108 stops inside the crop (sol 1 to 1866, thinned to 40 m apart). `MERB_traverse_5130.csv` (Opportunity), SHA-256 `bd0a50b39c62f021ce609170f72c00229ef9dd15459bf48fa5bb5f5c45ba553b`: 134 stops (sol 2630 to 4922, thinned to 80 m). Converted by `web/scripts/extract-mer-traverse.mjs`; Opportunity's table is in metres from its landing site, which the frontend ties to the published landing coordinates (1.9462° S, 354.4734° E), so its positions may be off by tens of metres. The PDS label marks these tables as not archived in PDS. Positions and identifiers only.
- Usage terms not verified here: NASA mission data served by JPL Mars Trek and the PDS Geosciences Node.
