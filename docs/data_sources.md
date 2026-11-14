# Data source register (Daniel)

Daniel's final terrain release remains pending. A newly processed provisional
CTX prior is now included on feat/planner; a separate HiRISE evaluator crop stays
local and isolated. See [actual processing provenance](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/34c515b6b86f73336844e8b3614c70b144574ec3/docs/planner_provenance.md),
the [provisional manifest](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/34c515b6b86f73336844e8b3614c70b144574ec3/data/planner_provisional/manifest.json), and the
[resource-to-result register](nasa_traceability.md). Templates remain templates;
an imported orbital product is not a locally verified corridor. Standalone
MGS/MOLA selection and meaningful use remain pending.

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
