# Mission viewer scaffold

Owner: Jorge. Integration: Jesús. Scientific review: David.

This is the React + TypeScript + Vite + Three.js foundation for requirements R04,
R05, R09 and R13–R18. It opens without ROS or Gazebo and displays an empty coordinate
grid, not Mars terrain or mission results. It does not perform route planning.

Use Node **24.18.0** (`.nvmrc`) and the checked-in lockfile:

```sh
cd web
npm ci
npm test
npm run build
npm run preview
```

`npm run dev` starts local development. The production build uses relative asset
paths for a GitHub Pages subdirectory; serve `dist/` over HTTP. Opening `index.html`
with `file://` is not a supported module-loading workflow. No CDN or remote asset
is needed to serve the build locally after installation.

## R–F–L–P and contracts

| Layer | Contract |
|---|---|
| R | Explain mission decisions, distinguish prior/belief and old/current routes, support replay |
| F | Render terrain, agents, routes, causal events and recorded runs |
| L | TerrainView; pending RouteOverlay, AgentLayer, Timeline, EventInspector, MissionHUD, ReplayAdapter |
| P | `src/`, with frame conversion and the proposed ICD-WEB-V1 envelope |
| V&V | Frame/version tests; typecheck/build. Integrated browser/replay evidence remains pending |

ROS map ENU metres map to Three.js `(x, z, -y)` without height exaggeration. Inputs
must come from Daniel's terrain metadata and Jesús's versioned JSON gateway or
local replay files. Never expose the evaluator's hidden reference through normal
map layers. A stale route must not be displayed as current.

The proposed gateway supplies `/api/manifest`, `/api/run/{run_id}/snapshot`,
`/api/mission/goal` and `/api/events` (WebSocket). `mode: null` means no active run;
only a real loaded run may display LIVE or REPLAY. The current scaffold makes no
API requests and has no mission/replay controls to imply unfinished functionality.

## Next integration tasks

1. Agree the JSON schema with Jesús and load Daniel's three ENU control points.
2. Add prior/belief/sigma and a route supplied by Diego, with version and reason.
3. Consume a reproducible simulated replay with before/observation/after states.
4. Add causal timeline, agent states, unavailable/error states and resource HUD.
5. Add browser evidence for J-01–J-06 and the English competition demo.

No bitmap, audio, video or NASA branding is included. Mandatory AI-use disclosure
for scaffold code is maintained by the repository's disclosure documentation and
metadata; preserve that disclosure when integrating this module.
