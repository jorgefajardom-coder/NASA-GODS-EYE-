"""Fail-closed world/agent checks without ROS or a running simulator."""
import json
import importlib.util
from hashlib import sha256
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from mge_bringup.gazebo_inputs import validate_inputs, validate_sensor_scene
from mge_sim.initial_conditions import load_agents


@pytest.fixture
def inputs(tmp_path):
    agents = {'agents': [
        {'id': 'rover_1', 'kind': 'ROVER', 'x_m': -14., 'y_m': -10., 'z_m': -2570.,
         'time_budget_s': 100., 'energy_budget_wh': 100.},
        {'id': 'human_1', 'kind': 'HUMAN', 'x_m': -14., 'y_m': -14., 'z_m': -2570.,
         'time_budget_s': 100., 'energy_budget_wh': 100., 'oxygen_budget_l': 100.},
    ]}
    meta = {'world_name': 'jezero', 'z_ref_m': -2570.,
            'origin_x_m': -64., 'origin_y_m': -64., 'resolution_m': 4., 'rows': 32, 'cols': 32,
            'agents': {'rover_1': {'model': 'rover', 'lift_m': 0., 'physical': True},
                       'human_1': {'model': 'astronaut', 'lift_m': .95, 'physical': False}}}
    sdf = '''<sdf version="1.10"><world name="jezero">
      <plugin name="gz::sim::systems::Physics"/><plugin name="gz::sim::systems::UserCommands"/>
      <model name="rover_1"><pose>-14 -10 .05 0 0 0</pose><link name="chassis"><collision name="c"/></link>
       <plugin name="gz::sim::systems::DiffDrive"><topic>/model/rover_1/cmd_vel</topic></plugin>
       <plugin name="gz::sim::systems::OdometryPublisher"><odom_topic>/model/rover_1/odometry_gt</odom_topic></plugin>
      </model><model name="human_1"><pose>-14 -14 .95 0 0 0</pose>
       <link name="link"><gravity>false</gravity></link></model></world></sdf>'''
    (tmp_path / 'world.sdf').write_text(sdf)
    (tmp_path / 'world.json').write_text(json.dumps(meta))
    (tmp_path / 'agents.yaml').write_text(yaml.safe_dump(agents))
    return {'world_sdf': tmp_path / 'world.sdf', 'world_json': tmp_path / 'world.json',
            'agents_file': tmp_path / 'agents.yaml', 'run_id': 'gazebo-input-test',
            'rover_id': 'rover_1', 'domain_id': '219'}


def change_meta(inputs, edit):
    value = json.loads(inputs['world_json'].read_text())
    edit(value)
    inputs['world_json'].write_text(json.dumps(value))


def test_matching_reusable_scene_requires_an_explicit_run_and_domain(inputs):
    result = validate_inputs(**inputs)
    assert result['world_name'] == 'jezero'
    assert result['agent_ids'] == ['human_1', 'rover_1']
    assert result['run_id'] == 'gazebo-input-test'


@pytest.mark.parametrize('domain', ['', '-1', '233', '0.5', '１２'])
def test_missing_or_invalid_domain_is_rejected(inputs, domain):
    with pytest.raises(ValueError, match='EXPLICIT_ROS_DOMAIN_ID_REQUIRED'):
        validate_inputs(**{**inputs, 'domain_id': domain})


@pytest.mark.parametrize('key,value', [('run_id', ''), ('run_id', '../other'), ('rover_id', 'bad/id')])
def test_invalid_id_is_rejected(inputs, key, value):
    with pytest.raises(ValueError, match='INVALID_.*ID'):
        validate_inputs(**{**inputs, key: value})


@pytest.mark.parametrize('edit,reason', [
    (lambda m: m.update(world_name='another'), 'WORLD_NAME_MISMATCH'),
    (lambda m: m.update(run_id='foreign-run'), 'WORLD_RUN_MISMATCH'),
    (lambda m: m.update(resolution_m=8.), 'WORLD_PUBLIC_GRID_MISMATCH'),
    (lambda m: m.update(z_ref_m=float('nan')), 'INVALID_WORLD_HEIGHT_REFERENCE'),
    (lambda m: m['agents']['rover_1'].update(physical=False), 'EXACTLY_ONE_PHYSICAL_ROVER_REQUIRED'),
    (lambda m: m['agents']['human_1'].update(physical=True), 'EXACTLY_ONE_PHYSICAL_ROVER_REQUIRED'),
    (lambda m: m['agents']['rover_1'].update(model='drone'), 'WORLD_AGENT_KIND_MISMATCH'),
    (lambda m: m['agents'].pop('human_1'), 'WORLD_AGENT_IDS_MISMATCH'),
])
def test_incompatible_world_metadata_is_rejected(inputs, edit, reason):
    change_meta(inputs, edit)
    with pytest.raises(ValueError, match=reason):
        validate_inputs(**inputs)


