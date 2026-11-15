# Science POI dossier (CONT-JOR-01)

Status: **draft for David's audit and Daniel's data import**, 2026-11-15, branch `feat/ux`.
Owner: Jorge. This dossier informs POI and patch selection; it does not assert a universal NASA formula,
does not approve any experiment and does not freeze any contract. Team interpretations are marked
**[team]** and kept apart from what the sources state.

## 1. What NASA missions publish as selection criteria

The sources distinguish three levels. Only statements verified in the cited text are listed; where only
the abstract or a summary section was read, that is said.

### 1.1 Landing site (orbital, before arrival)

| Mission | Published criteria | Source (verified part) |
| --- | --- | --- |
| InSight | Engineering constraints first: elevation at or below −2.5 km (enough atmosphere to slow the lander), latitude, ellipse size, a load-bearing surface without thick dust, low rock abundance and slopes (landing and instrument deployment), and a fragmented regolith about 5 m thick for the heat-flow probe. These limited acceptable areas to western Elysium Planitia. | Golombek et al. 2017, *Selection of the InSight Landing Site*, Space Sci. Rev. 211, 5–95, doi:10.1007/s11214-016-0321-9 (abstract) |
| Mars 2020 | The site (Jezero) was chosen for a former lake with a river delta and carbonate-bearing rocks, favourable for habitability and biosignature studies, with crater-floor volcanic units, rim megabreccia and fluvially deposited clasts adding sample diversity. | Farley et al. 2020, *Mars 2020 Mission Overview*, Space Sci. Rev. 216, 142, doi:10.1007/s11214-020-00762-y (abstract and record summary; full sections not read: **to confirm**) |
| MER (Athena) | Explore two sites where water may once have been present and assess past environmental conditions there. | Squyres et al. 2003, *Athena Mars rover science investigation*, JGR 108(E12), doi:10.1029/2003JE002121 (abstract) |

### 1.2 Local science target (on the ground)

| Mission | Published criteria | Source (verified part) |
| --- | --- | --- |
| Curiosity | Drill targets follow a route planned from orbital mapping around hypotheses; sites sample distinct ancient environments and key geologic contacts (e.g. the Murray–Stimson unconformity), rise through the stratigraphy of Mount Sharp, follow diagenetic features (veins, concretions, alteration halos) and prioritise fine-grained lacustrine mudstones for habitability and organic preservation. | Vasavada 2022, *Mission Overview and Scientific Contributions from the MSL Curiosity Rover After Eight Years of Surface Operations*, Space Sci. Rev. 218, 14, doi:10.1007/s11214-022-00882-7, PMC8981195 (first 100,000 characters; the sampling-system section, with engineering limits, **not read**) |
| MER | Contact science with the arm instruments (Microscopic Imager, APXS, Mössbauer) and the Rock Abrasion Tool, which removes dusty and weathered surfaces to expose fresh rock. | Squyres et al. 2003 (abstract); PDS Geosciences Node, MER Contact Science Target List, urn:nasa:pds:mer_cs_target_list |

### 1.3 Sampling (what is cored and cached)

| Mission | Published criteria and workflow | Source (verified part) |
| --- | --- | --- |
| Mars 2020 | Criteria: represent the units and stratigraphic positions of each campaign; prioritise fine-grained, hydrated, clay-rich rocks for organics and biosignatures; diversify the suite (igneous and sedimentary rocks, several depositional settings, regolith); orient cores for geologic context. Workflow: target identified at a site of interest; standard multi-scale imaging and chemistry/mineralogy; a sample-proxy abrasion patch (about 1 cm deep, 5 cm wide) within tens of centimetres of the core, in the same lithology or layer; coring, in-tube imaging and sealing; a Sample Dossier and Initial Report archived in the PDS. Regolith is exposed by a scuff first. | Herd et al. 2025, *Sampling Mars: Geologic context and preliminary characterization of samples collected by the NASA Mars 2020 Perseverance Rover Mission*, PNAS 122(2), e2404255121, doi:10.1073/pnas.2404255121, PMC11745317 (introduction, campaign sections, Materials and Methods; no dedicated criteria section exists). The abrasion-as-proxy step is also described by Sun et al. 2023, JGR Planets, doi:10.1029/2022JE007613 (abstract and search summary only). |

