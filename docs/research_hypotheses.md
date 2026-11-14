# Optional research hypotheses

These are proposed experiments, not implemented capabilities or acceptance
results. They do not block the [probable mission](mission_checklist.md).

## H-DAN-01: informed synthetic terrain and seeded planner adaptation

Recorded: 14 November 2026, from the project owner's proposal.
Owner: Daniel. Priority: **P1, time permitting**. Scientific review: David.
Planner evaluation: Diego; integration/reference isolation: Jesus.
State: **proposed and untested**. No generator, new map, rover-image import or
experiment is delivered by this record.

### Hypothesis

A coarse orbital terrain prior can anchor an ensemble of finer-grid, explicitly
synthetic worlds. Rover photographs may inform plausible scenario families and
parameter assumptions. Simulated drone reconnaissance can reveal limited parts
of those worlds as higher-detail synthetic observations. We can then test whether
the unchanged planner adapts to the new knowledge by rerouting, rejecting a task
or reporting a reasoned block while preserving return and resources.

The hypothesis concerns adaptation within declared hypothetical environments.
Its applicability to Mars and the realism of the generated detail remain open.
Fine sampling, attractive rendering and informed assumptions do not make a map
observationally accurate. An orbital image is not itself a DEM; use an identified
terrain product or document any tested elevation derivation separately.

For this classical planner, domain randomization means a controlled ensemble of
terrain/observation variations, not a claim that the planner learns a policy or
that simulation-to-real transfer has been demonstrated. Methodological background:
[Tobin et al. (2017)](https://arxiv.org/abs/1703.06907) studies randomized simulated
images for visual learning; it is not evidence for this terrain/planning hypothesis.

### Smallest useful experiment

1. Freeze the public orbital prior, source hashes, extent, frame/datum, NoData,
   initial knowledge, A/B, resource model and budgets. Keep observed and unknown
   cells distinct. Reuse P0 handoffs rather than changing their interfaces.
2. Generate a private synthetic world using a versioned procedural generator,
   scenario family, parameters and seed. Preserve the coarse terrain envelope
   within a tolerance agreed by David; add bounded hypothetical relief,
   roughness, obstacles or corridor structure. A denser grid adds modeled detail,
   not new native information from the orbital product. Do not fabricate a
   measured soil, friction or slip field from image appearance.
3. Use rover images as traceable qualitative references. Metric rock size,
   density, height or physical properties require an adequate calibrated
   derivation or an explicit assumed range with sensitivity checks. A photograph
   from another location is an analog, not a measurement at the mission site.
4. Let the simulated sensor reveal only its footprint, with source kind
   SIMULATED, observation ID, uncertainty/noise assumptions and map-version
   updates. Keep the full synthetic world and unobserved future information
   isolated from planner, mission and public viewer, just like held-out reference.
   Keep it distinct from the observational HiRISE evaluator product.
5. Record the response from the current pose: invalidated route, new candidate
   or explicit rejection, costs, return reserve and reason. An UNKNOWN result
   before sufficient observations is valid; never force a feasible answer.

Prioritize numerical height/mask/uncertainty fields that affect planning over
photorealistic textures. Camera reconstruction and a learned image generator
are not prerequisites for this pilot. Any wire-contract change still requires
the normal coordinated ICD/version review.

### Qualitative diversity and seed control

Different seeds do not guarantee different mission outcomes. Choose explicit
scenario families first, then freeze a small seed set per family before running:

| Family | Intended distinction to verify, not a result already observed |
| --- | --- |
| Open corridor | Primary and return remain feasible after observation. |
| Newly blocked corridor with an alternative | Discovery invalidates the old route; a resource-feasible detour is selected. |
| No admissible alternative | The planner/mission reports a justified block or abort without calling it mission success. |
| Optional resource-stress variant | Geometry permits a route, but full mission/return costs exceed a fixed applicable budget. |

Keep separate terrain, sensor-noise and policy random streams. Record their
seeds and generator versions: a policy's extra observations must not regenerate
the underlying world. Compare policies on identical worlds, budgets and initial
knowledge. Do not search seeds until a preferred narrative appears, or discard
failed/boring cases. Different maps may correctly produce the same route when
their changed cells do not affect the decision. Report that outcome honestly.

### Pilot acceptance and possible refutation

- [ ] David approves the assumption register, parameter bounds, diversity
  criteria and numerical tolerances before evaluation; no occurrence frequency
  on Mars is inferred from a deliberately constructed scenario family.
- [ ] Same family/seed/configuration and pinned versions reproduce the canonical
  map/array hash. Preserve separate file hashes and generation timestamps.
- [ ] The pilot includes structurally distinct maps and verifies the declared
  family distinctions, using connectivity, route/cost change and reason codes;
  changed texture or pixel noise alone is insufficient diversity evidence.
- [ ] A blocked active segment with a feasible alternative causes correct
  invalidation/replanning. A genuine no-path/budget case produces the correct
  reason. Ground traversal and reserves remain valid under the stated model.
- [ ] Full worlds remain inaccessible; only accepted simulated footprint updates
  alter belief, once per observation. No reference leak or prior-to-observation
  promotion can explain the apparent improvement.
- [ ] Publish N, all seeds/families, successes, failures, aborts, replan latency,
  path/resource changes and limitations. Distinguish planner-only fixtures from
  integrated three-agent mission evidence and exploratory from comparative claims.

Failure to obtain meaningful structural diversity, reproducibility or correct
responses to the predeclared cases does not support the hypothesis for that
configuration. Passing a pilot supports only those generated conditions; it
does not establish real drone sensing, realistic geology or Mars mobility safety.

### Resource lineage and disclosure

Follow [NASA resource traceability](nasa_traceability.md). For every generated
world retain orbital product/file/version/hash, rover image ID/camera/sol or
acquisition time/URL/credits, the visual cue used, each assumed parameter and its
bounds/justification, generator commit, family/seeds, output hashes, synthetic
label and run/decision evidence. No specific raw rover image is selected here;
the [official Perseverance raw-image catalog](https://mars.nasa.gov/mars2020/multimedia/raw-images/)
is the starting reference, not evidence of ingestion.

Keep source observations, processed orbital derivatives, informed synthetic
terrain and simulated sensor outputs identifiable as different artifacts. Label
synthetic content in data metadata, viewer/replay and submission claims. Record
actual AI tool use in descriptive text and metadata; if images/videos are
AI-generated, their visible AI-generated watermark must survive captures/exports.
Do not include NASA branding/design elements in generated media. Never relabel
an assumed world as a NASA observation or a verified LIVE mission.

### Stop rule

Explore only after P0 data/model handoffs are stable and minimum-mission,
replay and submission work remain protected. Daniel first proposes the bounded
pilot for David/Diego review. If it threatens those priorities or the scope
freeze, leave H-DAN-01 deferred; no P0 requirement depends on it.
