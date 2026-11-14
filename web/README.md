# Mars Gods Eye — web viewer

Owner: Jorge. Integration: Jesús. Scientific review: David.

3D mission viewer: terrain layers, routes, agents and mission events on real Mars
terrain, with a saved-run replay that needs no ROS, Gazebo or network.

## Status

Early P0 increment, **REPLAY mode only**. The live link is shown as offline because the
API gateway does not exist yet.

| Part | What it is |
|---|---|
| Terrain | **Real**: a provisional 2 km crop of the NASA/USGS Mars 2020 TRN CTX DTM (20 m, Jezero), resampled to a local ENU grid |
| Mission, agents, routes, events | **Simulated** (`scripts/make-demo-fixture.mjs`); routes come from a slope-constrained search inside the generator, not from the planner |
| Adverse case | **Synthetic**: a scarp added to the hidden evaluator reference; it is not in the CTX data |
| POIs C and D | Fictitious |
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

The terrain is drawn smoothed between the 20 m cells, with contour lines every 10 m (bold every 50 m) at true elevation. Contours can be turned off in the view options.

Keys: `F` follow camera, `Space` play/pause, `←` `→` ±5 s, `Home` restart.
`?evaluator=1` shows the hidden reference layer; it is off by default.

## Architecture

| Path | Role |
|---|---|
| `src/types/` | TypeScript mirror of ICD-ROS2-V1 (draft) and the replay fixture layout |
| `src/data/replayAdapter.ts` | Loads and validates a saved run |
| `src/lib/coords.ts` | ENU to Three.js conversion and grid sampling |
| `src/lib/replay.ts` | State at time t, event ordering, replans, visual pose interpolation |
| `src/lib/management.ts` | List, details and alert data built only from received objects |
| `src/lib/astronautPose.ts` | Upright copies of the idle and walk clips (torso vertical, no pelvis or shoulder tilt, reduced bounce); the model file is not modified |
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
| J-02 replanning | Automated (data logic) and checked in the browser on 2026-11-14 |
| J-03 restrictions | Automated for the list, details and alert logic; not exercised in the UI with a non-feasible route |
| J-04 replay | Production build opened from a local preview without API or ROS |
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

No gateway, planner routes, mission profiles or processed terrain package from the other
workstreams yet. Percentages are relative to the first received sample, not to a
certified budget. Astronaut posture is covered by tests on the real model, but the walk in a live window at full frame rate has not been reviewed by eye. No
browser automation tests. Tactical map, scanner and weather are not started.