Engineering constraints for drilling/coring (rock strength, flatness, rover tilt, arm reach) were **not found
in the parts read**; they must not be invented. **[team]** Daniel's coverage/accessibility checks stand in
for them in this project and are labelled as the project's own model.

## 2. Real science sites now used by the viewer

`web/scripts/extract-science-sites.mjs` places each site at **the rover's own published position when it
did that work** (the target itself lies a few metres away); nothing is picked from images.

| World | Sites inside the crop | List (what) | Position (where) |
| --- | --- | --- | --- |
| Jezero (Perseverance) | 13 samples, sol 164–516 | NASA, *Mars Rock Samples*, sealed sol per sample, https://science.nasa.gov/mission/mars-2020-perseverance/mars-rock-samples/ (retrieved 2026-11-15) | Last MMGIS M20 waypoint at or before that sol; feed SHA-256 `bd143ee69241229926abd373e6305b8bbb326d6b5a7b4a8d6935262696f93dc4` |
| Gale (Curiosity) | 8 drill holes, sol 759–1332 | NASA/JPL PIA21254, *Curiosity's Rock or Soil Sampling Sites on Mars, Through November 2016* | Last MMGIS MSL waypoint at or before that sol; feed SHA-256 `5a32324f4b8ba22ebdfac50a503e195f47ccdc876ad4c15b19e29dc7cef15a09` |
| Gusev (Spirit) | 111 contact-science features, sol 13–1922 | PDS MER Contact Science Target List, `mera_cs_target_list.csv`, SHA-256 `f8bbb72ab4e26f7198975d58b824294b3f4c0b664f5a08da000a223d295f014f` | Rover position at the target's site/drive in the PDS corrected traverse `MERA_traverse.csv` |
| Meridiani (Opportunity) | 37 contact-science features, sol 2669–5024 | `merb_cs_target_list.csv`, SHA-256 `b8e4ab8e87ea03b5ff485b7d78d129cc8bc6263fca7e8e181107d6714d8c04a9` | Same, `MERB_traverse_5130.csv` (tied to the published landing site by the frontend: tens of metres) |
| Elysium (InSight) | none: a lander has no traverse targets | — | InSight lander shown at NASA's published coordinates |
| Valles Marineris (Melas) | none: no landed mission | — | — |

## 3. Candidate matrix

Objective → published criterion → observed supporting product → uncertainty → coverage/accessibility →
recommendation. Accessibility is the project's slope-limited drive on the 8 m DEM (**[team]** model, not
a NASA criterion).

| World / site | Objective | Published criterion it meets | Supporting product | Uncertainty | Coverage / access in this project | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| Jezero · Salette (C) | Igneous crater floor (Séítah) | Mars 2020: represent the units of the campaign; diversity of the suite (Herd 2025) | NASA sample list (sol 262, rock Brac, South Séítah); MMGIS stop 8_0; CTX DTM 20 m | Rover stop vs core: metres; sealed sol used as sampling sol | Drivable, 903 m from the rover's home | Keep as inspection target |
| Jezero · Swift Run (D) | Delta front sediments | Mars 2020: fine-grained sedimentary rocks for biosignatures (Herd 2025) | Sample list (sol 490, Skinner Ridge); stop 26_1004 | As above | 2.9 km: beyond the illustrative budget, rejected in the story | Keep as the out-of-budget case |
| Gale · Buckskin (C) | Murray formation, Marias Pass | Curiosity: distinct environments and contacts (Vasavada 2022) | PIA21254 (sol 1060); stop 48_2542; MSL Gale DEM 8 m | Stop vs hole: metres | Drivable, 607 m | Keep |
| Gale · Big Sky (D) | Stimson/Murray area | Curiosity: unit changes and diagenetic halos (Vasavada 2022) | PIA21254 (sol 1119); stop 50_592 | As above | 916 m, rejected by budget | Keep |
| Gusev · Snowboard (C) | Bonneville crater rim rocks | MER: contact science on rock, fresh surfaces by RAT (Squyres 2003) | PDS target list (sol 89, target Shredder); traverse 24_0; Columbia Hills DEM | Site frame vs traverse: metres | Drivable, 220 m | Keep |
| Gusev · Mohave (D) | Plains rocks | As above | PDS target list (sol 150, target Joshua); traverse 61_4 | As above | 2.4 km, rejected | Keep |
| Meridiani · Gibraltar (C) | Endeavour plains/rim approach | As above | PDS target list (sol 2669); traverse 156_573; Endeavour HiRISE DEM | Landing-site tie: tens of metres | Drivable, 2.1 km | Keep; flag the long drive |
| Meridiani · Botany Bay (D) | Cape York, Botany Bay | As above | PDS target list (sol 3332, target Gnarlaroo); traverse 172_1348 | As above | 2.9 km, rejected | Keep |
| Elysium · C, D | — | No published science targets for a traverse | — | — | — | Keep **fictitious**, labelled |
| Valles Marineris · C, D | — | No mission | — | — | — | Keep **fictitious**, labelled; a future patch would need published candidate-site work, not found yet |

