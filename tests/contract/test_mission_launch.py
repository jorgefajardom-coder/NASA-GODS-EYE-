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
        'mission': mission, 'planner': planner, 'terrain': 'mock', 'host': '127.0.0.1', 'port': '8769',
        'agents_file': str(ROOT / 'src/mge_bringup/config/agents.yaml'),
        'profiles_file': str(ROOT / 'config/planner_profiles.illustrative.json'),
        'mission_profiles_path': str(ROOT / 'config/scenario_demo.yaml'),
        'mission_path': str(ROOT / 'config/scenario_demo.yaml'),
        'base_enu_m': '[2.5, 2.5, 0.0]', 'allow_illustrative': 'true',
        'model_agreement_confirmed': 'false', 'approved_model_id': '',
        'record': 'false', 'record_dir': 'evidence', **changes,
    })
    return value


@pytest.mark.parametrize('terrain', ['mock', 'real'])
@pytest.mark.parametrize('mission', ['mock', 'real'])
@pytest.mark.parametrize('planner', ['mock', 'real'])
def test_selected_mission_and_planner_are_exclusive(monkeypatch, mission, planner, terrain):
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
                if node.condition is None or node.condition.evaluate(context(mission, planner, terrain=terrain))]
    assert set(selected) & {'mock_mission', 'mission_node'} == {
        'mock_mission' if mission == 'mock' else 'mission_node'}
    assert set(selected) & {'mock_planner', 'planning_node'} == {
        'mock_planner' if planner == 'mock' else 'planning_node'}
    assert set(selected) & {'mock_terrain', 'data_node', 'mapping_node'} == (
        {'mock_terrain'} if terrain == 'mock' else {'data_node', 'mapping_node'})


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
