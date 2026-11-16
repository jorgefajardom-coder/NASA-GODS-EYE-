"""Build the Gazebo world of a sensing run: public jezero_mvp terrain + its SIMULATED scene.

Run from a built, sourced workspace root:
  python3 scripts/live_scenarios/gazebo_world.py <scene.json> <agents.yaml> <out_dir>
Then: gz sim -r <out_dir>/world.sdf   and   ros2 run mge_sim gz_mirror --ros-args
  -p run_id:=<run_id> -p world_json:=<out_dir>/world.json
"""
import json
from hashlib import sha256
from pathlib import Path
import sys

import numpy as np

from mge_data.core import default_manifest_path, load_public_terrain
from mge_sim.gz_world import build_world
from mge_sim.initial_conditions import load_agents
from mge_sim.scene_sensing import scene_from_file

def build_from_files(scene_file, agents_file, out_dir, physical=(), models_dir=None):
    """Reuse the same declared NEW_SCENE initialization as ROS agent producers."""
    tile = load_public_terrain(default_manifest_path())
    rows, cols = tile.prior.shape
    m = tile.metadata
    grid = (m.origin_x_m, m.origin_y_m, m.resolution_m, rows, cols)
    heights = np.where(tile.nodata_mask, np.nan, tile.prior)
    scene = scene_from_file(scene_file, (rows, cols, *grid[:3]), heights.reshape(-1))
    specifications = load_agents(agents_file)
    kinds = {agent['id']: agent['kind'] for agent in specifications}
    if len(physical) != len(set(physical)) or any(kinds.get(agent_id) != 'ROVER' for agent_id in physical):
        raise ValueError('physical agent IDs must identify distinct configured ROVER agents')
    agents = [(a['id'], a['kind'], a['x_m'], a['y_m'], a['z_m']) for a in specifications]
    # Preserve the remote GLB/base additions and their existing licensing metadata.
    model_root = Path(models_dir) if models_dir is not None else Path('web/public/assets/models')
    web_models = {kind: model_root / name for kind, name in
                  (('ROVER', 'rover.glb'), ('DRONE', 'drone.glb'),
                   ('HUMAN', 'astronaut.glb'), ('BASE', 'base.glb'))
                  if (model_root / name).is_file()}
    home = next(((x, y) for _, kind, x, y, _ in agents if kind == 'HUMAN'), None)
    with np.load(Path(default_manifest_path()).parent / 'jezero_aux_layers.npz') as aux:
        meta = build_world(out_dir, grid, heights, scene.blocked, agents,
                           ctx_dn=aux['ctx_ortho_dn'], physical=physical,
                           web_models=web_models, base_xy=home)
    meta['input_files'] = {
        'scene_sha256': sha256(Path(scene_file).read_bytes()).hexdigest(),
        'agents_sha256': sha256(Path(agents_file).read_bytes()).hexdigest(),
        'world_sdf_sha256': sha256((Path(out_dir) / 'world.sdf').read_bytes()).hexdigest(),
    }
    (Path(out_dir) / 'world.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    return meta


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) not in (3, 4, 5):
        raise SystemExit('usage: gazebo_world.py <scene.json> <agents.yaml> <out_dir> [physical_ids] [models_dir]')
    physical = tuple(agent_id for agent_id in (arguments[3] if len(arguments) >= 4 else '').split(',') if agent_id)
    meta = build_from_files(*arguments[:3], physical=physical,
                           models_dir=arguments[4] if len(arguments) == 5 else None)
    print(json.dumps({key: meta[key] for key in (
        'world_name', 'z_ref_m', 'relief_m', 'boulders', 'small_rocks', 'web_models')}))


if __name__ == '__main__':
    main()
