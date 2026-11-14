# NASA resource-to-result traceability

Owner: Daniel for terrain; David for scientific models; Jesus for run binding;
Jorge for public source access. Supports [the minimum mission checklist](mission_checklist.md),
R03-R06, R16 and R17. A citation, a valid JSON manifest and a completed import are
different evidence states. No new acceptance is claimed by writing this register.

This branch contains planning documentation. Links to planner inputs and
computational evidence identify their published implementation revision; those
code/data changes are not copied into this documentation branch.

## Current resource register

| Source ID | Official product / role | Observed state and remaining proof |
| --- | --- | --- |
| NASA-CTX | MRO/CTX, [USGS DTM release, DOI 10.5066/P906QQT8](https://www.usgs.gov/data/mars-2020-terrain-relative-navigation-ctx-dtm-mosaic). Public prior. | A newly processed provisional crop is recorded in [the manifest](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/34c515b6b86f73336844e8b3614c70b144574ec3/data/planner_provisional/manifest.json) and [processing record](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/blob/34c515b6b86f73336844e8b3614c70b144574ec3/docs/planner_provenance.md). Native post spacing 20 m; 4 m computational cells add no native detail. Import/finite samples do not verify ground traversal. Daniel's final release and consumer acceptance remain open. |
| NASA-HIR | MRO/HiRISE, [USGS DTM release, DOI 10.5066/P9REJ9JN](https://www.usgs.gov/data/mars-2020-terrain-relative-navigation-hirise-dtm-mosaic). Isolated evaluator reference. | A private provisional crop/manifest exists locally under data/reference; excluded from Git/public runtime. Product post spacing 1 m. Topography is not mobility ground truth. Record source identity and evaluator configuration without exporting the full reference through planner/mission/web payloads. |
| NASA-MOLA | MGS/MOLA, [PDS derived-topography bundle](https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?identifier=urn%3Anasa%3Apds%3Amgs_mola_topography_derived&version=1.0). Regional context/area selection. | Exact collection, product/version and file still pending. Supply a regional derivative plus a recorded area-selection or validation decision. A CTX/HiRISE datum containing MOLA in its name is not proof of separate MGS data ingestion or contribution. |

The provisional CTX derivative was retrieved on 14 November 2026 at 15:22:49 UTC
and processed at 15:22:52 UTC. Its manifest contains the exact product ID,
artifact/source-window hashes, source/target CRS, datum, NoData, resampling,
processing versions and controls. Keep that manifest as the authoritative record
rather than duplicating changing hashes here. Revalidate the actual bytes before
binding a later run. The provisional manifest differs from the final proposed
terrain schema; it must not be relabelled ready without an explicit reviewed
adapter/schema decision and consumer tests.

CTX and HiRISE are both MRO instruments. R03's meaningful MRO + MGS contribution
is the team's requirement; official competition eligibility must be checked
separately. Source observations predate their import; processing dates do not
change observation dates or establish eligibility.

## Competition reference resources

Use the official sources prioritized in AGENTS.md. Record actual use, including
non-use, instead of claiming that every linked resource supplied scientific data.

| Resource | Permitted planned role / record |
| --- | --- |
| [JPL Mars Trek](https://trek.nasa.gov/mars/) | Discovery, context and layer inspection. Record specific layer/product ID, footprint and date, then the actual downloaded product/terms if used in computation. A portal URL alone is insufficient. |
| [USGS-NASA interactive Mars maps](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars) | Geological context/area selection when actually used. Record map release, scale, unit/feature and the decision informed. Geological interpretation is not an observed traversability mask. |
| [Curiosity proposed Mount Sharp route](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/) | Optional annotated-route design reference. If adopted, record design-reference use; do not represent its route as Jezero mission input. |
| [NASA Worldview](https://worldview.earthdata.nasa.gov/) | Optional Earth imagery/temporal-view reference. Not a Mars elevation input; do not claim use if no actual material or design reference was adopted. |
| [Perseverance raw images](https://mars.nasa.gov/mars2020/multimedia/raw-images/) | Optional contextual image, with exact image ID, camera, acquisition time/sol and required credits/terms. No calibrated local DEM, obstacle detection or stereo reconstruction is claimed without an implemented and tested derivation. |

## Scientific-model resources

David's parallel science front proposes activity/grade models with parameter-level
source locators, units, derived formulas, sensitivity ranges and approval states.
Import those records together with their implementation and checks; do not infer
approval from the existence of source-backed values or a configuration projection.

| Source ID | Primary reference | Traceability obligation |
| --- | --- | --- |
| SCI-HUMAN-ACTIVITY | [NASA/TM-2010-216138, Table 4](https://ntrs.nasa.gov/api/citations/20110001417/downloads/20110001417.pdf#page=21) | Identify the lunar-analog context and every proposed adaptation to the Mars model. |
| SCI-HUMAN-OXYGEN | [NASA BVAD Rev2, Table 4-70](https://ntrs.nasa.gov/api/citations/20210024855/downloads/BVAD_2.15.22-final.pdf?attachment=true#page=149) | Separate published aggregate references, oxygen/energy conversion assumptions and gas-volume convention; no suit-certification claim. |
| SCI-ROVER | [JPL LSOS/ROAMS model background](https://dartslab.jpl.nasa.gov/References/pdf/2011-howard_ieeeaero_2011.pdf), [Perseverance components](https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/) | Distinguish model structure/reference scales from team-selected rolling, slip, efficiency and auxiliary-load coefficients. |
| SCI-DRONE | [Ingenuity overview](https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/), [flight-control/aerodynamics report](https://science.nasa.gov/blog/what-were-learning-about-ingenuitys-flight-control-and-aerodynamic-performance/) | Keep flight reference values separate from assumed auxiliary power, activity mapping and kinematic simplifications. |

Final budget, position and tolerance choices remain mission configuration, not
NASA measurements. Pin model ID/configuration hash with every route/run. The
current ROS wire does not carry that hash; deployment records must establish
identity and numerical agreement must be checked separately (DAV-02/DIE-02).

## Required lineage at each boundary

1. **Original resource:** source ID, mission/instrument or publication, exact
   product/file/version, observation/publication date, retrieval time, URL/DOI,
   citation and license/terms. For ranged acquisition identify the source window,
   its value/byte hash and upstream version/ETag; do not pretend it is a full-file
   checksum. An ETag alone is not a scientific-content SHA-256.
2. **Processing:** input hashes, command and code revision, crop/bounds, CRS/datum,
   native/output post spacing, row orientation, units, NoData, resampling,
   uncertainty assumptions, tool versions, output files/hashes and timestamp.
3. **Runtime input:** dataset ID, prior/belief/observed role, public layer hashes,
   profile/model identity, run ID, map version, unique batch stamp and clock.
   Preserve the distinction between validity, knowledge and traversability.
4. **Observation/decision:** SIMULATED source kind where applicable, observation
   ID/footprint/uncertainty/seed, accepted version update, request/route/event IDs,
   pose and resource state, costs, reason and causal link. Synthetic obstacles
   and formula fixtures retain their own provenance, not a NASA-observation label.
5. **Evidence/result:** acceptance-case ID, expected/observed result, command,
   environment, commit/configuration/source hashes, metrics, failures, reviewer
   and limitations under a new immutable evidence/<run_id>/ directory.
6. **Public claim:** replay/figure/presentation item identifies the supporting
   run/test and source IDs. Export only allowed layers. Record each resource's
   concrete contribution to a layer, selection, cost assumption or evaluation;
   merely listing it as a credit does not prove use.

For a selected decision a reviewer must be able to travel both directions:
official resource -> processed input -> map/model -> decision -> test -> claim,
and claim -> exact run -> exact input bytes/configuration -> source citation.
The existing file manifest covers part of this chain; run and processing records
must supply the remainder without silently extending or freezing the ICD.

## Optional synthetic-terrain research

[H-DAN-01](research_hypotheses.md) proposes a time-permitting experiment for
Daniel, not a new NASA dataset or implemented sensing capability. Keep orbital
inputs and rover-image references tied to explicit assumed generation parameters;
record generator/configuration versions, family/seeds and canonical output hashes.
Coarse-source resolution remains unchanged even when synthetic detail is added.

Separate observational products, processed orbital derivatives, informed
synthetic worlds and simulated observations in provenance and public claims.
The full synthetic world is held out; only simulated footprint observations may
reach belief. Preserve applicable AI declarations/watermarks in later artifacts.
No raw rover image, synthetic map or new measured result is added by this proposal.

## Release checklist

- [ ] Daniel verifies source/derived hashes and permitted distribution; David
  approves scientific scale, adaptation assumptions and the claimed contribution.
- [ ] Consumers verify non-collinear controls and an asymmetric mask. Current
  provisional diagonal-only controls are insufficient to rule out x/y swapping.
- [ ] Jesus confirms that planner/mission/web runtime packages cannot read the
  held-out reference or future tasks; source citation does not grant runtime access.
- [ ] Each presentation claim resolves to an actual recorded run or is explicitly
  labelled proposed/unvalidated. The unverified CTX prior still returns UNKNOWN.
- [ ] Jorge preserves source access, simulation/replay labels and applicable
  required watermarks in the final browser view, captures and exports.
- [ ] All owners reconcile [AI text](AI_USAGE.md), [AI metadata](ai_usage.json),
  source attribution, licenses and competition submission declarations. Tool-use
  disclosure is not an authorship signature. Check the organizer's final rules
  and local cutoff instead of inferring eligibility from this engineering plan.