**[team]** Story roles: C is the nearest reachable rock target (at least 150 m), D a farther one (at least
1.3 × C's drive); the rover's illustrative energy budget is then set so that C fits and D does not. This is a
demonstration device, not a NASA selection rule. Rock targets (cores, drill holes, contact science on rock)
are preferred over soil, scuffs, regolith and atmosphere, following the bedrock priority above.

## 5. Sites of interest for the astronaut

**Published criteria for human sites.** NASA's 2015 *Exploration Zones* rubric (First Landing Site/Exploration
Zone Workshop for Human Missions to the Surface of Mars; blank rubric
https://www.nasa.gov/wp-content/uploads/2015/06/blank_exploration_zones_rubric_tagged.pdf, page 1, read in
full) scores Regions of Interest within about 100 km of a landing site on:

- Science thresholds: potential for past or present habitability (astrobiology); Noachian/Hesperian rocks with
  trapped atmospheric gases (atmosphere); a range of geologic time with datable surfaces, evidence of aqueous
  processes and potential for relative ages (geoscience); plus qualifying criteria (organic matter with surface
  exposure, igneous provinces, ancient bedrock, remnant magnetisation, impact deposits, aeolian diversity).
- Resources (ISRU): ice or ice/regolith mix and/or hydrated minerals in quantity, minable by automated systems,
  less than 3 km from processing and no more than 3 m deep; metal/silicon resources likewise.
- Civil engineering threshold: a ~50 km² region of flat, stable terrain with sparse rocks, slope below 10° at
  the 1–10 km scale, within 5 km of the landing site; qualifying: northern hemisphere, loose regolith with
  cobble-size or smaller rocks, useful terrain features. Food production: low latitude, no shadowing terrain,
  access to water and to dark basaltic sands.
- Engineering first-order criteria: latitude, elevation, thermal inertia.

**Applied in the viewer** (`web/scripts/make-demo-fixture.mjs`, astronaut sites; `for_agent: HUMAN` in each
manifest, grouped under *Astronaut* in the Sites list):

