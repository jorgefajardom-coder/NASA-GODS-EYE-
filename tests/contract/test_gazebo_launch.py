"""Actual Jazzy launch actions preserve MOCK authority and one physical rover."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip('launch_ros', reason='Requires ROS 2 Jazzy launch packages')
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.utilities import perform_substitutions
from launch_ros.utilities import evaluate_parameters, normalize_parameters

ROOT = Path(__file__).resolve().parents[2]


def load_launch():
    spec = importlib.util.spec_from_file_location('gazebo_launch_under_test',
        ROOT / 'src/mge_bringup/launch/gazebo_mock.launch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def context(**changes):
    value = LaunchContext()
    value.environment['ROS_DOMAIN_ID'] = '219'
    value.launch_configurations.update({
        'run_id': 'gazebo-launch-test', 'world_sdf': '/tmp/world.sdf',
        'world_json': '/tmp/world.json', 'agents_file': '/tmp/agents.yaml',
        'rover_id': 'rover_1', 'gui': 'false', 'host': '127.0.0.1', 'port': '8019',
        'record': 'false', 'record_dir': '/tmp/recordings', 'profiles_file': '',
        'exploration_policy_file': '', 'allow_continuous_starts': 'false',
        'allow_legacy_cost_model': 'false',
        'budget_fallback': 'false', 'complete_on_return': 'false', 'completion_tolerance_m': '1.0',
        'sensor': 'false', 'sensor_scene_file': '', **changes,
    })
    return value


INPUTS = {'run_id': 'gazebo-launch-test', 'world_name': 'jezero',
          'world_sdf': '/tmp/world.sdf', 'world_json': '/tmp/world.json',
          'agents_file': '/tmp/agents.yaml', 'rover_id': 'rover_1',
          'agent_ids': ['drone_1', 'human_1', 'rover_1']}


def test_launch_does_not_promote_profile_or_start_a_goal():
    module = load_launch()
    description = module.generate_launch_description()
    declarations = [action for action in description.entities if isinstance(action, DeclareLaunchArgument)]
    names = {action.name for action in declarations}
    assert not names & {'profile', 'mission', 'terrain', 'planner', 'use_sim_time', 'agents', 'external_agents'}
    defaults = {action.name: perform_substitutions(context(), action.default_value)
                for action in declarations if action.default_value is not None}
    assert defaults['gui'] == defaults['sensor'] == defaults['record'] == 'false'
    assert defaults['budget_fallback'] == defaults['complete_on_return'] == 'false'
    assert defaults['allow_legacy_cost_model'] == 'false'


@pytest.mark.parametrize('gui,headless', [('false', True), ('true', False)])
def test_start_wires_one_way_world_clock_and_scopes_gazebo_transport(monkeypatch, tmp_path, gui, headless):
    module = load_launch()
    calls, nodes = [], []
    monkeypatch.setattr(module, 'validate_inputs', lambda *args: INPUTS)
    monkeypatch.setattr(module.shutil, 'which', lambda name: '/usr/bin/gz')
    bridge = tmp_path / 'lib/ros_gz_bridge/parameter_bridge'
    bridge.parent.mkdir(parents=True)
    bridge.write_text('')
    monkeypatch.setattr(module, 'get_package_prefix', lambda name: str(tmp_path))
    monkeypatch.setattr(module.os, 'access', lambda *args: True)
    monkeypatch.setattr(module, '_probe_clock', lambda **kwargs: calls.append(kwargs))
    original = module.Node
    def capture(**kwargs):
        nodes.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(module, 'Node', capture)
    actions = module._start(context(gui=gui))
    assert calls == [{'require_clean': True}]
    gazebo = next(action for action in actions if isinstance(action, ExecuteProcess))
    command = [perform_substitutions(context(), item) for item in gazebo.cmd]
    assert command == ['gz', 'sim', '-r', *(['-s'] if headless else []), '/tmp/world.sdf']
    bridge_node = nodes[0]
    assert bridge_node['package'] == 'ros_gz_bridge'
    assert bridge_node['arguments'] == ['/world/jezero/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock']
    assert bridge_node['remappings'] == [('/world/jezero/clock', '/clock')]
    assert bridge_node['parameters'] == [{'use_sim_time': True}]
    environment = next(action for action in actions if isinstance(action, module.SetEnvironmentVariable))
    assert perform_substitutions(context(), environment.name) == 'GZ_PARTITION'
    assert perform_substitutions(context(), environment.value) == 'mge-gazebo-launch-test'


@pytest.mark.parametrize('legacy', ['false', 'true'])
def test_consumers_wait_for_clock_and_keep_single_agent_providers(monkeypatch, legacy):
    module = load_launch()
    calls, nodes = [], []
    monkeypatch.setattr(module, '_probe_clock', lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(module, 'get_package_share_directory', lambda name: '/tmp/share')
    original = module.Node
    def capture(**kwargs):
        nodes.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(module, 'Node', capture)
    actions = module._consumers(context(mission='real', agents='static', use_sim_time='false',
                                        allow_legacy_cost_model=legacy), INPUTS)
    assert calls == [{}]
    included = next(action for action in actions if isinstance(action, IncludeLaunchDescription))
    arguments = dict(included.launch_arguments)
    assert arguments['mission'] == 'mock'
    assert arguments['terrain'] == arguments['planner'] == 'real'
    assert arguments['use_sim_time'] == 'true'
    assert arguments['agents'] == 'kinematic' and arguments['external_agents'] == 'rover_1'
    assert arguments['allow_legacy_cost_model'] == legacy
    assert {node['executable'] for node in nodes} == {'gz_rover_driver', 'gz_mirror'}
    for node in nodes:
        values = evaluate_parameters(context(), normalize_parameters(node['parameters']))[0]
        assert values['use_sim_time'] is True and values['run_id'] == INPUTS['run_id']
        assert values['world_json'] == INPUTS['world_json']
        if node['executable'] == 'gz_rover_driver':
            assert values['agent_id'] == 'rover_1' and values['agents_file'] == INPUTS['agents_file']


def test_clock_failure_starts_no_consumers(monkeypatch):
    module = load_launch()
    def unavailable(**kwargs):
        raise RuntimeError('NOT_READY: ADVANCING_GAZEBO_CLOCK_REQUIRED')
    monkeypatch.setattr(module, '_probe_clock', unavailable)
    monkeypatch.setattr(module, 'Node', lambda **kwargs: pytest.fail('started before clock preflight'))
    with pytest.raises(RuntimeError, match='ADVANCING_GAZEBO_CLOCK_REQUIRED'):
        module._consumers(context(), INPUTS)


def test_missing_sensor_scene_fails_before_any_process(monkeypatch):
    module = load_launch()
    monkeypatch.setattr(module, 'validate_inputs', lambda *args: INPUTS)
    monkeypatch.setattr(module, '_probe_clock', lambda **kwargs: pytest.fail('preflight ran before file checks'))
    with pytest.raises(RuntimeError, match='SIMULATED_SENSOR_SCENE_REQUIRED'):
        module._start(context(sensor='true', sensor_scene_file='/missing/scene.json'))


def test_clock_preflight_uses_an_independent_ros_context(monkeypatch):
    # The launcher has not initialized rclpy's default context. A custom-context
    # node must use an executor created with that same context.
    monkeypatch.setenv('ROS_DOMAIN_ID', '229')
    load_launch()._probe_clock(require_clean=True)
