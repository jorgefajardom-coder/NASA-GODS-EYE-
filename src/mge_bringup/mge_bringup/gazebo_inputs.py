"""Validate an explicitly selected Gazebo world before starting a MOCK run.

This is an experimental launch boundary, not the approved simulation profile.
World files describe a reusable scene; run identity belongs to the ROS launch.
"""
import json
from hashlib import sha256
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from mge_sim.initial_conditions import load_agents


IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
MODELS = {'HUMAN': 'astronaut', 'DRONE': 'drone', 'ROVER': 'rover'}


def _require(condition, reason):
    if not condition:
        raise ValueError('NOT_READY: ' + reason)


def validate_inputs(world_sdf, world_json, agents_file, run_id, rover_id, domain_id):
    """Return resolved input identities, or reject inconsistent scene/configuration.

    A dedicated ROS domain is required, never selected or changed implicitly.
    Existing world.json files have no run_id; if supplied, it must match launch.
    """
    _require(isinstance(run_id, str) and IDENTIFIER.fullmatch(run_id), 'INVALID_RUN_ID')
    _require(isinstance(rover_id, str) and IDENTIFIER.fullmatch(rover_id), 'INVALID_ROVER_ID')
    _require(isinstance(domain_id, str) and domain_id.isascii() and domain_id.isdecimal()
             and 0 <= int(domain_id) <= 232, 'EXPLICIT_ROS_DOMAIN_ID_REQUIRED')
    paths = [Path(value).expanduser().resolve() for value in (world_sdf, world_json, agents_file)]
    _require(all(path.is_file() for path in paths), 'WORLD_AND_AGENTS_FILES_REQUIRED')
    sdf_path, meta_path, agents_path = paths
    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        root = ET.parse(sdf_path).getroot()
        agents = load_agents(agents_path)
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        raise ValueError('NOT_READY: INVALID_WORLD_OR_AGENTS: ' + str(exc)) from exc
    _require(isinstance(meta, dict), 'INVALID_WORLD_METADATA')
    hashes = meta.get('input_files', {})
    _require(isinstance(hashes, dict), 'INVALID_WORLD_INPUT_HASHES')
    for key, path in (('agents_sha256', agents_path), ('world_sdf_sha256', sdf_path)):
        _require(key not in hashes or hashes[key] == sha256(path.read_bytes()).hexdigest(),
                 'WORLD_INPUT_HASH_MISMATCH')
    name = meta.get('world_name')
    _require(isinstance(name, str) and IDENTIFIER.fullmatch(name), 'INVALID_WORLD_NAME')
    _require('run_id' not in meta or meta['run_id'] == run_id, 'WORLD_RUN_MISMATCH')
    z_ref = meta.get('z_ref_m')
    _require(isinstance(z_ref, (int, float)) and not isinstance(z_ref, bool)
             and math.isfinite(z_ref), 'INVALID_WORLD_HEIGHT_REFERENCE')
    # The reused vertical's real data provider serves its default public crop.
    # An unrelated Gazebo extent must not be paired with that mapping silently.
    from mge_data.core import default_manifest_path, load_public_terrain
    tile = load_public_terrain(default_manifest_path())
    expected = {'origin_x_m': tile.metadata.origin_x_m, 'origin_y_m': tile.metadata.origin_y_m,
                'resolution_m': tile.metadata.resolution_m,
                'rows': tile.prior.shape[0], 'cols': tile.prior.shape[1]}
    _require(all(type(meta.get(key)) in (int, float) and meta[key] == value
                 for key, value in expected.items()), 'WORLD_PUBLIC_GRID_MISMATCH')
    worlds = root.findall('world')
    _require(root.tag == 'sdf' and len(worlds) == 1 and worlds[0].get('name') == name,
             'WORLD_NAME_MISMATCH')
    world = worlds[0]
    _require(not world.findall('.//include'), 'SELF_CONTAINED_WORLD_REQUIRED')
    resources = world.findall('.//uri') + world.findall('.//texture/diffuse') + world.findall('.//texture/normal')
    for resource in resources:
        local = (sdf_path.parent / (resource.text or '')).resolve()
        _require(local.is_relative_to(sdf_path.parent) and local.is_file(), 'WORLD_RESOURCE_REQUIRED')
    world_models = world.findall('model')
    names = [model.get('name') for model in world_models]
    _require(len(names) == len(set(names)), 'DUPLICATE_WORLD_MODEL')
    models = dict(zip(names, world_models))
    by_id = {agent['id']: agent for agent in agents}
    _require(all(IDENTIFIER.fullmatch(agent_id) for agent_id in by_id), 'INVALID_AGENT_ID')
    entries = meta.get('agents')
    _require(isinstance(entries, dict) and set(entries) == set(by_id), 'WORLD_AGENT_IDS_MISMATCH')
    _require(rover_id in by_id and by_id[rover_id]['kind'] == 'ROVER', 'PHYSICAL_ROVER_REQUIRED')
    _require(all(isinstance(value, dict) and isinstance(value.get('physical'), bool)
                 for value in entries.values()), 'EXPLICIT_PHYSICAL_AGENT_FLAGS_REQUIRED')
    _require({agent_id for agent_id, value in entries.items() if value['physical']} == {rover_id},
             'EXACTLY_ONE_PHYSICAL_ROVER_REQUIRED')
    for agent_id, agent in by_id.items():
        budget_names = ('time_budget_s', 'energy_budget_wh') + (('oxygen_budget_l',)
                       if agent['kind'] == 'HUMAN' else ())
        _require(all(type(agent.get(key)) in (int, float) and math.isfinite(agent[key])
                     and agent[key] >= 0 for key in budget_names), 'INVALID_AGENT_BUDGET')
        info = entries[agent_id]
        _require(info.get('model') == MODELS[agent['kind']] and agent_id in models,
                 'WORLD_AGENT_KIND_MISMATCH')
        model = models[agent_id]
        try:
            pose = [float(value) for value in model.findtext('pose', '').split()]
            lift = float(info['lift_m'])
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError('NOT_READY: INVALID_AGENT_SPAWN') from exc
        _require(len(pose) == 6 and all(math.isfinite(value) for value in (*pose, lift)),
                 'INVALID_AGENT_SPAWN')
        _require(math.dist(pose[:2], (agent['x_m'], agent['y_m'])) <= 0.002,
                 'WORLD_AGENT_SPAWN_MISMATCH')
        if agent_id == rover_id:
            plugins = {plugin.get('name'): plugin for plugin in model.findall('plugin')}
            drive = plugins.get('gz::sim::systems::DiffDrive')
            odom = plugins.get('gz::sim::systems::OdometryPublisher')
            _require(drive is not None and odom is not None and lift == 0.0
                     and model.find('link/collision') is not None,
                     'PHYSICAL_ROVER_PLUGINS_REQUIRED')
            _require(drive.findtext('topic') == f'/model/{rover_id}/cmd_vel'
                     and odom.findtext('odom_topic') == f'/model/{rover_id}/odometry_gt',
                     'PHYSICAL_ROVER_TOPICS_MISMATCH')
        else:
            _require(not model.findall('link/collision')
                     and all(link.findtext('gravity') == 'false' for link in model.findall('link')),
                     'MIRRORED_AGENTS_MUST_BE_VISUAL_ONLY')
            _require(abs(pose[2] - (agent['z_m'] - z_ref + lift)) <= 0.002,
                     'WORLD_AGENT_SPAWN_MISMATCH')
    plugins = {plugin.get('name') for plugin in world.findall('plugin')}
    _require({'gz::sim::systems::Physics', 'gz::sim::systems::UserCommands'} <= plugins,
             'WORLD_PHYSICS_AND_POSE_SERVICE_REQUIRED')
    return {'world_sdf': str(sdf_path), 'world_json': str(meta_path),
            'agents_file': str(agents_path), 'world_name': name,
            'agent_ids': sorted(by_id), 'run_id': run_id, 'rover_id': rover_id}


def validate_sensor_scene(world_json, scene_file):
    """Sensing and world collision geometry must originate in the same scene file."""
    meta = json.loads(Path(world_json).read_text(encoding='utf-8'))
    hashes = meta.get('input_files', {})
    expected = hashes.get('scene_sha256') if isinstance(hashes, dict) else None
    _require(isinstance(expected, str) and len(expected) == 64,
             'SCENE_WORLD_BINDING_REQUIRED: regenerate the world with gazebo_world.py')
    _require(expected == sha256(Path(scene_file).read_bytes()).hexdigest(), 'SENSOR_WORLD_SCENE_MISMATCH')
