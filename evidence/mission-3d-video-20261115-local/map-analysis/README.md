# Active window versus regional context for the recorded EVA

Read-only analysis of sealed run `local-cost-eva-bunsen-20261115-02`.
No A/B, pose, cost, original raster, observation or raw record was changed.

| Quantity | Measured result |
|---|---:|
| A ENU x/y, m | -226 / -218 |
| B ENU x/y, m | -238 / -82 |
| A–B horizontal separation | 136.5284 m |
| Bounds of all reached positions and returned planner paths | 12 × 136 m |
| Programmed observation | centre (-230,-182), radius 12 m, 29 grid centres |
| Bounds including the entire circular observation footprint | 24 × 136 m |
| Enclosing-box area as fraction of 512² | 1.2451% |
| Smallest containing 4 m-aligned rectangle | 28 × 140 m, origin (-244,-220) |

The enclosing-box fraction is **not** the observed-ground fraction, a coverage
metric, or the search frontier's area. It only describes the returned geometry
and the specified observation circle. The 29 cells are computational samples,
not independent CTX observations at 4 m precision; native DTM spacing stays20 m.

A128 m-side square cannot contain this A/B pair: its northing span alone is
136 m. A160 m-side square can contain the geometric union, but no search result
is claimed for that tight square. A256 m-side square is a conservative local
working window with explicit metadata;512 m is not demonstrated necessary for
this particular mission's planning or scientific work.

At4 m/cell, **128×128 cells means512×512 m**. A128×128 m patch means32×32 cells.
Always specify physical side and grid dimensions separately.

## Actual planner consumer check

The aligned southwest256 m crop is rows0:64/columns0:64 of the public128×128
source. Its origin remains(-256,-256) m. Absolute ENU A/B/return coordinates,
heights, resources, reserves, sigma, NoData, obstacles and activity schedule are
preserved. All29 observation indices were explicitly remapped from128-wide to
64-wide rows while retaining the same world cell centres. No recentring or
silent snapping occurred.

The actual pinned published planner and exact scientific-cost composition were
run on both windows for the initial request and the post-observation replan.
All four queries returned FEASIBLE under2 s/200,000 labels; no extended fallback
was needed. **Outbound geometry, directed return geometry and time/Wh/O2 totals
were exactly identical in each pair.** The initial pair expanded3033 labels,
the replan pair1804 labels in each window. Serial measured latencies were
0.297/0.281 s for512/256 initial and0.188/0.172 s for the replan; these small
differences are diagnostic rather than a hardware performance claim.

The256 crop contains4096 rather than16384 raster cells, a75% reduction. This
establishes sufficiency for these two fixed model requests only, not universal
equivalence across agents, goals, perturbations or objectives. Cropping changes
map boundaries and can remove alternatives; future queries require their own
checks. The unchanged source's west edge is only14 m beyond the enclosing
footprint bound, so an extra symmetric margin greater than12 m is not available
on that side even in the original512 m patch.

## Interpretation for the presentation

Use256 m as the local active window for this demonstrated case and512 m only
as optional regional context or scale-study input. Camera focus can follow
the route without changing physical coordinates. If the research question is
the benefit of a larger planning domain, compare domains under the same mission
or define a new adequately budgeted mission that actually needs distant targets
or alternatives. This run does not establish such a benefit or scientific site
representativeness. No probability of discovery is inferred.

`footprint.json` contains geometry and candidate crops; `crop-comparison.json`
contains full actual requests/results, resource snapshots, observation remapping,
code hashes and the narrow equivalence conclusion. The initial measurement
script attempt mixed2D footprint points with3D poses, failed before writing
results, and was corrected to project all measured bounds to x/y; the original
experiment remained untouched.
