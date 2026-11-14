# Blender scripts for the viewer's 3D models

Run with Blender 5.2 in background mode from `web/`.

## Surface base

Source: the team's `source/base-marciana-v2.blend` (AI-generated with OpenAI Codex by the owner, 14 November 2026,
SHA-256 `1599ec1bea327ead66e000a667e3791aa004c91502ab0bf1664febad93f646ee`): hub, three
habitat modules, corridors, hangar, geodesic dome and solar field, untextured, without agency
logos, flags or mission marks. `prepare_base.py` turns it into `public/assets/models/base.glb`:

- removes its own ground and rocks (the viewer draws the real CTX terrain);
- realism pass: matte cladding, a dust film fading from the ground up to 1.6 m (vertex
  colours), regolith sandbag berms against the module block (radiation shielding), two
  thermal radiators, a comms mast with a dish and guy lines, and power cables from the solar
  field to the hub. The solar panels are checked to face the equator (south at 18° N);
- exports GLB with +Y up and the origin on the ground at the hub centre.

`tests/baseModel.test.ts` checks that no ground or rocks remain, the model sits on y = 0 at
real scale, carries no textures and stays under 60k triangles.

```sh
blender -b scripts/blender/source/base-marciana-v2.blend --python scripts/blender/prepare_base.py -- public/assets/models/base.glb [preview.png]
```

## Rover and drone (official NASA/JPL models, branding removed)

Sources (credit NASA/JPL-Caltech), downloaded 14 November 2026:

| Output | Source | SHA-256 of the download |
|---|---|---|
| `public/assets/models/rover.glb` | [Mars Perseverance Rover, 3D Model](https://science.nasa.gov/resource/mars-perseverance-rover-3d-model/), `25042_Perseverance.glb` (11.15 MB) | `484f00aa5d3739b127b6d413e77149a2d74ae87b76ae57463c4b91965ffb4990` |
| `public/assets/models/drone.glb` | [Mars Ingenuity Helicopter, 3D Model](https://science.nasa.gov/resource/mars-ingenuity-helicopter-3d-model/), `25043_Ingenuity_v3.glb` (1.73 MB) | `d9ebff90d0475d0be0f9dc241e69bb1700d86c702a1f289578c35f4fefc9f19f` |

The NASA Space Apps rules and AGENTS.md section 11 do not allow NASA branding in the
delivery, so every agency mark on the textures was painted out with the plain surrounding
surface before use; nothing of the marks is kept:

- Rover: `arm_graphics` (mission emblem, rover name, agency logos plate), `nameplate`
  (mission plaque), `cvoidPlaque` (commemorative plaque), `mars_2020_03` (perforated agency
  names on a panel), `mars_2020_04` (plaque copy), `mars_2020_01` (calibration target with
  commemorative motto).
- Drone: `blade` (agency plate, national flag, agency logo), `cameras_diff` (camera brand
  labels).

Then `clean_nasa_model.py` swaps in the cleaned textures, decimates the rover to about 35 %
(199k to 84k triangles), limits textures to 512 px and turns the rover to face +X:

```sh
blender -b --factory-startup --python scripts/blender/clean_nasa_model.py -- perseverance.glb <clean_tex>/perseverance public/assets/models/rover.glb 0.35 512 90
blender -b --factory-startup --python scripts/blender/clean_nasa_model.py -- ingenuity.glb <clean_tex>/ingenuity public/assets/models/drone.glb 1.0 512 0
```

### Second pass: marks the Blender cleanup missed

Two textures kept agency marks after the Blender export:

- the rover's `blade` (the helicopter stowed under the rover), which still showed the
  agency plate, the national flag and the agency logo;
- the drone's `chopper_sp_r2` (blade roughness map), which still showed two agency logos.

`../strip-glb-branding.mjs` removes them without Blender and without synthesising any
image. It copies the drone's already cleaned `blade` sheet (same 512 × 256 layout) into the
rover, and fills pixels x 440–511, y 172–255 of the roughness map with its plain
background RGB (166, 161, 157). Every other buffer view stays byte-identical, and a second run changes
nothing. Run it from `web/` after re-exporting:

```sh
node scripts/strip-glb-branding.mjs
```

| File | SHA-256 after cleanup |
|---|---|
| `public/assets/models/rover.glb` | `9588ad8239fc025bd5a210380fa84c2f61a5f343d4529ab4edd238fde8c0fcbc` |
| `public/assets/models/drone.glb` | `48a4720a2f3ae234d86d7eb85defb2311e5e21a678588d04058b766ec574e219` |

`tests/modelBranding.test.ts` fails if any of these regions shows marks again.

The geometry and remaining textures are NASA/JPL-Caltech's and are not AI-generated; the
cleanup and preparation scripts were written with AI assistance (see `docs/AI_USAGE.md`).

`common.py` holds helpers for procedural models (base habitat, in progress).
