"""Build the Gazebo world of a sensing run: public jezero_mvp terrain + its SIMULATED scene.

Run from a built, sourced workspace root:
  python3 scripts/live_scenarios/gazebo_world.py <scene.json> <agents.yaml> <out_dir>
Then: gz sim -r <out_dir>/world.sdf   and   ros2 run mge_sim gz_mirror --ros-args
  -p run_id:=<run_id> -p world_json:=<out_dir>/world.json
"""
import json
from pathlib import Path
import sys

import numpy as np
import yaml

from mge_data.core import default_manifest_path, load_public_terrain
from mge_sim.gz_world import build_world

scene_file, agents_file, out_dir = sys.argv[1:4]
physical = tuple(a for a in (sys.argv[4] if len(sys.argv) > 4 else '').split(',') if a)
tile = load_public_terrain(default_manifest_path())
aux = np.load(Path(default_manifest_path()).parent / 'jezero_aux_layers.npz')
rows, cols = tile.prior.shape
m = tile.metadata
grid = (m.origin_x_m, m.origin_y_m, m.resolution_m, rows, cols)
heights = np.where(tile.nodata_mask, np.nan, tile.prior)
scene = json.loads(Path(scene_file).read_text())
if scene.get('source_kind') != 'SIMULATED' or (scene['rows'], scene['cols']) != (rows, cols):
    raise SystemExit('the scene must be a SIMULATED scene of this grid')
kinds = {'HUMAN', 'ROVER', 'DRONE'}
agents = [(a['id'], a['kind'], a['x_m'], a['y_m'], a.get('z_m', float(np.nanmin(heights))))
          for a in yaml.safe_load(Path(agents_file).read_text())['agents'] if a['kind'] in kinds]
meta = build_world(out_dir, grid, heights, scene['blocked'], agents, ctx_dn=aux['ctx_ortho_dn'], physical=physical)
print(json.dumps({k: meta[k] for k in ('world_name', 'z_ref_m', 'relief_m', 'boulders', 'small_rocks')}))
