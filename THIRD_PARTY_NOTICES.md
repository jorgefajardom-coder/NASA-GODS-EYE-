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
- The full file is not stored in this repository. `web/scripts/data/ctx_crop.json` holds a
  2 km × 2 km crop (100 × 100 cells of 20 m) resampled by `web/scripts/extract-ctx-crop.mjs`
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
- `web/public/replay/demo/ctx_ortho.png`: 400 × 400 px over the 2 km crop (5 m/px), made by `web/scripts/extract-ctx-ortho.mjs` from nine level-13 tiles (tiles SHA-256 `f2ad4cdaf747f36b508cb063ee904d60204c5f3c5dcb77284ab201812369e527`). Bilinear resampling onto the crop's ENU grid and a 1st–99th percentile contrast stretch; no detail is added. The viewer tints the panchromatic image for display.
- Usage terms not verified here: NASA planetary data, see the Mars Trek and USGS product pages.

