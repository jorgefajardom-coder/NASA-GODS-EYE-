# Public terrain sample - pending

`manifest.template.json` is a fill-in template, **not an imported dataset**. It contains no terrain matrix or NASA imagery. Keep `status: pending` until Daniel has verified the actual product, resolution, datum, orientation, license/terms, URL and SHA-256 for every source. `ready` requires non-null provenance fields under the proposed schema, but schema validation alone is not scientific approval.

Expected future files: public prior/belief/sigma arrays, distinct NoData and observation masks, reduced public previews, and three ENU control points. Do not bundle evaluator HiRISE reference matrices in public artifacts or shared terrain archives.

All coordinates use Mars-local ENU in meters, with an explicit planetary projection and datum. Never silently substitute terrestrial WGS84/EPSG:4326. Resampling does not improve native resolution. MOLA is regional context unless a defensible additional role is demonstrated.

Populate source metadata from the exact imported file; a generic portal URL is not a substitute. All fixture obstacles, sensor observations and toy scenarios must be marked `SIMULATED` and distinguished from NASA measurements.
