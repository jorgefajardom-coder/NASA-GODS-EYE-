# Provisional planner terrain provenance

The planner's temporary terrain is a newly processed derivative of official
USGS/MRO source products. It is not copied from the preparation repository.
The predecessor `dryanguasr/NASA-Sandbox` at commit `827da15` (10 November 2026)
was consulted only to identify upstream product URLs and their citations. Its
Apache-2.0 source code, cached arrays, scenario outcomes, metrics and media are
not imported by this workflow. Existing upstream observations remain pre-existing
scientific data and are cited as such; processing them now does not make the
measurements new or establish competition eligibility by itself.

## New import

```sh
python -m pip install -r requirements-terrain.txt
python scripts/prepare_planner_terrain.py
```

The default is a 128 m square centred at 18.45 degrees planetocentric north,
77.45 degrees east, with a 4 m computational grid (32 by 32). The projection is
a local equirectangular Mars sphere, radius 3,396,190 m. Southwest origin is
(-64, -64) m; rows increase north, columns east; cell centres are at half-cell
offsets. Heights retain the product's MOLA topography / DeltaGeoid reference.
No terrestrial datum is substituted and no synthetic elevation fills source
NoData. The warp is bilinear and NoData-aware. A separate mask records finite
output samples; that mask is **not** evidence of local ground verification.

The HTTP reader requires bounded 206 range responses and provides no full-file
or cached-Sandbox fallback. This avoids a native GDAL curl failure observed in
the Windows environment while retaining bounded source-window acquisition.

## Distribution boundary

- `data/planner_provisional/terrain.npz` contains only CTX prior elevation and
  validity, with grid metadata. Its manifest records actual processing/acquisition
  times, native source window/value hash, file SHA-256, CRS, units and versions.
  Three cell-centre control points include row/column, ENU, elevation and
  planetocentric/east-positive coordinates for the renderer and consumers.
- `data/reference/planner_provisional/` contains the newly processed HiRISE
  evaluator crop and its own manifest. It is ignored by Git and is not a planner,
  mission or normal web-view input.
- A CTX pixel's native post spacing is 20 m. Rendering or computing on a 4 m
  grid creates no 4 m native information. HiRISE's product post spacing is 1 m;
  it still does not certify mobility, soil mechanics or EVA safety.
- CTX and HiRISE are both instruments on **MRO**. No MGS/MOLA multi-mission
  contribution is asserted by this import; that requirement awaits Daniel's data.

The public data are labelled `provisional` and
`orbital_prior_not_locally_verified`. Resource profiles and synthetic obstacles
used in planner tests remain separate, explicitly illustrative inputs. Replacing
the crop with Daniel's product must preserve coordinate, NoData, provenance and
held-out-reference boundaries; it must not require modifying the search engine.

## Sources

- [CTX product / DOI](https://doi.org/10.5066/P906QQT8): Fergason et al. (2020),
  Mars 2020 Terrain Relative Navigation CTX DTM Mosaic, USGS.
- [HiRISE product / DOI](https://doi.org/10.5066/P9REJ9JN): Fergason et al. (2020),
  Mars 2020 Terrain Relative Navigation HiRISE DTM Mosaic, USGS.
- [USGS copyrights and credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits).
- [Official Space Apps clarification on prior work and resource disclosure](https://github.com/nasa/spaceapps/discussions/1827).

No claim is made that regenerating pre-event artifacts retroactively changes
their origin or eligibility. Keep antecedents distinct from the newly implemented
competition code and newly measured test results.

## Actual import record

New public CTX crop: acquired 14 November 2026 at 15:22:49 UTC, processed at
15:22:52 UTC; 32 by 32 cells, all output elevations finite. New private HiRISE
crop: acquired and processed during the same competition session, with its own
timestamps/hash in the ignored reference manifest. No old crop was used as a
fallback. Consult the manifests for full hashes, source windows and versions.
Public and private file hashes are deliberately not treated as mission evidence.
