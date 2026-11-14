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
