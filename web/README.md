# Mars Gods Eye — web viewer

Owner: Jorge. Integration: Jesús. Scientific review: David.

3D mission viewer: terrain layers, routes, agents and mission events on real Mars
terrain, with a saved-run replay that needs no ROS, Gazebo or network.

## Status

**REPLAY mode only**. The live link is shown as offline: the gateway
on `feat/integration` is not connected to the viewer yet. Two saved runs can be opened
(see the Run selector below).

| Part | What it is |
|---|---|
| Terrain | **Real**: a provisional 2 km crop of the NASA/USGS Mars 2020 TRN CTX DTM (20 m, Jezero), resampled to a local ENU grid |
| Mission, agents, routes, events | **Simulated** (`scripts/make-demo-fixture.mjs`); routes come from a slope-constrained search inside the generator, not from the planner. The rover (1 m/s) stops and pivots at 6°/s at corners and the U-turn; the drone (4 m/s, 40 m) spins up, climbs and descends vertically. The speeds are simulated, the rover's far faster than real hardware |
| Adverse case | **Synthetic**: a scarp added to the hidden evaluator reference; it is not in the CTX data |
| POIs C and D | Fictitious |
| Gateway replay `mock-vertical-001` | **Recorded MOCK run** from Jesús's `replay_recorder`: flat synthetic grid, straight-line MOCK planner, no Mars data |
| Uncertainty, budgets, consumption | Illustrative assumptions, not certified limits |
| Atmos tab, HUD atmosphere and dose | NASA weather summaries and published radiation averages (other sites/periods); not the conditions of the simulated run. The HUD pressure map is a barometric **estimate** from one MEDA value, not a measured field |
| Earth and Mars clocks | Your device clock; Mars time from the NASA GISS Mars24 algorithm (real present time, not the replay's) |
| Shadows, footprints, dust, rotor blur, wheel and joint motion | **Cosmetic display** derived from the drawn poses; they never change a position in the data |
| Rover, drone, base models | NASA/JPL models with branding removed; the base is the team's own Blender model |
| Astronaut portrait | **AI-generated** (ChatGPT), shown beside human_1 in the details panel with a burned-in `AI-generated` watermark |
| Slope layer | Derived from the orbital CTX DTM (Horn 3x3, about 60 m window); a lower bound for local slope, not a hazard map |
| Surroundings (option, off by default) | Same CTX DTM over 20 km (100 m box average, `scripts/extract-ctx-context.mjs`) and CTX orthomosaic at 40 m; context only |

The terrain crop is provisional: the data owner's processed package replaces it.

## Requirements

Node 24 (`.nvmrc` pins 24.18.0; `package.json` engines `>=24 <25`).

## Commands

```bash
npm ci
npm run dev        # development server (vite)
npm run build      # tsc -b && vite build into dist/
npm run preview    # serve the production build
npm test           # vitest run
npm run typecheck  # tsc -b --noEmit
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
layers, Atmos and Mission replay. The 3D labels always stay under the panels.

The **agent HUD** (bottom right) is a circle with six buttons on its rim: oxygen, energy, time,
route, atmosphere and radiation dose. With no option, or with Route, the circle is the minimap:
heading up (it turns with the selected agent, the N moves round the rim), 450 m around the agent,
with route, coverage, sites and other agents. Each other option fills the circle with its own gauge,
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

The **Slope** layer is computed in the viewer from the orbital CTX DTM with Horn's 3×3 method (the method of `gdaldem slope`) on the 20 m grid, never from the updated map. Each value averages about 60 m of ground, so it is a lower bound for local slope, not a hazard map. On the demo crop the median is 4.8°, the 90th percentile 13.9° and the maximum 34.2°; border cells without a full 3×3 window are grey.

The mission area is drawn as a solid block: plain rock-tone walls and a base that claim nothing about the subsurface (the Ground layers tab replaces them with the schematic strata). The view option *Surroundings (20 km)* shows the same CTX DTM around the area, box-averaged to 100 m (`scripts/extract-ctx-context.mjs`, from the same file, SHA-256 checked), draped with the CTX orthomosaic at 40 m (`scripts/extract-ctx-ortho.mjs public/replay/demo/context_ortho.png 500 20000 10`). It is context only and is never read by the planner or the mission.

The **Ground layers** tab drapes the USGS SIM 3464 geologic map (Sun and Stack, 2020) on the terrain and lists the units of the area with their share, description, composition (the map's mineral associations, such as Fe/Mg clay and carbonate in the fan) and interpretation. Selecting a unit highlights it. The geologic map can be turned off (the CTX image shows again), and a **cut-away block** shows the terrain as a cut piece of ground: each wall column starts with the unit mapped at the surface there and continues with older strata in the order given by the SIM 3464 unit interpretations (Aeb, NHjf2, Njf, Nue, older crust). Thicknesses, rock tones and the Nue/Njf order are schematic, as the panel states. Boundaries are approximate: the map has a 100–200 m registration offset against the CTX terrain. Regenerate with `node scripts/extract-geology.mjs`.

The rover and drone are the official NASA/JPL models with all branding removed, drawn at real size with the astronaut at 1.9 m. Their motion is display-only, derived from the drawn pose:

- **Rover**: turns about the middle of its six wheels; only the four corner wheels steer, each with its steering joint (actuator and fork); every wheel rolls at the ground speed, the outer ones faster in a turn, and rises or drops up to 15 cm to rest on the ground; the body tilts to the slope.
- **Drone**: rotors spin up (about 4 s) before it may leave the pad and spin down after landing; on or near the pad it neither moves sideways nor turns; take-off and landing are eased; in flight it keeps 8 m over the highest ground around it and climbs ahead of walls (a ramp up to 80 m ahead), so it never cuts through relief; landed, it rests on its four legs, tilted to the slope. A soft blur disc fades in with rotor speed, and near the ground the downwash lifts dust.

Up close (under about 200 m of camera distance) the ground gets procedural grain: grit, pebble speckle and metre-scale undulation (no ripples: their crests read as lines and alias into moiré) computed in the shader from the ground position. It is **cosmetic, not measured** (the data stops at 5–20 m), fades out at mission scale, is not drawn on the uncertainty layer or the geologic map, and can be turned off in the view options.

The terrain is drawn smoothed between the 20 m cells, with contour lines every 10 m (bold every 50 m) at true elevation. Contours can be turned off in the view options.

Poses between received samples follow a monotone cubic (PCHIP) through the samples: no overshoot, continuous speed, no extrapolation past the last sample or across gaps. Agents are then drawn at an eased copy of that pose (about 0.1 s, display only). A jump in replay time (Restart, seek) places every agent at its new pose at once.

**Cameras** (bar under the agent list): Map, Astronaut, Rover, Drone and Base. The agent and base cameras are locked on their target (no lag), so the target stays steady on screen; following an agent selects it and sets the replay to 1× (turning it off restores the previous speed). In the Map camera **Grab map** is on by default: left drag slides the map, right drag or Shift + drag rotates, the wheel zooms; the ⟲ ⟳ buttons and `Q` / `E` turn the view 45°. The camera can zoom to about 0.3 m and is kept above the drawn terrain, with its near plane adapted to the zoom. **Camera smoothing** in the view options now sets only the orbit damping. In the follow view the route overlay is hidden.

The **replay** opens and restarts 4 s before the first agent moves (the demo's agents are idle for 10 s), at 10×, the highest speed offered (1×, 5×, 10×).

The walk clip is a lunar bounding gait. The viewer plants the lower foot at every keyframe, keeps the pelvis turn and weight shift the legs were animated with (the spine is counter-rotated so the torso stays upright) and re-times the cycle so the stance foot moves backward at constant speed. Played at the ground speed on screen divided by the clip's own walking speed, the planted foot slips about 5 mm per step at 1 m/s (it skated about 35 cm before), checked by a test on the real model; above about 2.5 m/s on screen the rhythm is capped and the feet slide. The astronaut casts a projected shadow along the scene's display sun (not a computed solar position) that walks with the skeleton, is not cut by terrain bumps or the route line, and never covers the model; footprints are boot soles, mirrored per foot.

Keys: `F` follow camera, `G` grab map, `Q` / `E` rotate the view, `Space` play/pause, `←` `→` ±5 s, `Home` restart.
`?evaluator=1` shows the hidden reference layer, **in the dev server only** (R05). `npm run fixture`
writes the reference to the repository's Git-ignored `data/reference/<run_id>/`; the dev server
serves it to the evaluator view and the build never copies it, so `dist/` and GitHub Pages do not
contain it (checked by `tests/referenceIsolation.test.ts`). Without the file the evaluator view says
the reference is not available.

The **Run** selector under the title (or `?run=<id>`) opens another saved run:

| Run | Source |
|---|---|
| `demo` | Simulated mission on the real CTX crop (`public/replay/demo/`) |
| `mock-vertical-001` | Package recorded by the gateway's `replay_recorder` from the MOCK vertical (Jesús, `../data/sample/replay/`, ICD §7). Flat synthetic grid, straight-line MOCK planner, 5.4 s of wall-clock time |

Gateway packages are read unchanged from `../data/sample/replay/<run_id>/`: Vite serves them
in development and copies them into `dist/replay/` on build. `src/data/gatewayReplay.ts`
converts `manifest.json` + `timeline.jsonl` into the viewer's bundle and, when the manifest names
it, reads the public raster attachment `files.public_rasters` (`mge-public-rasters-1.0.0`,
`../docs/REPLAY_CONTRACT.md`, JOR-03): the prior and, per map version, belief, sigma and observed
cells. The attachment is checked against the package (run, dataset, geometry, grid, cell values,
observed indices, every map version the states use) and refused with `PUBLIC_RASTERS_INVALID` on
any mismatch; no version falls back to another and an evaluator or reference key is refused.
Without an attachment only a MOCK package over a declared flat grid is drawn, as an explicitly
labelled illustration; any other package fails with `PUBLIC_RASTERS_REQUIRED`. The bundled sample
predates the attachment, so it shows the flat MOCK grid; a MOCK grid shows no latitude or longitude.

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
| `src/lib/format.ts`, `layers.ts` | Honest formatting ("Not estimated") and colour scales |
| `src/components/` | Terrain, routes, agents, sites, astronaut and vehicle models (wheels, steering joints, rotors, downwash), cameras (`CameraBar`, `FollowCamera`, `ViewRotator`), agent HUD (`RadialHud`, `HudGauge`), live clocks, interface panels |
| `scripts/` | Terrain crop, orthomosaic, context terrain, geology and atmosphere extraction, fixture generation, GLB branding strip, Blender base preparation |

## Data contract

Field names follow ICD-ROS2-V1 (draft, owned by the integrator). Frame `map` is ENU and
the viewer converts with `(x, y, z)_three = (x_east, z_up, -y_north)`. Local z equals the
MOLA areoid elevation minus the offset recorded in the manifest. Vertical exaggeration is
visual only and labelled. The viewer never plans routes.

ICD-ROS2-V1 types mirrored in `src/types/icd.ts`: `RunEnvelope`, `UnavailableResponse`, `Pose`, `AgentState`, `RouteDecision`, `MissionState`, `MissionEvent`, `TerrainMeta` (plus mode, route and task enums).

Replay fixture layout (`public/replay/<run_id>/`, demo run `demo-sim-002`, `mode: REPLAY`, `source_mode: SIMULATION`, `illustrative: true`): `manifest.json`, `timeline.json`, `routes.json`, `rasters.json`, `geology.json`, `atmosphere.json`, `ctx_ortho.png`, `context.json`, `context_ortho.png`. Gateway packages (`manifest.json` + `timeline.jsonl`) are read from `../data/sample/replay/<run_id>/`.

## Acceptance tests

Automated suite on 2026-11-14: 22 files, 123 tests passed (`npm test`); `npm run build` passes.

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

Not consumed yet from the other workstreams: the live gateway (`feat/integration`), routes
from the planner now on `main`, mission profiles and the processed terrain package. The viewer
reads the public raster attachment, but no bundled package carries one yet, so a recorded run
still shows the declared flat MOCK grid; AC-08 (private-browser replay with every backend off)
is not recorded yet. Percentages are relative to the first received sample, not to a certified budget.
The vehicle, drone and astronaut motion was checked in the dev server on one machine, mostly from
still frames; the rover over steep relief and the drone climbing over a wall were not watched live.

Astronaut posture (vertical torso, level shoulders) and planted-foot slip are covered by tests on
the real model and were checked by eye in the follow view, but only in the dev server on one machine. No browser automation tests. Of the candidate NASA layers in
`../docs/data_sources.md`, the Mars Trek CTX orthomosaic and USGS SIM 3464 geology are
shown; Perseverance raw images are not yet. The tactical map tab was removed (a minimap
remains in the agent HUD); scanner not started.
