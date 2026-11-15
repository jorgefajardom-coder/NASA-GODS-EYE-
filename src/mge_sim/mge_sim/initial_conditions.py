"""Initial positions for a NEW labelled SIMULATED scene, never telemetry.

Explicit XYZ is preserved. Missing Z needs an explicit public-prior scene
declaration; it is never interpreted as zero, an observation or flight altitude.
"""
from copy import deepcopy
import math
from pathlib import Path

import yaml


KINDS = frozenset({'HUMAN', 'ROVER', 'DRONE'})
SCENE_FIELDS = frozenset({'source_kind', 'phase', 'height_source', 'dataset_id',
                          'prior_sha256', 'vertical_datum', 'drone_state'})


def _coordinate(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be an explicit finite coordinate')
    return float(value)


def _scene_terrain(declaration):
    # Reuse the public loader's provenance/checksum/NoData/reference guards.
    from mge_data.core import default_manifest_path, load_public_terrain
    tile = load_public_terrain(default_manifest_path())
    if (tile.metadata.dataset_id != declaration['dataset_id']
            or tile.metadata.vertical_datum != declaration['vertical_datum']
            or tile.sources.by_role('prior').sha256 != declaration['prior_sha256']):
        raise ValueError('SIMULATED scene does not match its declared public terrain identity')
    return tile


def initialize_public_scene(agents, declaration):
    """Complete only absent Z in declared new initial conditions.

    Every agent is initially on the public-prior surface; the drone is PARKED.
    Existing XYZ must agree with that scene and is validated, never projected.
    This creates no local observation, traversability approval or flight claim.
    """
    if (not isinstance(declaration, dict) or set(declaration) != SCENE_FIELDS
            or declaration['source_kind'] != 'SIMULATED' or declaration['phase'] != 'NEW_SCENE'
            or declaration['height_source'] != 'PUBLIC_PRIOR' or declaration['drone_state'] != 'PARKED'
            or any(not isinstance(declaration[key], str) or not declaration[key].strip()
                   for key in ('dataset_id', 'prior_sha256', 'vertical_datum'))):
        raise ValueError('explicit NEW_SCENE/SIMULATED/PUBLIC_PRIOR/PARKED initialization is required')
    tile = _scene_terrain(declaration)
    result = deepcopy(agents)
    for agent in result:
        x, y = (_coordinate(agent[name], name) for name in ('x_m', 'y_m'))
        cell = tile.transform.enu_to_cell(x, y)
        height = float(tile.prior[cell])
        if tile.nodata_mask[cell] or not math.isfinite(height):
            raise ValueError(f"agent {agent['id']}: no public scene height at this position")
        if 'z_m' in agent:
            explicit = _coordinate(agent['z_m'], 'z_m')
            if abs(explicit-height) > 1e-6:
                raise ValueError(f"agent {agent['id']}: explicit XYZ disagrees with the declared parked scene")
        else:
            agent['z_m'] = height
    return result


def load_agents(path):
    """Read complete initial XYZ or explicitly create a new public-prior scene."""
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('agents'), list) or not data['agents']:
        raise ValueError('agent configuration requires a nonempty agents list')
    agents = deepcopy(data['agents'])
    ids = []
    for agent in agents:
        if not isinstance(agent, dict) or not isinstance(agent.get('id'), str) or not agent['id'].strip():
            raise ValueError('every agent requires an explicit identity')
        if not isinstance(agent.get('kind'), str) or agent['kind'] not in KINDS:
            raise ValueError(f"agent {agent['id']}: unknown kind")
        ids.append(agent['id'])
        for name in ('x_m', 'y_m'):
            _coordinate(agent.get(name), name)
        if 'z_m' in agent:
            _coordinate(agent['z_m'], 'z_m')
    if len(ids) != len(set(ids)):
        raise ValueError(f'duplicate agent ids in {path}')
    if 'initial_conditions' in data:
        agents = initialize_public_scene(agents, data['initial_conditions'])
    if any('z_m' not in agent for agent in agents):
        raise ValueError('z_m is required: missing altitude is not zero; declare new SIMULATED scene inputs')
    return agents