@pytest.mark.parametrize('edit,reason', [
    (lambda w: w.find('model/plugin/topic').__setattr__('text', '/wrong'), 'PHYSICAL_ROVER_TOPICS_MISMATCH'),
    (lambda w: w.find('model/pose').__setattr__('text', '10 20 .05 0 0 0'), 'WORLD_AGENT_SPAWN_MISMATCH'),
    (lambda w: ET.SubElement(w, 'include'), 'SELF_CONTAINED_WORLD_REQUIRED'),
    (lambda w: ET.SubElement(w, 'uri').__setattr__('text', 'missing.obj'), 'WORLD_RESOURCE_REQUIRED'),
    (lambda w: ET.SubElement(w.find("model[@name='human_1']/link"), 'collision'),
     'MIRRORED_AGENTS_MUST_BE_VISUAL_ONLY'),
])
def test_incompatible_sdf_is_rejected(inputs, edit, reason):
    tree = ET.parse(inputs['world_sdf'])
    edit(tree.getroot().find('world'))
    tree.write(inputs['world_sdf'])
    with pytest.raises(ValueError, match=reason):
        validate_inputs(**inputs)


def test_missing_world_file_is_rejected(inputs):
    inputs['world_sdf'].unlink()
    with pytest.raises(ValueError, match='WORLD_AND_AGENTS_FILES_REQUIRED'):
        validate_inputs(**inputs)


def test_world_script_reuses_declared_public_scene_heights(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('gazebo_world_script',
        root / 'scripts/live_scenarios/gazebo_world.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scene = tmp_path / 'scene.json'
    scene.write_text(json.dumps({'schema_version': 'mge-sim-scene-1.0.0',
                                'source_kind': 'SIMULATED', 'rows': 32, 'cols': 32, 'blocked': []}))
    agents_file = root / 'src/mge_bringup/config/agents_jezero.yaml'
    expected = load_agents(agents_file)
    models = tmp_path / 'models'
    models.mkdir()
    for name in ('rover.glb', 'drone.glb', 'astronaut.glb', 'base.glb'):
        (models / name).write_bytes(b'model fixture; writer mocked below')
    captured = []
    def capture(out, grid, heights, blocked, agents, **kwargs):
        captured.extend(agents)
        Path(out).mkdir()
        (Path(out) / 'world.sdf').write_text('generated fixture')
        assert kwargs['base_xy'] == next((a['x_m'], a['y_m']) for a in expected if a['kind'] == 'HUMAN')
        assert kwargs['web_models'] == {
            'ROVER': models / 'rover.glb', 'DRONE': models / 'drone.glb',
            'HUMAN': models / 'astronaut.glb', 'BASE': models / 'base.glb'}
        return {'physical': kwargs['physical']}
    monkeypatch.setattr(module, 'build_world', capture)
    result = module.build_from_files(scene, agents_file, tmp_path / 'world', ('rover_1',), models_dir=models)
    assert result['physical'] == ('rover_1',)
    assert result['input_files']['scene_sha256'] == sha256(scene.read_bytes()).hexdigest()
    assert captured == [(a['id'], a['kind'], a['x_m'], a['y_m'], a['z_m']) for a in expected]
    assert len({a[4] for a in captured}) > 1     # no blanket minimum-height fallback
    with pytest.raises(ValueError, match='configured ROVER'):
        module.build_from_files(scene, agents_file, tmp_path / 'invalid', ('human_1',))


def test_sensing_requires_the_exact_world_scene(inputs, tmp_path):
    scene = tmp_path / 'scene.json'
    scene.write_text('{"source_kind": "SIMULATED"}')
    with pytest.raises(ValueError, match='SCENE_WORLD_BINDING_REQUIRED'):
        validate_sensor_scene(inputs['world_json'], scene)
    change_meta(inputs, lambda m: m.update(input_files={'scene_sha256': sha256(scene.read_bytes()).hexdigest()}))
    validate_sensor_scene(inputs['world_json'], scene)
    scene.write_text('{"source_kind": "SIMULATED", "blocked": [12]}')
    with pytest.raises(ValueError, match='SENSOR_WORLD_SCENE_MISMATCH'):
        validate_sensor_scene(inputs['world_json'], scene)


@pytest.mark.parametrize('key', ['agents_sha256', 'world_sdf_sha256'])
def test_changed_bound_inputs_are_rejected(inputs, key):
    change_meta(inputs, lambda m: m.update(input_files={key: '0' * 64}))
    with pytest.raises(ValueError, match='WORLD_INPUT_HASH_MISMATCH'):
        validate_inputs(**inputs)