| World · site | Objective | Criterion | Supporting product | Uncertainty | Access | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| Jezero · Three Forks depot | Retrieve the cached samples | Mars Sample Return objective (Farley et al. 2020, abstract): samples cached for return | PDS `urn:nasa:pds:mars2020_sample_depot_three_forks`, `sample_tube_locations.csv` | Rover position per drop; tube within about 1–2 m | 2.60 km on foot from base A on a slope-limited route (project model) | Keep: an astronaut-specific retrieval task |
| Jezero · Habitat area | Base/landing pad on flat, stable ground | Rubric civil engineering: slope < 10° at 1–10 km, within 5 km of the landing site | Scene DEM (8 m) | 1 km-scale slope 0.9°, mean 8 m slope 1.6°, 0 % of cells > 10°; rocks not assessed | 4.80 km from base A | Candidate only; needs rock abundance and the ~50 km² area check |
| Gale · Lubango | Field geology at a site the rover already characterised | Mars 2020 / MSL / MER target criteria (section 1) | Same as section 2 | As section 2 | Walkable from goal B (project slope limit 20°) | Keep as the astronaut's science stop |
| Gale · Habitat area | Base/landing pad on flat, stable ground | Rubric civil engineering: slope < 10° at 1–10 km, within 5 km of the landing site | Scene DEM (8 m) | 1 km-scale slope 4.2°, mean 8 m slope 4.9°, 3 % of cells > 10°; rocks not assessed | 2.61 km from base A | Candidate only; needs rock abundance and the ~50 km² area check |
| Gusev · Truckin Flats | Field geology at a site the rover already characterised | Mars 2020 / MSL / MER target criteria (section 1) | Same as section 2 | As section 2 | Walkable from goal B (project slope limit 20°) | Keep as the astronaut's science stop |
| Gusev · Habitat area | Base/landing pad on flat, stable ground | Rubric civil engineering: slope < 10° at 1–10 km, within 5 km of the landing site | Scene DEM (8 m) | 1 km-scale slope 0.2°, mean 8 m slope 1.3°, 0 % of cells > 10°; rocks not assessed | 1.29 km from base A | Candidate only; needs rock abundance and the ~50 km² area check |
| Meridiani · NW Bench | Field geology at a site the rover already characterised | Mars 2020 / MSL / MER target criteria (section 1) | Same as section 2 | As section 2 | Walkable from goal B (project slope limit 20°) | Keep as the astronaut's science stop |
| Meridiani · Habitat area | Base/landing pad on flat, stable ground | Rubric civil engineering: slope < 10° at 1–10 km, within 5 km of the landing site | Scene DEM (8 m) | 1 km-scale slope 0.3°, mean 8 m slope 0.4°, 0 % of cells > 10°; rocks not assessed | 3.68 km from base A | Candidate only; needs rock abundance and the ~50 km² area check |
| Elysium · Habitat area | Base/landing pad on flat, stable ground | Rubric civil engineering: slope < 10° at 1–10 km, within 5 km of the landing site | Scene DEM (8 m) | 1 km-scale slope 0.2°, mean 8 m slope 0.7°, 0 % of cells > 10°; rocks not assessed | 2.43 km from base A | Candidate only; needs rock abundance and the ~50 km² area check |
| Valles Marineris · Habitat area | Base/landing pad on flat, stable ground | Rubric civil engineering: slope < 10° at 1–10 km, within 5 km of the landing site | Scene DEM (8 m) | 1 km-scale slope 1.9°, mean 8 m slope 3.9°, 1 % of cells > 10°; rocks not assessed | 3.03 km from base A | Candidate only; needs rock abundance and the ~50 km² area check |

Not assessed, and not invented: water ice and hydrated minerals (no CRISM, SHARAD or SWIM product imported;
these equatorial crops are unlikely ice sites), rock abundance, thermal inertia, metal/silicon. **[team]** The
astronaut science stop is the real science site nearest to goal B within 1.2 km that the astronaut can walk to;
the habitat window is the gentlest 1 km² area passing the slope criterion within 5 km of base A. Both are
demonstration rules for David's review.

## 6. Water, ice and radiation for the astronaut

