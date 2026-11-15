# F-TERRAIN-02 - Synthetic local-surface A* prototype

Base: d162cd869409381bf5b3e10bf31ed8db6cf064f6 on the experimental branch.
The prepared scientific PR branch stays at d737e0fa; all five development commits
are preserved. This is an isolated Python experiment under D-DEL-03, not a change
to the frozen delivery revision or an activation proposal for this delivery.

## Architecture and distinction from legacy
local_surface.py adds frozen LocalSurface, SurfaceLimits and MobilityEvaluation.
evaluate_surface invokes the existing plan_route on a fully covered synthetic
fine TerrainGrid. No search is copied; core._motion_costs is unchanged and applies
max_step=0.2 on every fine edge and connector. A continuous ramp accumulates rise
across many small increments; an abrupt0.35m jump remains an inadmissible edge.
Omitting this standalone experimental entry point preserves all defaults.

Only SYNTHETIC_CELL_SURFACE is supported. Its complete sampled cell-surface/edge
model is a declared synthetic computational world, not a reconstruction of
physical continuity from two points. Neither measured nor orbital datasets can
be activated through this prototype. Real-world continuity between samples,
subsample hazards, suspension/traction and deformation remain unproved. Dense
samples alone never establish physical safety; a physical provider would require
an independently reviewed support/error contract before being accepted here.

Coarse-to-fine grids have identical extents/origins, an odd integer subdivision
and matching coarse-centre heights. This preserves exact centred endpoints.
The wrapper checks run/map/request association, explicit map ENU/datum agreement,
native spacing, dimensions, full raster availability, finite nonnegative sigma,
parent sigma and forbidden/unknown masks. It never lowers uncertainty to gain
admission. Missing support returns UNKNOWN; incompatible metadata ERROR; stale
versions STALE_MAP. No optimistic result is promoted to FEASIBLE.

Full synthetic raster coverage is required, conservatively stronger than just
corridor coverage. The unchanged fine-grid geometry checks swept footprint,
map boundaries, diagonal corners, slopes and local steps on all search/return
edges and continuous connectors. Experimental cross/roughness filters add mask
obstacles; the same filtered grid is returned as evaluation_grid for subsequent
validation. ReplanPolicy KEEP is tested using precisely that grid/context. Passing
the coarse parent to policy instead is unsupported and can correctly reject the
ramp: this prototype does not wire automatic coarse/fine map conversion or events.

SurfaceLimits explicitly declares native support<=0.5m, worst-heading cross
slope<=30 degrees and interpolation residual<=0.1m in the fixtures. These are
synthetic trial parameters, not David profile modifications or stability limits.
Worst-heading cross grade uses atan(norm(gradient)); this is deliberately more
conservative than heading-specific lateral grade and can reject a steep but
longitudinally permissible edge. Roughness is the maximum opposite-neighbour
interpolation residual, not physical wheel roughness. Resulting mask cells remain
subject to footprint inflation. These criteria require review before real inputs.

MobilityEvaluation binds exact surface bytes/provenance, parent map bytes and
experimental profile/limits through hashes. Feasible experimental route IDs also
include those identities. is_current requires the same source/map/limits/profile;
changed versions, sources and parameters invalidate the evaluation. Request and
agent IDs remain the original planner identities. No runtime authorization or
physical command follows; MissionManager remains the sole route authority.

## Reproducible comparisons
Fixtures use a3x5 coarse grid,9x subdivision (27x45 fine raster), human and rover,
FAST and SAFE. Coarse spacing is0.35/tan(5 degrees)=4.0005183m, so the5 degree
ramp and0.35m discontinuity have exactly the same endpoint rise over one coarse
spacing. Fine spacing is about0.444502m, declared original synthetic support,
not a resampled20m orbital product or an assertion of centimetre DEM support.
The ramp is generated analytically as z=x*tan(angle); the step is a full-width
piecewise-constant stripe boundary. The supplied local model covers both sides
and the entire footprint, not a pair of isolated samples.

