# Public terrain sample (`jezero_mvp`)

Owner: Daniel (`feat/data`).

This directory contains the validated public multi-mission terrain package for Jezero Crater (`18.45° N, 77.45° E`, `32 × 32` grid at `4.0 m` cell spacing, `128 m × 128 m` local ENU extent in `frame_id = "map"`):

- `manifest.json`: operational manifest (`status: "ready"`) conforming to `../manifest.schema.json`.
- `manifest.template.json`: original pending schema template (`status: "pending"`) retained for contract negative-testing.
- `terrain.npz`: public raster layers (`prior`, `belief`, `sigma`, `nodata_mask`, `observed_mask`, plus `elevation_m` and `valid_mask` aliases for planner interchange).
- `mola_regional_context.npz`: separate **Mars Global Surveyor / MOLA** (`463 m/px` native) regional topography layer covering the Jezero basin context.
- `provenance_details.json`: complete upstream HTTP 206 window bounds, ETags, native elevation statistics, regional MOLA cross-check metrics, and 4 non-collinear ENU control points.
- `preview_ctx_prior.png`: deterministic 8-bit north-up grayscale preview rendered directly from the MRO/CTX prior elevation grid.

## Reference isolation

Evaluator reference arrays (**MRO / HiRISE** 1 m DTM, DOI `10.5066/P9REJ9JN`) are stored exclusively under `../reference/` (ignored by Git) and are never included in `terrain.npz` or loaded by `mge_data.core.load_public_terrain`.
