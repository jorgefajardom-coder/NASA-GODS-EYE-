"""Evaluate real Jazzy launch conditions and owner parameter forwarding."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip('launch_ros', reason='Requires ROS 2 Jazzy launch packages')
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument
from launch.utilities import perform_substitutions
from launch_ros.utilities import evaluate_parameters, normalize_parameters

ROOT = Path(__file__).resolve().parents[2]


def load_launch():
    spec = importlib.util.spec_from_file_location('mission_launch_under_test',
        ROOT / 'src/mge_bringup/launch/vertical_mock.launch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def context(mission='real', planner='real', **changes):
    value = LaunchContext()
    value.launch_configurations.update({
        'run_id': 'mission-launch-contract', 'use_sim_time': 'true',
        'mission': mission, 'planner': planner, 'terrain': 'mock', 'agents': 'static',
        'host': '127.0.0.1', 'port': '8769',
        'cors_origins': "['http://localhost:5173', 'http://127.0.0.1:5173']",
        'agents_file': str(ROOT / 'src/mge_bringup/config/agents.yaml'),
        'profiles_file': str(ROOT / 'config/planner_profiles.illustrative.json'),
        'scientific_profiles_path': str(ROOT / 'config/scenario_demo.yaml'),
        'allow_legacy_cost_model': 'false',
        'exploration_policy_file': '',
        'mission_profiles_path': str(ROOT / 'config/scenario_demo.yaml'),
        'mission_path': str(ROOT / 'config/scenario_demo.yaml'),
        'base_enu_m': '[2.5, 2.5, 0.0]', 'allow_illustrative': 'true',
        'model_agreement_confirmed': 'false', 'approved_model_id': '',
        'allow_continuous_starts': 'false', 'budget_fallback': 'false', 'complete_on_return': 'false', 'completion_tolerance_m': '0.001', 'external_agents': '',
        'sensor': 'false', 'sensor_scene_file': '',
        'sensor_agents': "['drone_1', 'human_1', 'rover_1']", 'sensor_radii_m': '[24.0, 8.0, 12.0]',
        'record': 'false', 'record_dir': 'evidence', **changes,
    })
    return value


@pytest.mark.parametrize('agents', ['static', 'kinematic'])
@pytest.mark.parametrize('terrain', ['mock', 'real'])
@pytest.mark.parametrize('mission', ['mock', 'real'])
@pytest.mark.parametrize('planner', ['mock', 'real'])
def test_selected_mission_and_planner_are_exclusive(monkeypatch, mission, planner, terrain, agents):
    module = load_launch()
    original = module.Node
    nodes = []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append((node, kwargs))
        return node
    monkeypatch.setattr(module, 'Node', capture)
    module.generate_launch_description()
    selected = [kwargs['executable'] for node, kwargs in nodes
                if node.condition is None or node.condition.evaluate(
                    context(mission, planner, terrain=terrain, agents=agents))]
    assert set(selected) & {'mock_mission', 'mission_node'} == {
        'mock_mission' if mission == 'mock' else 'mission_node'}
    assert set(selected) & {'mock_planner', 'planning_node'} == {
        'mock_planner' if planner == 'mock' else 'planning_node'}
    assert set(selected) & {'mock_terrain', 'data_node', 'mapping_node'} == (
        {'mock_terrain'} if terrain == 'mock' else {'data_node', 'mapping_node'})
    # Exactly one publisher per agent state topic.
    assert set(selected) & {'mock_agents', 'kinematic_executor'} == {
        'mock_agents' if agents == 'static' else 'kinematic_executor'}


def test_real_owner_parameters_forward_without_autoagreement(monkeypatch):
    module = load_launch()
    original, nodes = module.Node, []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append(kwargs)
        return node
    monkeypatch.setattr(module, 'Node', capture)
    description = module.generate_launch_description()
    mission = next(item for item in nodes if item['executable'] == 'mission_node')
    values = evaluate_parameters(context(), normalize_parameters(mission['parameters']))[0]
    assert values['profiles_path'] == str(ROOT / 'config/scenario_demo.yaml')
    assert values['mission_path'] == str(ROOT / 'config/scenario_demo.yaml')
    assert values['run_id'] == 'mission-launch-contract'
    assert values['use_sim_time'] is True
    assert values['base_enu_m'] == [2.5, 2.5, 0.0]
    assert values['allow_illustrative'] is True
    assert values['model_agreement_confirmed'] is False
    assert values['approved_model_id'] == ''
    defaults = {item.name: perform_substitutions(context(), item.default_value)
                for item in description.entities if isinstance(item, DeclareLaunchArgument)}
    assert defaults['mission'] == 'mock'
    assert defaults['allow_illustrative'] == defaults['model_agreement_confirmed'] == 'false'


def test_real_selection_rejects_wall_clock_and_missing_configuration(tmp_path):
    module = load_launch()
    with pytest.raises(RuntimeError, match='REQUIRES_SIM_TIME'):
        module._check_real_configuration(context(use_sim_time='false'))
    for key in ('mission_profiles_path', 'mission_path'):
        for missing in ('', str(tmp_path / 'missing.yaml')):
            with pytest.raises(RuntimeError, match='CONFIGURATION_REQUIRED'):
                module._check_real_configuration(context(**{key: missing}))
    assert module._check_real_configuration(context()) is True
    assert module._check_real_configuration(context(mission='mock', use_sim_time='false')) is False


def test_real_selection_cannot_skip_external_clock_preflight(monkeypatch):
    module = load_launch()
    def unavailable():
        raise RuntimeError('NOT_READY: EXTERNAL_SIMULATION_CLOCK_REQUIRED')
    monkeypatch.setattr(module, '_require_external_clock', unavailable)
    with pytest.raises(RuntimeError, match='EXTERNAL_SIMULATION_CLOCK_REQUIRED'):
        module._real_mission_preflight(context())
    assert module._real_mission_preflight(context(mission='mock')) == []


def test_real_terrain_rejects_mock_planner_before_startup():
    module=load_launch()
    with pytest.raises(RuntimeError,match='REAL_TERRAIN_REQUIRES_REAL_PLANNER'):
        module._check_terrain_selection(context(terrain='real',planner='mock'))
    assert module._check_terrain_selection(context(terrain='real',planner='real')) == []


@pytest.mark.parametrize('enabled', ['false', 'true'])
def test_continuous_start_opt_in_is_forwarded_only_to_the_real_planner(monkeypatch, enabled):
    module = load_launch()
    original, nodes = module.Node, []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append(kwargs)
        return node
    monkeypatch.setattr(module, 'Node', capture)
    description = module.generate_launch_description()
    ctx = context(allow_continuous_starts=enabled)
    defaults = {item.name: perform_substitutions(ctx, item.default_value)
                for item in description.entities if isinstance(item, DeclareLaunchArgument)}
    assert defaults['allow_continuous_starts'] == 'false'
    for item in nodes:
        values = evaluate_parameters(ctx, normalize_parameters(item.get('parameters', [])))
        if item['executable'] == 'planning_node':
            assert values[0]['allow_continuous_starts'] is (enabled == 'true')
        else:
            assert all('allow_continuous_starts' not in value for value in values)


@pytest.mark.parametrize('agents', ['static', 'kinematic'])
def test_only_kinematic_mock_mission_requires_stop_acknowledgement(monkeypatch, agents):
    module = load_launch()
    original, nodes = module.Node, []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append(kwargs)
        return node
    monkeypatch.setattr(module, 'Node', capture)
    module.generate_launch_description()
    ctx = context(mission='mock', agents=agents)
    for item in nodes:
        values = evaluate_parameters(ctx, normalize_parameters(item.get('parameters', [])))
        if item['executable'] == 'mock_mission':
            assert values[0]['require_stop_ack'] is (agents == 'kinematic')
        else:
            assert all('require_stop_ack' not in value for value in values)


@pytest.mark.parametrize('enabled', ['false', 'true'])
def test_budget_fallback_reaches_only_the_mock_mission(monkeypatch, enabled):
    module = load_launch()
    original, nodes = module.Node, []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append(kwargs)
        return node
    monkeypatch.setattr(module, 'Node', capture)
    module.generate_launch_description()
    ctx = context(mission='mock', budget_fallback=enabled)
    for item in nodes:
        values = evaluate_parameters(ctx, normalize_parameters(item.get('parameters', [])))
        if item['executable'] == 'mock_mission':
            assert values[0]['budget_fallback'] is (enabled == 'true')
        else:
            assert all('budget_fallback' not in value for value in values)


def test_scene_sensor_is_opt_in_and_receives_its_scene_and_radii(monkeypatch):
    module = load_launch()
    original, nodes = module.Node, []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append(kwargs)
        return node
    monkeypatch.setattr(module, 'Node', capture)
    module.generate_launch_description()
    sensor = next(item for item in nodes if item['executable'] == 'scene_sensor')
    assert sensor['condition'].evaluate(context(sensor='false')) is False
    ctx = context(sensor='true', sensor_scene_file='/tmp/scene.json')
    assert sensor['condition'].evaluate(ctx) is True
    values = evaluate_parameters(ctx, normalize_parameters(sensor['parameters']))[0]
    assert values['scene_file'] == '/tmp/scene.json'
    assert values['agent_ids'] == ['drone_1', 'human_1', 'rover_1']
    assert values['radii_m'] == [24.0, 8.0, 12.0]


def test_complete_on_return_reaches_only_the_mock_mission(monkeypatch):
    module = load_launch()
    original, nodes = module.Node, []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append(kwargs)
        return node
    monkeypatch.setattr(module, 'Node', capture)
    module.generate_launch_description()
    ctx = context(mission='mock', complete_on_return='true')
    for item in nodes:
        values = evaluate_parameters(ctx, normalize_parameters(item.get('parameters', [])))
        if item['executable'] == 'mock_mission':
            assert values[0]['complete_on_return'] is True
        else:
            assert all('complete_on_return' not in value for value in values)


def test_external_agents_reach_only_the_kinematic_executor(monkeypatch):
    module = load_launch()
    original, nodes = module.Node, []
    def capture(**kwargs):
        node = original(**kwargs)
        nodes.append(kwargs)
        return node
    monkeypatch.setattr(module, 'Node', capture)
    module.generate_launch_description()
    ctx = context(mission='mock', agents='kinematic', external_agents='rover_1', completion_tolerance_m='1.0')
    for item in nodes:
        values = evaluate_parameters(ctx, normalize_parameters(item.get('parameters', [])))
        if item['executable'] == 'kinematic_executor':
            assert values[0]['external_agents'] == 'rover_1'
        else:
            assert all('external_agents' not in value for value in values)
        if item['executable'] == 'mock_mission':
            assert values[0]['completion_tolerance_m'] == 1.0
