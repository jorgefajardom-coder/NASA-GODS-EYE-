# Mars Gods Eye — web viewer

Owner: Jorge. Integration: Jesús. Scientific review: David.

3D mission viewer: terrain layers, routes, agents and mission events on real Mars
terrain, with a saved-run replay that needs no ROS, Gazebo or network.

## Status

Early P0 increment, **REPLAY mode only**. The live link is shown as offline: the gateway
on `feat/integration` is not connected to the viewer yet. Two saved runs can be opened
(see the Run selector below).

| Part | What it is |
|---|---|
| Terrain | **Real**: a provisional 2 km crop of the NASA/USGS Mars 2020 TRN CTX DTM (20 m, Jezero), resampled to a local ENU grid |
| Mission, agents, routes, events | **Simulated** (`scripts/make-demo-fixture.mjs`); routes come from a slope-constrained search inside the generator, not from the planner |
| Adverse case | **Synthetic**: a scarp added to the hidden evaluator reference; it is not in the CTX data |
| POIs C and D | Fictitious |
| Gateway replay `mock-vertical-001` | **Recorded MOCK run** from Jesús's `replay_recorder`: flat synthetic grid, straight-line MOCK planner, no Mars data |
| Uncertainty, budgets, consumption | Illustrative assumptions, not certified limits |

The terrain crop is provisional: the data owner's processed package replaces it.

## Requirements

Node 24 (`.nvmrc`).

## Commands

```bash
npm ci
npm run dev        # development server
npm run build      # type-check + production build into dist/
npm run preview    # serve the production build
npm test           # unit and contract tests (Vitest)
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

Selectable list of agents, tasks and routes (left), contextual details (right), telemetry
and route status (bottom left), replay timeline (bottom). Modes: Exploration and Mission
replay; Tactical map and Atmos are disabled until they exist.

The demo terrain is draped with the real CTX orthomosaic of Jezero from JPL Mars Trek (6 m source, 5 m image, same production as the DTM; regenerate with `node scripts/extract-ctx-ortho.mjs`). The panchromatic image is contrast-stretched and tinted for display only; it can be turned off in the view options and is not used on the uncertainty layer. Site marker masts hide when the camera is closer than 70 m so they do not cut through agents standing on a site.

The terrain is drawn smoothed between the 20 m cells, with contour lines every 10 m (bold every 50 m) at true elevation. Contours can be turned off in the view options.

Agents are drawn at an eased copy of their pose (about 0.1 s, display only) so they do not tremble when the camera is close; the follow camera reads that drawn pose in the same frame. **Camera smoothing** in the view options sets the follow and orbit easing: Off (rigid), Soft (default) or Cinematic; the choice is remembered in this browser.

Keys: `F` follow camera, `Space` play/pause, `←` `→` ±5 s, `Home` restart.
`?evaluator=1` shows the hidden reference layer; it is off by default.

The **Run** selector under the title (or `?run=<id>`) opens another saved run:

| Run | Source |
|---|---|
| `demo` | Simulated mission on the real CTX crop (`public/replay/demo/`) |
| `mock-vertical-001` | Package recorded by the gateway's `replay_recorder` from the MOCK vertical (Jesús, `../data/sample/replay/`, ICD §7). Flat synthetic grid, straight-line MOCK planner, 5.4 s of wall-clock time |

Gateway packages are read unchanged from `../data/sample/replay/<run_id>/`: Vite serves them
in development and copies them into `dist/replay/` on build. `src/data/gatewayReplay.ts`
converts `manifest.json` + `timeline.jsonl` into the viewer's bundle. The package has no
rasters yet, so only a declared flat grid can be shown; sigma and the evaluator reference
are NoData, and a MOCK grid shows no latitude or longitude.

## Architecture

| Path | Role |
|---|---|
| `src/types/` | TypeScript mirror of ICD-ROS2-V1 (draft) and the replay fixture layout |
| `src/data/replayAdapter.ts` | Loads and validates a saved run; lists the runs offered |
| `src/data/gatewayReplay.ts` | Reads a gateway replay package (ICD §7) into the same bundle |
| `src/lib/coords.ts` | ENU to Three.js conversion and grid sampling |
| `src/lib/replay.ts` | State at time t, event ordering, replans, visual pose interpolation |
| `src/lib/management.ts` | List, details and alert data built only from received objects |
| `src/lib/astronautPose.ts` | Upright copies of the idle and walk clips (torso vertical, shoulders and pelvis level, reduced bounce); the model file is not modified |
| `src/lib/smoothing.ts` | Frame-rate independent easing for drawn agent poses and the camera |
| `src/lib/terrainSmooth.ts` | Bicubic display smoothing between source cells (adds no detail; cell centres stay exact) |
| `src/lib/format.ts`, `layers.ts` | Honest formatting ("Not estimated") and colour scales |
| `src/components/` | Terrain, routes, agents, sites, astronaut model, follow camera, interface panels |
| `scripts/` | Terrain crop extraction and fixture generation |

## Data contract

Field names follow ICD-ROS2-V1 (draft, owned by the integrator). Frame `map` is ENU and
the viewer converts with `(x, y, z)_three = (x_east, z_up, -y_north)`. Local z equals the
MOLA areoid elevation minus the offset recorded in the manifest. Vertical exaggeration is
visual only and labelled. The viewer never plans routes.

## Acceptance tests

| Test | Status |
|---|---|
| J-01 coordinates | Automated on the fixture's control points; the data owner's three points not received |
| J-02 replanning | Automated (data logic) and checked in the browser on 2026-11-14, on the demo and on the gateway replay (route r1 invalidated, r2 on map v2) |
| J-03 restrictions | Automated for the list, details and alert logic; not exercised in the UI with a non-feasible route |
| J-04 replay | Production build opened from a local preview without API or ROS; the build also bundles the gateway package from `../data/sample/replay` |
| J-05 accessibility | Checked at 1366×768 only |
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
from the planner now on `main`, mission profiles and the processed terrain package. Gateway
packages carry no rasters yet, so a recorded run can only show a declared flat grid.
Percentages are relative to the first received sample, not to a certified budget.

Astronaut posture (vertical torso, level shoulders and pelvis) is covered by tests on the
real model and was checked by eye in the follow view at 20×, but only in the dev server on
one machine. No browser automation tests. Candidate NASA layers found in the reference
review (Mars Trek CTX orthomosaic, USGS SIM 3464 geology, Perseverance raw images) are
documented in `../docs/data_sources.md` and not yet shown. Tactical map, scanner and
weather are not started.