Matrix cases: flat; ramps5/10/15/25;0.35 step; missing native support; side10/35;
crest/valley; irregular surface with obstacles; alternative corridor; high sigma;
NoData. Published human/rover slope, downhill, footprint and step limits remain
unchanged. A15 degree candidate is only a model result and may be rejected by
its own profile. Cross35 exceeds the explicit30 trial limit; this is not a
rollover threshold. Full scenario/agent/mode results are in evidence/planner-terrain-f02.
Each record includes profile, native/evaluation/coarse spacing, exact evidence
identity, legacy and experimental status/reason, costs, remaining energy and
expanded labels/time. The fixture code supplies analytic slope/rise and terrain
provenance; no NASA/evaluator/reference arrays or UX scenes are used.

Additional tests cover directed science segment/activity totals independently
summed through the shared API, explicit pending inspect1s, return and reserves,
continuous actual XYZ starts, diagonal edges, immutable arrays, incomplete masks,
wrong run/origin/datum, uncertainty downgrade, stale map2, source/parameter
identity changes, resource exhaustion and one-label UNKNOWN/SEARCH_LIMIT.
The earlier oracle tests run unchanged; the tiny oracle is not presented as an
exhaustive oracle for the27x45 mobility grid. No second science model is created.

## Limits, ownership and future activation
David must approve the relationship of raster support to local-step interpretation,
cross/roughness/uncertainty limits and remaining service/resource semantics.
Daniel must supply measured support/provenance/error and frame/datum association
for an actual full footprint. Orbital resampling is not that evidence. Jesus
must review any future transport, coherent fine-grid snapshots, evidence changes
and invalidation/stop/execution consumers. Current TerrainGrid lacks a datum field:
the wrapper compares explicit caller-supplied datum with declared local evidence,
not a verified ROS transport datum contract. No production contract is altered.

Operational integration remains blocked on that physical evidence/owner contract.
Reusing a returned candidate under a different evidence map or unfiltered/coarse
geometry is forbidden. No ROS node, MissionManager, profile, scientific equation,
public map or UI is changed. Flight3D, traction, tipping, EVA safety, scientific
mission success and three-role execution are unvalidated. Organizer notification
and explicit endorsement are separate delivery gates, not supplied by this study.

Future acceptance requires reviewed native support/error bounds and full footprint
coverage; independently verified frame/datum and version binding; consistent
search/connector/replan geometry; directed costs/strict reserves; stale evidence
rejection; exact boundary/NoData regressions; actual consumer checks and explicit
opt-in approvals before any runtime activation. No step gate is removed here.

## Fresh validation

76 new cases passed; full Python1344 passed,22 skipped,0 failed.
One existing Starlette warning. Full suite includes prior legacy,C2,MVP and oracle
regressions. Repository/whitespace checks are required at the local commit gate.
No shared core/node/ROS path changed, so native ROS/web were not repeated; their
earlier recorded outcomes are historical. Exact versions/source hashes and
commands are retained in evidence/planner-terrain-f02/validation.json.

The final two paired tests use the same one-cell horizontal span and assert
exactly0.35m rise for both ramp and step, for each agent: ramp FEASIBLE, step
not FEASIBLE. This establishes a synthetic model distinction only.

Observed FAST comparisons (SAFE matrix is retained in JSON): both agents change
from legacy NO_PATH to experimental FEASIBLE on5 and10 degree synthetic ramps.
On15 degrees human remains NO_PATH and rover becomes FEASIBLE under its model;
25 degrees and the0.35m step remain NO_PATH for both. These are model outcomes,
not physical ratings. The original increment cap still imposes a spacing-dependent
bound on the fine grid too (atan(0.2/0.444502), about24.22 degrees along grid axes).
Thus this experiment reduces, but does not abolish, the discretization coupling;
a25 degree rejection must not be attributed solely to the profile slope limit.
It is not a general physical discontinuity classifier or a waiver for roughness.
