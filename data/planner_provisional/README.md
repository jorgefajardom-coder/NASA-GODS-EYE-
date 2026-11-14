# Provisional public CTX prior

`terrain.npz` and `manifest.json` are newly processed from the cited official
MRO/CTX source by `scripts/prepare_planner_terrain.py`. The grid is south-first
ENU with 4 m computational cells; native CTX information remains 20 m.

`valid_mask` means a finite raster elevation exists. It does **not** mean that
the cell has been locally observed or verified as traversable. A mission must
provide its own belief, knowledge, uncertainty and profile-specific constraints.

This bundle contains no HiRISE reference, saved route, prior test outcome or
resource profile. Replace it with Daniel's approved public crop when available.
See `docs/planner_provenance.md` for full provenance and limitations.
