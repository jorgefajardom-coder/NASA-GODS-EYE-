# F-TERRAIN-01 - Experimental raster mobility diagnostics

Local experiment derived from planner scientific PR source d737e0fa. The prepared
branch and frozen delivery revision are unchanged. No runtime imports or admission
rules call terrain_diagnostics.py. All new terrain is deterministic synthetic input.

## Demonstrated issue and present interpretation
core._motion_costs rejects abs(dz)>max_step_m independently of directed slope.
With max_step=0.2 m and horizontal spacing4 m, atan(0.2/4)=2.862405 degrees.
Five/ten/fifteen degree analytic ramps have per-edge rises0.349955/0.705308/1.071797 m.
These can fail the current absolute-height bound even below a slope limit.
This is a conservative graph model, not a demonstrated algorithm defect.
On diagonals the effective angle differs because horizontal spacing increases.

A physical discontinuity and an average grade are different quantities. Two
centre elevations are compatible with both a smooth ramp and a local jump.
Resampling20 m CTX into4 m cells adds samples, not centimetre-scale information.
The experiment records this ambiguity rather than deleting the current step gate.

## Audit of shared checks
Graph geometry, continuous connectors and policy segment validation reuse directed
slope/height-change checks and swept clearance. Policy checks full rasterized
segments, not just endpoints. The scientific wrapper retains that geometry;
ScientificContext.validate forbids weaker step/slope/sigma profile limits.
Costs use shared estimate_segment/estimate_activity; their grade dependence is
an estimate, not an additional collision certificate. No equations are changed.
Mapping derives gradient-based mask slope, with policy/uncertainty/NoData and
obstacle checks. This overlaps planner slope conservatively but differs from
edge grade. Masks cannot restore microtopography or encode a missing step sensor.
Footprint, obstacles, uncertainty, directional grade and unresolved relief are
independent risks; an absolute centre-height cap conflates grade and local steps.
See core.py, resource_costs.py, replan.py and mapping/core.py; all remain unchanged.

## Evaluator and evidence
terrain_diagnostics.diagnose accepts an adjacent directed edge and explicit
MEASURED/ORBITAL_ESTIMATE/SYNTHETIC provenance plus native resolution. Longitudinal
angle is atan2(dz,h). A known3x3 least-squares plane estimates signed transverse
grade relative to heading; RMS plane residual describes raster-scale irregularity.
It is not wheel-scale roughness, uncertainty propagation or a rollover limit.
The diagnostic reuses the conservative existing swept-footprint clearance.
Missing/invalid/high-sigma support removes the local plane estimate.

No local-step value is produced from centre elevations. Optional explicit paired
samples have along-track offsets, heights, source identity and native spacing;
the synthetic abrupt case uses samples at1.995/2.005 m across a0.349955 m jump.
That records a resolved jump indicator at1 cm synthetic support, not proof of a
mathematically discontinuous surface or measured Mars relief. Orbital evidence
cannot supply this object. Even a resolved pair does not characterize the rest
of a footprint, traction, dynamics or all subcell features. Every result has
current authorization=false and never reports a safe/pass state.

## Scenarios and human/rover comparison
Tests cover both published human/rover geometry projections separately: flat;
analytic5/10/15 degree ramps;45 degree over-limit; abrupt jump with the same
endpoint difference as5 degrees; descending grade; transverse10 degree hillside;
crest, valley, heading change; irregular surface with an obstacle; high sigma;
NoData; and a longer obstacle detour. Published parameters/coefficients are read
unchanged. These are synthetic analytical fixtures, not NASA observations.
Both agents retain max_step0.2; independent footprint, speed, slope and energy
profiles can change search outcomes. Directed science energy differs uphill
versus downhill in both profiles. Drone flight is explicitly excluded.

Each comparison stores agent/profile, grid/native support, dz, longitudinal and
transverse angles, plane residual, jump/ambiguity, sigma, clearance, diagnostic
reasons, actual legacy status/reason, expanded labels and latency in JUnit.
No UNKNOWN or SEARCH_LIMIT is relabelled. Ordinary flat/ramp evidence remains
INSUFFICIENT_TERRAIN_EVIDENCE for unresolved local relief, even if search FEASIBLE.
An over-limit grade or resolved excessive jump yields REJECT_DIAGNOSTIC.
Tests assert repeatability and unchanged original height arrays.

The initial alternative-rover fixture returned INSUFFICIENT_BUDGET under the
inherited1000 s allowance. Final comparison uses an explicitly synthetic10000 s
time allowance to isolate geometric detours; energy/reserves and published
budgets/configuration files are unchanged. This is not a mission allocation.
The first31 pass/1 fail run is historical under ignored tmp/terrain-first.xml.
Final cases/results and source hashes are in evidence/planner-terrain-local.

## F-TERRAIN-02 proposal and acceptance criteria
David must distinguish conservative graph-height bounds from a local-obstacle
threshold, approve required cross-slope/roughness/traction limits and missing-evidence
policy. Daniel must supply native support, registration/vertical uncertainty,
provenance and actually resolved local obstacle evidence. Jesus reviews any future
transport/versioning and consumers. No new threshold or acceptance is selected here.

Before operational admission changes: (1) independently reproduce the ramp/jump
ambiguity and resolved synthetic counterexample; (2) document evidence support
and uncertainty over the entire swept footprint; (3) validate diagonal/continuous
and raster-crossing paths, crests/valleys, NoData and exact threshold boundaries;
(4) reconcile mapping and planner interpretations across owners; (5) preserve
FAST/SAFE, reserves, directed return, science/oracle and legacy regression gates;
(6) obtain a separately reviewed explicit opt-in with UNKNOWN on missing required
terrain evidence. Step removal or profile relaxation is not authorized by this study.

This local extension respects D-DEL-03: no delivery baseline change, ROS activation,
public data change, UI-scene input, evaluator HiRISE access, publication or physical
safety claim. Organizer notification/endorsement remains a separate Jesus/David
delivery responsibility; this experiment does not establish readiness to submit.

Final validation:32 new cases passed; full Python1268 passed/22 skipped/0 failed.
All legacy/C2/MVP/oracle cases are included. One existing Starlette warning.
Repository and diff checks passed. Native ROS/web were not repeated for this
non-runtime module; earlier prepared-branch checks remain historical.
A stricter draft assertion failed twice because obstacle-invalidated patches
correctly have unavailable roughness, then was corrected without code relaxation.
