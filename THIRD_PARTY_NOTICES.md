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
