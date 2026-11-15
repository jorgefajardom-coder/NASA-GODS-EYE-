# Mars Gods Eye — web viewer

Owner: Jorge. Integration: Jesús. Scientific review: David.

3D mission viewer: terrain layers, routes, agents and mission events on real Mars
terrain, with a saved-run replay that needs no ROS, Gazebo or network.

## Status

**REPLAY mode only**. The live link is shown as offline: the gateway
is not connected to the viewer. The viewer opens only the simulated `demo`; recorded MOCK
packages are neither offered nor used by the viewer (see the Run selector below).

| Part | What it is |
|---|---|
| Recorded recovery package (`recorded-recovery-001`) | **Not used by the viewer.** Kept in `public/replay/` only for the team's contract and consumer tests; it declares `source_mode` MOCK and ends `READY`, not scientific `COMPLETE` |
| Demo terrain | **Real**: a provisional 3.4 km × 7.6 km crop of the NASA/USGS Mars 2020 TRN CTX DTM (centre 18.490° N, 77.435° E) that joins the Perseverance landing area (south) with the terrain 5.4 km to its north (the earlier demo area), drawn on an **8 m display grid** (425 × 950 cells) interpolated from the **20 m** source: finer cells, no new detail |
| Gale world (`?run=gale-demo`, or *Zones* / `Z` in the map view) | **Real**: a 3.4 km × 7.6 km crop of the NASA/USGS MSL Gale crater DEM mosaic (1 m, HiRISE and CTX stereo; only its 8 m overview is read, about 1.7 MB) at the foot of Mount Sharp, relief about 900 m, draped with the MRO CTX Gale mosaic (Trek layer `Gale_CTX_BlockAdj_dd`, 10 m/px). Curiosity's real stops (sol 751 to 4462, thinned to at least 80 m apart: 166 of the crop's) are marked and toured. NASA's Curiosity raw-image feed gives only the **sol** of each image, so a stop shows that sol's images (the rover may have moved); 30 hops between stops are straight lines because the slope search finds no rover path. No surroundings, geology or weather layers for this world. The mission story is simulated, as in Jezero |
| Zone selector (opens on every load right after the intro; afterwards the *Zones* button or `Z` in the map view; `src/components/ZoneSelector.tsx`, `src/lib/zoneGlobe.ts`, `src/data/worlds.ts`) | A **Mars globe** textured with the **Viking MDIM 2.1 colour mosaic** (NASA/USGS via JPL Mars Trek; 32 level-2 tiles in `public/zones/globe/`, `scripts/extract-globe-tiles.mjs`, stitched in the browser), with one point per zone at **the centre of its scene crop**. The selected zone turns to face the camera and the globe closes in on it; *SELECT ZONE* and *MARS* curve on the planet's left and fade out on the zoom. Its card, fitted **radially** against the planet (left edge concentric with the globe, laid out once per screen size so it never moves or shakes during the turn and zoom), shows the zone's own orbital image (the one draped on its terrain, central 3.4 km), a two-sentence synopsis and its coordinates; hovering another point shows its image. The horizon at the bottom is two smoothed elevation profiles of the Melas Chasma scene DEM, stretched to the band (`scripts/extract-zone-horizon.mjs`, decorative, not to scale). *Travel* zooms the card image to fill the screen (object-fit cover: edge to edge, no black bands), opens the scene, and on arrival the same image lays itself down on the terrain it is draped on: its corners move onto the projected corners of the imagery footprint at the mean ground height (a perspective `matrix3d` warp recomputed every frame, so it follows the camera; `src/lib/arrivalQuad.ts`, `ArrivalAnchor` in `MissionScene.tsx`), a thin scan outline locks on, then it fades into the 3D map. It stays full screen while the scene loads, with no loading screen or static page in between: `index.html` paints the same photo before the app starts and the arrival takes over from it (up to 6 s; without a footprint in view it simply fades), the intro is skipped on arrival and reduced motion skips the warp; travelling to the zone already loaded enters it. Six Mars scenes: Jezero (Perseverance), Gale (Curiosity), **Gusev crater** (`?run=gusev-demo`: Columbia Hills HiRISE/CTX/HRSC DEM mosaic, 1 m averaged to 8 m, over Spirit's whole traverse from the landing site to the Columbia Hills; 108 real Spirit stops, sol 1 to 1866), **Elysium Planitia** (`?run=insight-demo`: InSight DEM mosaic, 20 m, centred on the lander; a flat plain, vertical exaggeration 4 by default; no stops), **Meridiani Planum** (`?run=meridiani-demo`: HiRISE DEM of Endeavour crater's west rim, 1 m averaged to 8 m; 134 real Opportunity stops, sol 2630 to 4922, tied to the published landing site by the frontend) and **Valles Marineris** (`?run=melas-demo`: CTX stereo DEM of a Melas Chasma floor and wall, 24 m, 1.5 km of relief; never visited by a rover, no stops). Spirit and Opportunity stops come from the PDS Geosciences Node corrected traverses (`scripts/extract-mer-traverse.mjs`); NASA's raw-image feed has no MER images, so their photo tour drives through the real stops and says so instead of showing photos. The scenes without stops have no photo tour. DEM crops: `scripts/extract-dem-crop.mjs` from whole Trek DEM files (`scripts/data/<zone>/`); the mission story on every scene is the same simulated one. Keys: ← → , Enter, Esc. Panchromatic images are tinted for display |
| Real Perseverance stops | **Real NASA positions**: 226 rover stops (sol 13 to 708) inside the crop, from NASA's public traverse feed (MMGIS waypoints); position and identifiers only, no image stored. Drawn as camera icons in 3D, on the minimap and the first-person compass. Base A and goal B sit on two of them. Standing still on a stop in first person opens a window that loads, on request, the raw images NASA lists for that exact stop (same sol, site and drive) |
| Demo mission, agents, routes, events | **Generated illustrative story** (`scripts/make-demo-fixture.mjs`); its routes come from a substitute slope-constrained search, not the integrated planner. Rover/drone speeds and motion are simulated |
| Demo adverse case | **Synthetic**: a scarp added to the hidden evaluator reference; it is not in the CTX data |
| Demo POIs C and D | **Real NASA science sites** on the rover worlds, at the rover's published position when it did that work (`scripts/extract-science-sites.mjs`, `scripts/data/<zone>/science_sites.json`): Jezero, Perseverance samples Salette (C) and Swift Run (D) from NASA's sample list; Gale, Curiosity drill holes Buckskin and Big Sky from NASA/JPL PIA21254; Gusev, Spirit contact-science rocks Snowboard and Mohave, and Meridiani, Opportunity's Gibraltar and Botany Bay, from the PDS MER Contact Science Target List. C is the nearest reachable rock target, D a farther one, and the rover's illustrative budget is set from them (a story device). **Fictitious**, and labelled, on Elysium and Valles Marineris, which have no traverse targets. Criteria and matrix: `../docs/science_poi_dossier.md` |
| Astronaut sites | Grouped under *Astronaut* in the Sites list (`pois[].for_agent`). **Three Forks sample depot** (Jezero): Perseverance's ten sealed tubes left for retrieval, at the rover's positions during the drops from the PDS depot bundle (`scripts/extract-three-forks.mjs`). **Science stop**: the real science site nearest to goal B that the astronaut can walk to (Gale, Gusev, Meridiani). **Habitat area**: the flattest 1 km × 1 km ground within 5 km of base A that meets the slope criterion of NASA's 2015 human Exploration Zone rubric (under 10° at the 1 km scale); rocks, the rubric's ~50 km² area, water ice and hydrated minerals are not assessed |
| Water, ice, radiation (Atmos tab of every zone and one line on each zone card; `src/lib/zoneEnvironment.ts`, data in `scripts/data/zone_environment.json`, reasoning in `../docs/science_poi_dossier.md` section 6) | **Water**: Mars Odyssey GRS water-equivalent hydrogen of the 5° cell holding each scene (top tens of cm; ice or minerals not distinguished), PDS ODY-M-GRS-5-ELEMENTS-V1.0. **Ice**: not imported (the SWIM 2.0 server was unreachable). **Radiation**: Gale shows what MSL RAD measured (0.64 ± 0.12 mSv/day); the other scenes apply RAD's measured dose-pressure relation (Guo et al. 2017, −κ = 0.135 µGy/day/Pa at Φ = 500 MV) to their pressure (InSight's measured 700 Pa, else hydrostatic from Gale), times ⟨Q⟩ = 3.05; Gusev and Meridiani are flagged as below RAD's measured 700–950 Pa (`scripts/extract-zone-environment.mjs`). The Atmos panel adds an example dose for a 4 h Marswalk (daily average × 4 / 24) and says that shielding and solar storms are not included, with a link to NASA DONKI |
| Where each site comes from | Each site carries its source in the package (`pois[].source`), shown in the *Sites* list as a tag (**NASA**, **chosen on NASA terrain**, **fictitious**) with the full text in the tooltip. Base A and goal B: real rover stops (within 12 m) on Jezero, Gale, Gusev and Meridiani; chosen by the generator among the flattest DEM cells on Elysium and Valles Marineris, which have no traverse. InSight lander: NASA's published landing coordinates. The drone's survey corridor follows an uncertainty of 3 m that the generator assigns around the middle of route r1: an illustrative assumption, not a measured DEM error |
| Gateway sample `mock-vertical-001` | **Not used by the viewer.** Test package in `../data/sample/replay/` (flat synthetic grid, no Mars data) |
| Uncertainty, budgets, consumption | Illustrative assumptions, not certified limits |
| Atmos tab, HUD atmosphere and dose | NASA weather summaries and published radiation averages (other sites/periods); not the conditions of the simulated run. The HUD pressure map is a barometric **estimate** from one MEDA value, not a measured field |
| Earth and Mars clocks | Your device clock; Mars time from the NASA GISS Mars24 algorithm (real present time, not the replay's) |
| Shadows (astronaut, rover and drone), footprints, dust, rotor blur, wheel and joint motion | **Cosmetic display** derived from the drawn poses; they never change a position in the data |
| Rover, drone, base models | NASA/JPL models with branding removed; the base is **AI-generated** (OpenAI Codex) and prepared in Blender |
| Astronaut portrait | **AI-generated** (ChatGPT), shown beside human_1 in the details panel with a burned-in `AI-generated` watermark |
| Intro screen | **AI-generated** video (Kling), skippable, with one discreet `AI-GENERATED · KLING` mark burned into every frame (no second label on screen); its audio track is declared and the clip plays muted |
| Team logo | **AI-generated** image (ChatGPT, edited by the team) with a visible `AI-generated` watermark (`public/assets/brand/`) |
| Link preview | **Real NASA image**: Viking global colour mosaic PIA00407 (NASA/JPL/USGS), centred on black, no text (`public/assets/brand/og-image.jpg`) |
| Tab icon | Illustration of Mars made by the team (`public/favicon.ico`, PNG sizes up to 512 px); not AI-generated |
| Slope layer | Derived from the orbital prior with Horn 3×3 at the run's grid spacing; source and grid spacing are displayed separately. Not a local hazard measurement |
| Demo surroundings (option, off by default) | Same CTX DTM over 20 km (100 m box average, `scripts/extract-ctx-context.mjs`) and CTX orthomosaic at 40 m; context only, checked for matching origin/datum/source before loading |
| Terrain scan | The orbital slope above and NoData, redrawn around the astronaut as a visual pulse; **not an observation, sensor or command**, no data changes |
| First-person route | The recorded route in force draped on the ground, with the next waypoint and its straight-line distance |
| Terrain formation, height morph, interface entrance, camera sway | **Cosmetic display** animations; no height or pose in the data changes |
| Route sufficiency alert | **Estimate**: route cost spread per metre against what is left, finishing vs walking back, 20 % JZ-P06 reserve ([rationale](../docs/route_resource_sufficiency.md)); pending science review, display only |
| Sun and sky | Sun from Mars24 at the real present time and site; sky colours are a display rendering |
| Stars | **Real catalogue**: Yale Bright Star Catalogue V ≤ 5.5 placed with the IAU 2009 Mars rotation model (`public/assets/sky/bright_stars.json`) |
| Artificial light (default), night fill, helmet lights | **Display** lighting choices, not sunlight or suit specifications; *Real light* (`I`) shows the hour's real light |
| Perseverance raw images (Atmos tab, and `M` in first person) | **Real NASA/JPL-Caltech images**, read from the public raw-images JSON feed **only when the person presses a load button** (needs a network; nothing is stored or bundled). They show where the rover is now, not the replay's site; not terrain data, never read by the map or planner. The shared loader keeps each result's mission and request (latest images or one stop and sol), so the Atmos panel only shows the latest Perseverance images and a tour's Curiosity photos are never shown as Perseverance's. First person: a *Mars now* window in the dock, the same size as the drone camera window |
| Rover photo tour (button *Photo tour*, in the four rover zones) | After the story, the **simulated** rover drives through **every real stop of the map** (Jezero: 226, sol 13 to 708; Gale: 166, sol 751 to 4462; Gusev: 108, sol 1 to 1866; Meridiani: 134, sol 2630 to 4922) in the order NASA's rover visited them; Spirit and Opportunity have no images in NASA's raw-image feed, so their tours show none and say so. The button follows the rover **from its own camera, with the first-person interface (compass, dial, dock)**; `V` steps back behind the rover to see it driving. On each arrival the replay **holds until every image of the stop (up to 9) has loaded**, then the rover "takes" them one by one (1.5 s each): the camera **turns smoothly towards where each photo was taken** and that photo lights up in the window's grid. Then it drives on. `⏮ Stop` / `Stop ⏭` jump between stops. The direction comes from the feed: Perseverance's `camera_vector` in the rover frame (or its mast angles) turned to the world with the rover's published yaw at the stop, so it is **approximate**; Curiosity's feed has no pointing, so only its hazard cameras are aimed (front and rear). The button is the person's request for the images (needs a network). Each photo is taken with **the real camera, and the eye of its stereo pair, named by the feed** (e.g. `NAVCAM_LEFT`, `MCZ_RIGHT`, `FRONT_HAZCAM_LEFT_A`, `SHERLOC_WATSON`): the rover's rig switches to it (a cut), the mast head slews to the photo's direction, Mastcam-Z zooms to the frame's focal length (read from its image ID) and a WATSON frame first deploys the arm; the photo lights up only once the rig has arrived, and the rover drives on only after the arm is stowed again. The mast pointing is the photo's world direction relative to the drawn rover, so it looks where NASA's camera looked although the replay's heading is not the real one. Curiosity's cameras were not checked: its photos keep the Navcam view. See *Rover cameras and arm* below. Illustrative: the rover moves at 2 m/s (real hardware is about 4.2 cm/s), the path between stops is a slope-constrained search on the map (a few long hops are straight lines) and the rover's time and energy are **not modelled** during the tour, so no resource alert shows |
| Rover cameras and arm (numbered keys `1`–`5` in the camera bar while following the rover, and in the first-person dock; *Arm close-up*; `src/lib/roverCameras.ts`, `src/lib/roverRig.ts`, `components/RoverCameraBar.tsx`) | The rover's view is drawn **from the camera node on the 3D model**, never from a free camera: Navcam (mast, 96° × 73°, fixed 19.2 mm, sharp 1.5 m–∞, stereo 42.4 cm), Mastcam-Z (mast, zoom 26–110 mm = 19.2° to 4.6° vertical, sharp 0.5 m–∞ up to about 50 mm and 1 m–∞ beyond, stereo 24.4 cm), front and rear Hazcam (body, 136° × 102° fisheye, sharp 0.8 m–∞, stereo 25 cm / 93.4 cm, fixed about 25° down; no distortion drawn) and WATSON (arm turret, sharp from 1.8 cm). Sources: Maki et al. 2020, [Space Science Reviews 216, 137](https://doi.org/10.1007/s11214-020-00765-9); Bell et al. 2021, [Space Science Reviews 217, 24](https://doi.org/10.1007/s11214-020-00755-x) and the [ASU Mastcam-Z tech specs](https://mastcamz.asu.edu/cameras/tech-specs); [WATSON, LPSC 52](https://ntrs.nasa.gov/citations/20220000131). WATSON's 35° × 27° field is derived from that abstract's example (about 17 × 13 cm from 27 cm), not published. **Movement follows the hardware**: the mast head pans 360° and tilts ±90°, at most 14°/s with a gentle acceleration (no slew rate is published: display assumption) and the head visibly turns on the model; only Mastcam-Z zooms (motor speed about 15 mm/s, assumption); Navcam and Hazcam have fixed lenses and the Hazcams cannot be aimed; changing camera eases to the other camera's view in about a third of a second (lens included) instead of jumping, and switching the eye of a stereo pair just slides the view across; the view is smoothed relative to the rover, so it never lags behind a driving rover. The photo tour plays at 5× (10× can still be chosen). **No shake**: the cameras are bolted to the rover, which drives at about 4 cm/s on Mars, so the camera sway is off for the rover and its view is stabilised (0.12 s low-pass). *Arm close-up* (rover standing still): the rover deploys its arm (6 s here; minutes on Mars), looks through WATSON at the ground ahead for 5 s, stows the arm and returns to the Navcam by itself; driving stows the arm. The deployed pose puts WATSON where a NASA feed frame reports it (2.45 m ahead, 0.77 m left, 0.16 m up), solved over the model's own joints; the stowed pose folds the arm across the front (display choice). At WATSON range the ground shows the 8 m terrain and 5 m/px imagery: no close-up detail exists in these data. Drag aims the mast, the wheel zooms Mastcam-Z, double-click returns the mast home |
| Drone camera window | The scene drawn again from the replayed drone pose; **not a camera feed**. Its Hazards tab reports steep cells and prior contradictions from the replay's **simulated** observations, not LiDAR |
| Lite 3D and 2D map tiers | Same replay with reduced 3D settings, or drawn in Canvas 2D without WebGL |

The 2 km demo and Daniel's validated public 128 m package are distinct scenes,
with different origins and height conventions. Their metrics and optional layers
must not be combined. The recorded entry preserves absolute datum/poses; camera
and OrbitControls fit those actual bounds without shifting the data.

## Requirements

Node 24 (`.nvmrc` pins 24.18.0; `package.json` engines `>=24 <25`).

## Commands

```bash
npm ci
npm run dev        # development server (vite)
npm run build      # tsc -b && vite build into dist/
npm run preview    # serve the production build
npm test           # vitest run
npm run fixture    # regenerate the replay fixture from scripts/data/ctx_crop.json (`WORLD=gale npm run fixture` for the Gale world)
npm run fixture    # regenerate the replay fixture from scripts/data/ctx_crop.json
```

The build uses relative paths, so `dist/` works from any subfolder (GitHub Pages) and
from a plain static server. Fonts are bundled; nothing loads from a CDN.

Regenerating the terrain crop needs the source GeoTIFF (not stored here):

```bash
node scripts/inspect-geotiff.mjs <ctx.tif>
node scripts/extract-ctx-crop.mjs <ctx.tif> 550 780   # centre pixel row, col
```

## Interface

Selectable list of agents, tasks and routes (left), status, contextual details and the agent HUD
(right column, stacked so nothing overlaps), replay timeline (bottom). Modes: Exploration, Ground
layers, Atmos and Mission replay. The 3D labels always stay under the panels, and when the camera pulls back a label that would cover another one waits until there is room (the selected agent first, then agents, base and goal, other sites, rover stops and route labels).

The **agent HUD** (bottom right) is a circle with six buttons on its rim: oxygen, energy, time,
route, atmosphere and radiation dose. With no option, or with Route, the circle is the minimap:
heading up (it turns with the selected agent, the N moves round the rim), 450 m around the agent,
with route, coverage, sites, other agents and a fading trail of where each agent was in the last 4 minutes
(the rover's drive shows behind it). Its elevation bands hold equal shares of the map and its shading adapts to the relief, so a flat area still shows its shape. Around the mission map it draws the 20 km surroundings of the same DTM in the same bands, dimmer, and a dashed line marks the map's edge, so near the edge the circle is not cut; a world without surroundings (Gale) shows a hatch outside the map. Each other option fills the circle with its own gauge,
and its button glows while active:

| Option | Gauge |
|---|---|
| Oxygen | Suit tank filled to the share left (astronaut only) |
| Energy | Battery cells charged to the share left |
| Time, radiation dose | Radial bar with the value; the dose bar is scaled to the whole run |
| Atmosphere | Estimated surface pressure map of the area, with the MEDA pressure and temperatures |

Tooltips give the use rate (from the two received samples around the replay time), how long it
lasts at that rate, and what the route in force needs and leaves (its `reserve_*` as published).
A button turns amber when the route leaves less than 15 % of the starting budget or is not verified.

The status block shows the **live clocks**: your local time and time zone, Mars Coordinated Time,
local mean solar time at Jezero (true solar time in the tooltip), the Perseverance sol and Ls,
computed with the NASA GISS Mars24 algorithm (Allison and McEwen 2000). They tick with your device
clock and are independent of the replay's simulated time.

The demo terrain is draped with the real CTX orthomosaic of Jezero from JPL Mars Trek (6 m source, 5 m image, same production as the DTM; regenerate with `node scripts/extract-ctx-ortho.mjs`). The panchromatic image is contrast-stretched and tinted for display only; it can be turned off in the view options and is not used on the uncertainty layer. Site marker masts hide when the camera is closer than 70 m so they do not cut through agents standing on a site.

The **Atmos** tab shows the latest Perseverance MEDA daily summaries at Jezero (temperature, pressure, sunrise and sunset), the annual cycle of Curiosity REMS at Gale crater as a reference (medians per 15° of solar longitude, another site, with the Jezero sols on top) and a surface radiation estimate for the run from the MSL RAD averages (Hassler et al. 2014), without suit or habitat shielding. The weather feeds are CAB outreach summaries, not the PDS archive; the replay has no Mars date, so none of it is presented as the conditions of the simulated run. Regenerate with `node scripts/extract-atmosphere.mjs`.

The status block shows `REPLAY` with the run's `source_mode` (`MOCK`, `SIMULATION` or `UNKNOWN`, ICD §6.1). A package that says `LIVE` or another value is refused; MOCK terrain metadata always shows `MOCK`; a package without the field shows `UNKNOWN`.

Agents and the base are drawn at true size by default (astronaut 1.9 m, rover 3.6 m with its arm, drone 1.2 m rotor span); the view option *True-size agents* can be turned off to enlarge agents with camera distance on the 2 km map. The base is `public/assets/models/base.glb`, the team's Blender base (`scripts/blender/source/base-marciana-v2.blend`) prepared by `scripts/blender/prepare_base.py` (own ground and rocks removed, dust film, sandbag berms, radiators, comms mast, power cables). It is placed whole at the median ground height under its footprint; a simple procedural cluster is drawn while it loads or if it fails.

The **Slope** layer uses Horn's 3×3 derivative on the orbital prior, never the
updated belief. The demo grid is 8 m (a 24 m computational window) and the recorded grid 4 m
(12 m), while their CTX source remains 20 m native. Resampling adds no source detail, and sub-grid hazards remain
unresolved. On the demo crop (before the synthetic scarp) the median is 2.9°, the 90th percentile
10.1° and the maximum 39.1°; cells lacking a complete valid window are grey.

The mission area is drawn as a solid block: plain rock-tone walls and a base that claim nothing about the subsurface (the Ground layers tab replaces them with the schematic strata). The view option *Surroundings (20 km)* shows the same CTX DTM around the area, box-averaged to 100 m (`scripts/extract-ctx-context.mjs`, from the same file, SHA-256 checked), draped with the CTX orthomosaic at 40 m (`scripts/extract-ctx-ortho.mjs public/replay/demo/context_ortho.png 500 20000 10`). It is context only and is never read by the planner or the mission.

The **Ground layers** tab drapes the USGS SIM 3464 geologic map (Sun and Stack, 2020) on the terrain and lists the units of the area with their share, description, composition (the map's mineral associations, such as Fe/Mg clay and carbonate in the fan) and interpretation. Selecting a unit highlights it. The geologic map can be turned off (the CTX image shows again), and a **cut-away block** shows the terrain as a cut piece of ground: each wall column starts with the unit mapped at the surface there and continues with older strata in the order given by the SIM 3464 unit interpretations (Aeb, NHjf2, Njf, Nue, older crust). Thicknesses, rock tones and the Nue/Njf order are schematic, as the panel states. Boundaries are approximate: the map has a 100–200 m registration offset against the CTX terrain. Regenerate with `node scripts/extract-geology.mjs`.

The rover and drone are the official NASA/JPL models with all branding removed, drawn at real size with the astronaut at 1.9 m. Their motion is display-only, derived from the drawn pose:

- **Rover**: turns about the middle of its six wheels; only the four corner wheels steer, each with its steering joint (actuator and fork); every wheel rolls at the ground speed, the outer ones faster in a turn, and rises or drops up to 15 cm to rest on the ground; the body tilts to the slope.
- **Drone**: rotors spin up (about 4 s) before it may leave the pad and spin down after landing; on or near the pad it neither moves sideways nor turns; take-off and landing are eased; in flight it keeps 8 m over the highest ground around it and climbs ahead of walls (a ramp up to 80 m ahead), so it never cuts through relief; landed, it rests on its four legs, tilted to the slope. A soft blur disc fades in with rotor speed, and near the ground the downwash lifts dust.

Up close (under about 200 m of camera distance) the ground gets procedural grain: grit, pebble speckle and metre-scale undulation (no ripples: their crests read as lines and alias into moiré) computed in the shader from the ground position. It is **cosmetic, not measured** (the data stops at 5–20 m), fades out at mission scale, is not drawn on the uncertainty layer or the geologic map, and can be turned off in the view options.

The terrain is drawn smoothed between the current run's cells, with contour
lines every 10 m (bold every 50 m) at true elevation. Smoothing does not improve
source resolution. Contours can be turned off in the view options.

Poses between received samples follow a monotone cubic (PCHIP) through the samples: no overshoot, continuous speed, no extrapolation past the last sample or across gaps. Agents are then drawn at an eased copy of that pose (about 0.1 s, display only). A jump in replay time (Restart, seek) places every agent at its new pose at once.

**Cameras** (bar under the agent list): Map, Astronaut, Rover, Drone and Base. The agent and base cameras are locked on their target (no lag), so the target stays steady on screen; following an agent selects it and sets the replay to 1× (turning it off restores the previous speed). In the Map camera **Grab map** is on by default: left drag slides the map, right drag or Shift + drag rotates, the wheel zooms; the ⟲ ⟳ buttons and `Q` / `E` turn the view 45°. The camera can zoom to about 0.3 m and is kept above the drawn terrain, with its near plane adapted to the zoom. **Camera smoothing** in the view options now sets only the orbit damping. In the follow view the route overlay is hidden.

**Opening and transitions.** The featured recorder entry omits the video intro.
The illustrative demo retains it (`?nointro=1` skips it). Terrain relief rises
visually over 1.4 s, zone by zone; map-version/layer changes morph heights over
1.8 s. These animations and the panel entrances are display only; reduced motion
skips them. Recorded heights, poses and mission time are not altered.

**Browsers without a GPU.** At start-up the viewer probes WebGL once (`src/lib/gpu.ts`). With a hardware GPU it renders in full. With a software rasteriser (SwiftShader, llvmpipe, Microsoft Basic Render) or a GPU the browser flags as slow, it keeps the 3D view in a lite tier: pixel ratio 1 (also in first person), no antialiasing, no surface detail and no surroundings. Without WebGL, or if the 3D view fails to start (`SceneBoundary.tsx`), a 2D top-down map of the same replay (`FlatMap.tsx`: terrain, routes, sites and agents, north up) replaces it while every panel and the timeline keep working; first person is off there. The zone selector then runs flat (the same card centred, with arrows, dots, keys and *Travel*, no globe), also when WebGL passes the probe but the globe's context cannot be created; the arrival photo simply fades. `?render=full`, `?render=lite` or `?render=2d` forces a tier.

**First person** (`V`, or the *3rd/1st person* button in the camera bar, while following an agent): the camera sits at the agent's eye (astronaut helmet at 1.62 m, rover mast at 2 m, drone camera under the body, pitched down) and looks along its heading; drag looks around, the wheel zooms (18°–110°), double-click recentres, and the frame is supersampled (1.5× the device pixels, capped at 3×). The agent's own model is hidden. The HUD (`src/components/FirstPersonHud.tsx`) shows:

- a compass tape with the bearing and straight-line distance to the base, the goal and revealed sites;
- the route in force, when it belongs to this agent, draped on the drawn ground (travelled part dimmed, the part ahead bright), with a beacon and the distance on the next waypoint (`PovRoute.tsx`, `src/lib/routeProgress.ts`);
- the same agent dial as in third person, same size, top right: its menu (resources, atmosphere, route...) and the heading-up map at its centre;
- a resource alert under the compass from the route sufficiency check (`src/lib/routeSufficiency.ts`, rationale and sources in [`docs/route_resource_sufficiency.md`](../docs/route_resource_sufficiency.md)): for each resource it compares what is left with what finishing the route in force needs (return included) and what walking back now along the travelled path needs, keeping the 20% reserve of JZ-P06. Amber *Route uses the reserve* (with the turn-back point), red *Turn back* when the route no longer fits, red *Return to base now* when even the walk-back uses the reserve; it pulses while critical and leaves when the margin recovers. Display only; the replay's plan is unchanged;
- one bottom dock: the drone camera window (left), every key control in one place (centre: `Q` terrain scan, `C` drone cam, `L` helmet lights, `I` artificial / real light, `B` sway, `V` third person, plus the mouse hints), so nothing overlaps;
- an optional camera sway (`B`): the astronaut's head bobs once per step, the drone drifts; a few centimetres at most, off by default with reduced motion, kept per browser. The rover has no sway (its cameras are rigidly mounted) and its dock shows its camera keys instead.

The HUD powers on when first person opens: the screen starts black while a short boot log prints in the centre, a bright line crosses it and two black shutters part from the centre to reveal the view, then the corner frame, the compass, the dial, the dock and the reticle come up in turn. Afterwards only quiet motion stays: the reticle breathes, a faint scan line passes every 7 s and a new scan readout slides in row by row. Contour lines are hidden in first person (they read as regular stripes on the ground) and the 20 km surroundings are always drawn, so the ground reaches the horizon wherever the eye looks. Display only; off with reduced motion.

**Drone camera** (`C`, first person only, while not looking through the drone itself): a window in the dock shows the scene a second time from the drone, looking ahead along its heading and 35° down, so the ground it is flying over is always visible (`src/components/DroneCam.tsx`). It is the replayed pose (`REPLAY · simulated pose`), not a live video feed; off by default in the lite render tier.

The drone window has two tabs. **Cam** is the view above. **Hazards** (`DroneMap.tsx`, `src/lib/droneHazards.ts`) is the drone's hazard report, north up and centred on it within 300 m, with 100 m rings and the flight trail. It draws only the cells the map version in force marks as observed: steep cells (hazard) in red, moderate (caution) in amber, cells whose updated height contradicts the orbital prior by more than twice its sigma outlined in red, clear cells as faint cyan dots; it also gives the nearest hazard (distance and bearing) and a status line of what the report caused in the replay. Slope bands are the viewer's display bands (`src/lib/scan.ts`, pending science approval). These observations are **simulated** in the replay; the drone carries no modelled LiDAR, and the window says so. This tab replaced the earlier survey-map tab.

**Helmet lights** (`L`, or *Lights* in the camera bar and the dock): EVA suits carry LED lamps on the helmet; the astronaut gets one cool-white spot light at helmet height aimed at the ground a few metres ahead (`src/components/HelmetLight.tsx`). Brightness and beam are display choices, not suit specifications.

**Sky, Sun and stars** (`src/components/SkyDome.tsx`, `src/lib/marsSky.ts`): the sky shows the real present time at the site, the same instant as the *Jezero LMST* clock. The Sun is placed with the Mars24 algorithm (solar declination from Ls, hour angle from local true solar time); the key light and the astronaut's shadow follow it (warmer and weaker when low) and blend at night to a dim overhead fill so the terrain stays readable (a display choice). The day sky is a dusty butterscotch with a blue glow around the Sun, strongest at sunrise and sunset; at night the 2887 naked-eye stars (V ≤ 5.5) of the Yale Bright Star Catalogue appear where they stand over the site, turned with the IAU 2009 rotation model of Mars. Planets and the moons are not drawn; no refraction or proper motion. `?skytime=2026-11-15T19:20:00Z` shows another instant. **Artificial light** is on by default (`I`, in the camera bar and the first-person dock): the terrain is lit as by day whatever the hour, from the viewer's fixed display direction, while the sky keeps the real time; it is a viewing aid, not sunlight. The same button then reads *Real light* and shows the terrain as it is at that hour (night included).

The ground grain (cosmetic, close views only) samples its noise octaves and its three pebble scales on rotated grids, so no rows or regular lines appear at grazing angles.

**Terrain scan** (`Q` in first person, or the *Terrain scan* key in the dock; `src/scanner/`, `TerrainScanner.tsx`): a visual pulse from the astronaut's position travels 50 m over the drawn relief at 25 m/s. The front lights the surface it passes, so it climbs ridges and drops into valleys; temporary 1 m contour lines and edges (curvature of the surface normal) appear in the swept area; symbols aligned with the surface show the run's orbital slope classes (cyan dot < 8°, yellow triangle 8–15°, red cross ≥ 15°, grey diamond NoData; display bands pending science approval, instanced, smaller farther out); footprints and the route in force light up; everything fades after 5 + 2 s and the key recharges for 3 s. One state machine (READY, SCANNING, COOLDOWN, DISABLED) drives the key, the shaders and optional synthesised sounds; holding the key does not repeat it. Display only: no new observation and no map, uncertainty or route change; the visual reach is not a sensor range. Inspired by the Odradek terrain scanner of *Death Stranding*; no assets from the game are used. Settings in `src/scanner/ScanConfig.ts`.

The astronaut always faces the direction it walks (display only): some recorded packages give the human a constant orientation, which drew it walking backwards on the return; the drawn yaw now follows its travel and is kept when it stops.

**Text access for language models.** `public/llms.txt` and `public/about.html` describe what the viewer shows, the controls, which data are real and which are simulated, the limits and the AI declaration; `index.html` carries page metadata, JSON-LD and a static summary that the app replaces on start. In the running page `window.mge.state()` returns the displayed replay state as JSON (`mge.viewer-state/1`: source, time, mission state, map version, agents with pose and resources, active route, recent events and view), always labelled REPLAY (`src/lib/stateSnapshot.ts`). `robots.txt` and `sitemap.xml` are included; on a project site crawlers only honour a `robots.txt` at the domain root.

The **replay** opens paused and restarts 4 s before the first recorded motion.
Short recordings start at 1×; the long demo starts at 10× (choices: 1×, 5×, 10×).

The walk clip is a lunar bounding gait. The viewer plants the lower foot at every keyframe, keeps the pelvis turn and weight shift the legs were animated with (the spine is counter-rotated so the torso stays upright) and re-times the cycle so the stance foot moves backward at constant speed. Played at the ground speed on screen divided by the clip's own walking speed, the planted foot slips about 5 mm per step at 1 m/s (it skated about 35 cm before), checked by a test on the real model; above about 2.5 m/s on screen the rhythm is capped and the feet slide. The astronaut casts a projected shadow along the scene's display sun (not a computed solar position) that walks with the skeleton, is not cut by terrain bumps or the route line, and never covers the model; footprints are boot soles, mirrored per foot.

Keys: `F` follow camera, `V` first person, `Q` terrain scan (first person; rotates the view otherwise), `C` drone camera (first person), `M` Mars now, the latest real Perseverance image (first person), `L` helmet lights, `I` artificial / real light, `B` camera sway (first person), `G` grab map, `Q` / `E` rotate the view, `Z` zone selector (map view), `1`–`5` rover camera (rover first person), `Space` play/pause, `←` `→` ±5 s, `Home` restart.
`?evaluator=1` shows the hidden reference layer, **in the dev server only** (R05). `npm run fixture`
writes the reference to the repository's Git-ignored `data/reference/<run_id>/`; the dev server
serves it to the evaluator view and the build never copies it, so `dist/` and GitHub Pages do not
contain it (checked by `tests/referenceIsolation.test.ts`). Without the file the evaluator view says
the reference is not available.

The **Run** selector under the title (or `?run=<id>`) opens another saved run:

The run selector offers the simulated `demo` and the five other zone scenes (`OFFERED_RUNS` in `src/data/replayAdapter.ts`: `demo` and every `*-demo`). The viewer does not use MOCK runs. Their packages remain in the repository for the team's tests and still load with `?run=<id>`, but only for review.

| Run | Source |
|---|---|
| `recorded-recovery-001` | Test package (not offered). Recorder output on the 128 m public Jezero crop; its `run_id` is kept independently of the folder name |
| `demo` (default) | Simulated mission on the real CTX crop (`public/replay/demo/`) |
| `mock-vertical-001` | Test package (not offered) from the gateway's `replay_recorder`, `../data/sample/replay/` (ICD §7) |

The recovery test package lives under `public/replay/recorded-recovery-001/`.
Historical gateway samples are read unchanged from `../data/sample/replay/<run_id>/`:
Vite serves them in development and copies them into `dist/replay/` on build.
`src/data/gatewayReplay.ts` validates `manifest.json`, `timeline.jsonl` and the
required final `snapshot.json` before converting to the existing viewer bundle. When the manifest names
it, reads the public raster attachment `files.public_rasters` (`mge-public-rasters-1.0.0`,
`../docs/REPLAY_CONTRACT.md`, JOR-03): the prior and, per map version, belief, sigma and observed
cells. The attachment is checked against the package (run, dataset, geometry, grid, cell values,
observed indices, every map version the states use) and refused with `PUBLIC_RASTERS_INVALID` on
any mismatch; no version falls back to another and an evaluator or reference key is refused.
Without an attachment only a package over a declared flat grid is drawn, as an explicitly
labelled illustration; any other package fails with `PUBLIC_RASTERS_REQUIRED`. The sample
`mock-vertical-001` predates the attachment, so it keeps that flat illustration, which shows no
latitude or longitude. The recovery package carries its recorded Jezero rasters.

## Architecture

| Path | Role |
|---|---|
| `src/types/` | TypeScript mirror of ICD-ROS2-V1 (draft) and the replay fixture layout |
| `src/data/replayAdapter.ts` | Loads and validates a saved run; lists the runs offered |
| `src/data/gatewayReplay.ts` | Reads a gateway replay package (ICD §7) into the same bundle |
| `src/lib/coords.ts` | ENU to Three.js conversion and grid sampling |
| `src/lib/replay.ts` | State at time t, event ordering, replans, monotone cubic pose interpolation, replay start point |
| `src/lib/management.ts` | List, details and alert data built only from received objects |
| `src/lib/astronautPose.ts` | Upright copies of the idle and walk clips (torso vertical, shoulders level, legs keep the pelvis motion, walk re-timed for planted feet); the model file is not modified |
| `src/lib/resources.ts`, `atmosMap.ts` | HUD resource use, time left and route figures; barometric pressure estimate for the atmosphere map |
| `src/lib/marsClock.ts` | Mars time from an Earth instant (Mars24): MSD, MTC, LMST/LTST, Ls, Perseverance sol |
| `src/lib/sun.ts`, `labels.ts` | Display sun shared by the light and the astronaut's shadow; z-index range keeping 3D labels under the panels |
| `src/lib/smoothing.ts` | Frame-rate independent easing for drawn agent poses and orbit damping settings |
| `src/lib/terrainSmooth.ts` | Bicubic display smoothing between source cells (adds no detail; cell centres stay exact) |
| `src/lib/slope.ts` | Terrain slope from an elevation grid (Horn 3x3), used by the Slope layer |
| `src/lib/atmos.ts`, `geology.ts`, `strata.ts`, `tacticalMap.ts`, `provenance.ts` | Atmos context, geologic units, schematic strata, minimap base image, REPLAY/source_mode display semantics |
| `src/data/referenceSources.ts` | Status of the mandatory NASA reference resources |
| `src/lib/scan.ts`, `droneHazards.ts`, `routeProgress.ts`, `routeSufficiency.ts`, `marsSky.ts`, `gpu.ts` | Terrain scan slope bands and bearings; drone hazard report from observed cells; route progress and sufficiency estimate; Mars sky and sun; WebGL tier probe |
| `src/scanner/`, `src/hooks/useTerrainScanner.ts` | Terrain scan state machine, controller, shaders, indicators and optional sounds |
| `src/lib/perseveranceRaw.ts`, `rawImagesStore.ts`, `components/RawImagesPanel.tsx`, `MarsNow.tsx` | Opt-in reader (links restricted to https mars.nasa.gov), one shared loader, the Atmos panel and the first-person *Mars now* window |
| `src/lib/siteKinds.ts`, `components/SiteIcon.tsx`, `SitesList.tsx` | One icon and colour per site kind, shared by the 3D markers, first-person compass, dial minimap, flat map and the Sites list |
| `src/lib/roverCameras.ts`, `roverRig.ts`, `components/RoverCameraBar.tsx` | The real Perseverance cameras (field of view, focal length, focus range, stereo baseline, model node), which camera and eye took a feed photo, and the rig that moves the mast head, the Mastcam-Z zoom and the arm within their limits; the dock's camera keys and arm close-up |
| `scripts/extract-dem-crop.mjs`, `scripts/extract-mer-traverse.mjs` | Crop of a whole NASA Trek DEM file (equirectangular metres or geographic degrees on the Mars 2000 sphere) to a scene's 8 m ENU grid; real Spirit and Opportunity stops from the PDS corrected traverses |
| `src/data/worlds.ts`, `components/ZoneSelector.tsx`, `src/lib/zoneGlobe.ts`, `src/lib/arrivalQuad.ts` | Zone catalogue (one Mars scene per place, with its centre, synopsis, NASA data and what it does not have) and the globe selector: point placement and aiming, title arcs, radial card geometry, card-to-scene transition (cover fit, quad-to-quad perspective warp onto the terrain footprint) |
| `src/lib/photoAim.ts` | Direction a real photo was taken towards (rover-frame vector or mast angles to a compass azimuth), its pointing relative to the drawn rover, and the third-person swing request |
| `src/lib/labelDeclutter.ts`, `projectedShadow.ts` | Hides floating labels that would overlap (priority order); the planar sun shadow shared by astronaut, rover and drone |
| `src/lib/format.ts`, `layers.ts` | Honest formatting ("Not estimated") and colour scales |
| `src/components/` | 3D scene (`MissionScene`, `TerrainView`, `ContextTerrain`, `CutawayBlock`, `RouteOverlay`, `SiteMarkers`, `AgentLayer`), astronaut, vehicle and base models (wheels, steering joints, rotors, `Downwash`, `FootDust`), cameras (`CameraBar`, `FollowCamera`, `FirstPersonCamera`, `ViewRotator`), first-person HUD (`FirstPersonHud`, `PovRoute`), agent dial (`RadialHud`, `HudGauge`, `Minimap`), drone window (`DroneCam` with its Hazards tab `DroneMap`), `TerrainScanner`, sky (`SkyDome`), panels (`DetailsPanel`, `ManagementList`, `LayerPanel`, `GeologyPanel`, `AtmosPanel`, `EventInspector`), `Timeline`, `LiveClocks`, `Intro`, `FlatMap` and `SceneBoundary` fallbacks |
| `scripts/` | Terrain crop, orthomosaic, context terrain, geology and atmosphere extraction, fixture generation, GLB branding strip, Blender base preparation |

## Data contract

Field names follow ICD-ROS2-V1 (draft, owned by the integrator). Frame `map` is ENU and
the viewer converts with `(x, y, z)_three = (x_east, z_up, -y_north)`. Local z equals the
MOLA areoid elevation minus the offset recorded in the manifest. Vertical exaggeration is
visual only and labelled. The viewer never plans routes.

ICD-ROS2-V1 types mirrored in `src/types/icd.ts`: `RunEnvelope`, `UnavailableResponse`, `Pose`, `AgentState`, `RouteDecision`, `MissionState`, `MissionEvent`, `TerrainMeta` (plus mode, route and task enums).

Replay fixture layout (`public/replay/<run_id>/`, demo run `demo-sim-002`, `mode: REPLAY`, `source_mode: SIMULATION`, `illustrative: true`): `manifest.json`, `timeline.json`, `routes.json`, `rasters.json`, `geology.json`, `atmosphere.json`, `ctx_ortho.png`, `context.json`, `context_ortho.png`. Gateway packages (`manifest.json` + `timeline.jsonl`) are read from `../data/sample/replay/<run_id>/`.

## Acceptance tests

Automated suite run on 2026-11-15 (`npm test`, branch `feat/challenge-gaps` after the per-zone water and radiation): 52 files passed (52); 314 tests passed, 1 skipped (315). `npm run build` passed.

| Test | Status |
|---|---|
| J-01 coordinates | Automated on the fixture's control points; the data owner's three points not received |
| J-02 replanning | Automated (data logic) and checked in the browser on 2026-11-14, on the demo and on the gateway replay (route r1 invalidated, r2 on map v2) |
| J-03 restrictions | Automated for the list, details and alert logic; not exercised in the UI with a non-feasible route |
| J-04 replay | Production build opened from a local preview without API or ROS; the build also bundles the gateway package from `../data/sample/replay` |
| J-05 accessibility | Panel layout measured free of overlaps at 1280×720, 1440×900 and 1920×1080; keyboard shortcuts listed above; no screen-reader audit |
| J-06 render | Not done |

## Third-party assets and attribution

"Animated Astronaut Character in Space Suit Loop" (https://skfb.ly/o9nHu) by LasquetiSpice is licensed under Creative Commons Attribution (http://creativecommons.org/licenses/by/4.0/).

Materials were converted to metallic-roughness. Terrain: NASA/USGS Mars 2020 TRN CTX DTM
mosaic. Fonts: Rajdhani, Barlow Condensed, IBM Plex Mono (SIL OFL 1.1). Details in
`../THIRD_PARTY_NOTICES.md`.

## AI use

The code, scripts, tests and the simulated fixture were written with AI assistance. See
`../docs/AI_USAGE.md` (section "Web mission viewer") and `../docs/ai_usage.json`.

## Known gaps

Terrain detail is limited by the 20 m source: close-ups look smooth. The 1 m HiRISE DTM covers this area and could provide real detail, but it is the hidden evaluator reference and must not reveal unknown terrain in the normal view.

The viewer's selector offers only the simulated zone scenes (`demo` and the `*-demo` zones); no recorded MOCK package is offered there.
The recorded entry consumes real planner output and the public terrain package
through the recorder, with strict snapshot/raster validation. A live gateway,
scientific model agreement and a completed three-role mission remain separate
acceptances. An automated private-browser replay check with every
backend off is recorded in `../evidence/web-private-replay-20261115/`; AC-08 is
not claimed as accepted (headless run, one machine, MOCK recorded package). Percentages are
relative to the first received sample, not to a certified budget.
The vehicle, drone and astronaut motion was checked in the dev server on one machine, mostly from
still frames; the rover over steep relief and the drone climbing over a wall were not watched live.

Astronaut posture (vertical torso, level shoulders) and planted-foot slip are covered by tests on
the real model and were checked by eye in the follow view, but only in the dev server on one machine. No browser automation tests. Of the candidate NASA layers in
`../docs/data_sources.md`, the Mars Trek CTX orthomosaic and USGS SIM 3464 geology are
shown; Perseverance raw images load on request in the Atmos tab. The tactical map tab was removed (a minimap
remains in the agent HUD). The terrain scan is a display effect only (`src/scanner/`).