Per world (`web/scripts/extract-zone-environment.mjs` → `web/scripts/data/zone_environment.json`). **Documented
only**: not yet in the scene packages or the viewer, to be implemented later in another part of the interface
(owner's decision, 15 November 2026).

| World | Water (Odyssey GRS) | Ice (SWIM) | Pressure (Pa) | Absorbed (mGy/day) | Dose equivalent (mSv/day) | Basis |
| --- | --- | --- | --- | --- | --- | --- |
| Jezero | 3.5 ± 0.4 wt% | not imported | 706 | 0.225 ± 0.040 | 0.69 ± 0.14 | RAD relation |
| Gale | 5.4 ± 0.4 wt% | not imported | 817 | 0.210 ± 0.040 | 0.64 ± 0.12 | measured (RAD) |
| Gusev | 7.3 ± 0.4 wt% | not imported | 668 | 0.230 ± 0.040 | 0.70 ± 0.14 | RAD relation, **outside 700–950 Pa** |
| Meridiani | 5.3 ± 0.4 wt% | not imported | 641 | 0.234 ± 0.041 | 0.71 ± 0.14 | RAD relation, **outside 700–950 Pa** |
| Elysium | 5.2 ± 0.4 wt% | not imported | 700 | 0.226 ± 0.040 | 0.69 ± 0.14 | InSight measured pressure; RAD relation |
| Valles Marineris | 3.4 ± 0.3 wt% | not imported | 741 | 0.220 ± 0.040 | 0.67 ± 0.14 | RAD relation |

- **Water**: Mars Odyssey Gamma Ray Spectrometer H2O concentration, smoothed 5° × 5° map
  (PDS ODY-M-GRS-5-ELEMENTS-V1.0, `H2O_SR_5X5.TAB`, SHA-256 `5cec0d637755ddb7a451f58d7b24b6fb34f081e3391b40cdfca5410200da0236`; Boynton et
  al. 2007, JGR 112, E12S99). Water-equivalent hydrogen in the top few tens of centimetres; the product does
  not say whether it is ice or bound in minerals, and a 5° cell (about 300 km) is far larger than a scene.
- **Ice**: SWIM 2.0 (−60 to 60° N) covers these latitudes, but swim.psi.edu answered HTTP 523 (Cloudflare:
  origin unreachable) to the scripts and to a browser on 2026-11-15, and no copy was found elsewhere or in the
  owner's Drive. No ice value is imported or estimated. **To do** when the server is back.
- **Radiation** (galactic cosmic rays; read in full: Guo et al. 2018, arXiv:1712.06987, sections 2.3 and 3.3):
  - Measured at Gale by MSL RAD: 0.21 ± 0.04 mGy/day absorbed, 0.64 ± 0.12 mSv/day dose equivalent, mean
    quality factor ⟨Q⟩ = 3.05 ± 0.3 (Hassler et al. 2014, Science 343, doi:10.1126/science.1244797).
  - Guo et al. 2018 (JGR Planets, doi:10.1002/2016JE005206), section 3.3: the measured anticorrelation of the
    RAD dose rate with surface pressure is −κ = c0 + c1·Φ with c0 = 0.28 ± 0.03 µGy/day/Pa and
    c1 = −2.9 ± 0.6 × 10⁻⁴ µGy/day/Pa/MV, measured between about 700 and 950 Pa (18.9–25.7 g/cm²); at
    Φ = 500 MV, the period of Hassler et al., −κ = 0.135 µGy/day/Pa. The paper states that extrapolating the
    linear relation outside the measured pressures is still an open question, and that the relative change
    of dose equivalent with depth is larger than that of the dose rate (so a constant ⟨Q⟩ understates it).
  - Applied: absorbed = 0.21 mGy/day + |κ| × (817 Pa − P); dose equivalent = absorbed × ⟨Q⟩; errors
    propagated. Pressures: Gale, the annual mean of the REMS daily summaries (817 Pa); Elysium, InSight's
    measured annual mean of about 700 Pa (Lange et al. 2022, JGR Planets 127, e2022JE007190, section 2.2);
    the others, hydrostatic from Gale with the scene elevation difference and the 11.1 km scale height (NASA
    Mars Fact Sheet). Check: that formula gives 711 Pa for InSight, 1.6 % above the measured 700 Pa.
  - Gusev and Meridiani fall below 700 Pa: their values are flagged as outside the measured range. Suit,
    vehicle and habitat shielding and solar particle events are not modelled.

## 4. Open items

- David: audit sections 1–3 and approve or change the matrix and the **[team]** rules.
- Daniel: confirm the products in section 2 can be located and imported (all are public, hashed above).
- Confirm in full text: Farley et al. 2020 selection sections; Vasavada 2022 section 8 (sampling system and
  engineering limits); Anderson et al. 2012, *Collecting Samples in Gale Crater, Mars*, Space Sci. Rev. 170.
- PIA21254 stops at sol 1495; later Curiosity drill holes are not listed here.
- Opportunity positions inherit the landing-site tie of the traverse (tens of metres).
- Ice (section 6): import SWIM 2.0 when swim.psi.edu answers. Radiation outside 700–950 Pa (Gusev,
  Meridiani) rests on an extrapolation the source calls unverified.
- Astronaut sites (section 5): the habitat window does not check the rubric's ~50 km² area or rocks; resources are not assessed.
