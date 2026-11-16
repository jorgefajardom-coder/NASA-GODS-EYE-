"""Opt-in Gazebo rover + kinematic companions under the existing MOCK mission.

No goal is sent. This does not enable profile:=simulation or a real mission.
"""
import os
from pathlib import Path
import shutil
from time import monotonic

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, ExecuteProcess, IncludeLaunchDescription,
                            LogInfo, OpaqueFunction, RegisterEventHandler,
                            SetEnvironmentVariable, TimerAction)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from mge_bringup.gazebo_inputs import validate_inputs, validate_sensor_scene


def _probe_clock(require_clean=False, timeout_s=15.0):
    """Bounded ROS graph/clock checks; a dedicated domain is still required."""
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from rosgraph_msgs.msg import Clock

    ros_context = Context()
    rclpy.init(args=[], context=ros_context)
    probe = rclpy.create_node('mge_gazebo_launch_preflight', context=ros_context)
    executor = SingleThreadedExecutor(context=ros_context)
    executor.add_node(probe)
    stamps = []
    subscription = None
    try:
        if not require_clean:
            subscription = probe.create_subscription(Clock, '/clock',
                lambda message: stamps.append(message.clock.sec * 10**9 + message.clock.nanosec),
                QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        deadline = monotonic() + (0.75 if require_clean else timeout_s)
        while monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
            if require_clean:
                continue
            count = probe.count_publishers('/clock')
            if count > 1:
                raise RuntimeError('PROVIDER_COLLISION: multiple ROS /clock publishers')
            if len(stamps) >= 2 and count == 1 and 0 <= stamps[-2] < stamps[-1]:
                return
        if require_clean:
            existing = {name for name, _ in probe.get_service_names_and_types()}
            if existing & {'/mge/planner/plan_route', '/mge/planner/register_context', '/mge/mission/set_goal'}:
                raise RuntimeError('PROVIDER_COLLISION: mission/planner service already active')
            topics = [name for name, _ in probe.get_topic_names_and_types()
                      if name == '/clock' or name.startswith('/mge/')]
            if any(probe.count_publishers(name) for name in topics):
                raise RuntimeError('PROVIDER_COLLISION: MGE or /clock publisher already active')
            return
        raise RuntimeError('NOT_READY: ADVANCING_GAZEBO_CLOCK_REQUIRED')
    finally:
        if subscription is not None:
            probe.destroy_subscription(subscription)
        executor.shutdown(timeout_sec=2.0)
        executor.remove_node(probe)
        probe.destroy_node()
        ros_context.shutdown()


def _consumers(context, inputs):
    _probe_clock()
    value = lambda name: LaunchConfiguration(name).perform(context)
    common = {'run_id': inputs['run_id'], 'use_sim_time': True}
    driver = Node(package='mge_sim', executable='gz_rover_driver', output='screen',
                  parameters=[{**common, 'world_json': inputs['world_json'],
                               'agents_file': inputs['agents_file'], 'agent_id': inputs['rover_id']}])
    vertical = IncludeLaunchDescription(PythonLaunchDescriptionSource(str(
        Path(get_package_share_directory('mge_bringup')) / 'launch' / 'vertical_mock.launch.py')),
        launch_arguments={
            'run_id': inputs['run_id'], 'agents_file': inputs['agents_file'],
            'use_sim_time': 'true', 'terrain': 'real', 'planner': 'real',
            'mission': 'mock', 'agents': 'kinematic', 'external_agents': inputs['rover_id'],
            **{name: value(name) for name in (
                'host', 'port', 'record', 'record_dir', 'profiles_file', 'exploration_policy_file',
                'allow_continuous_starts', 'allow_legacy_cost_model', 'budget_fallback', 'complete_on_return',
                'completion_tolerance_m', 'sensor', 'sensor_scene_file')},
        }.items())
    return [
        LogInfo(msg='Gazebo experimental MOCK run; SIMULATED sensing; no scientific or LIVE acceptance'),
        RegisterEventHandler(OnProcessExit(target_action=driver,
            on_exit=[EmitEvent(event=Shutdown(reason='Gazebo rover driver exited'))])),
        vertical, driver,
        Node(package='mge_sim', executable='gz_mirror', output='screen',
             parameters=[{**common, 'world_json': inputs['world_json']}]),
    ]


def _start(context):
    value = lambda name: LaunchConfiguration(name).perform(context)
    inputs = validate_inputs(value('world_sdf'), value('world_json'), value('agents_file'),
                             value('run_id'), value('rover_id'), context.environment.get('ROS_DOMAIN_ID', ''))
    for argument in ('profiles_file', 'exploration_policy_file'):
        if value(argument) and not Path(value(argument)).is_file():
            raise RuntimeError('NOT_READY: CONFIGURATION_FILE_REQUIRED: ' + argument)
    if value('sensor') == 'true' and not Path(value('sensor_scene_file')).is_file():
        raise RuntimeError('NOT_READY: SIMULATED_SENSOR_SCENE_REQUIRED')
    if value('sensor') == 'true':
        validate_sensor_scene(inputs['world_json'], value('sensor_scene_file'))
    if not shutil.which('gz'):
        raise RuntimeError('NOT_READY: GAZEBO_HARMONIC_REQUIRED')
    bridge_path = Path(get_package_prefix('ros_gz_bridge')) / 'lib/ros_gz_bridge/parameter_bridge'
    if not bridge_path.is_file() or not os.access(bridge_path, os.X_OK):
        raise RuntimeError('NOT_READY: ROS_GZ_CLOCK_BRIDGE_REQUIRED')
    _probe_clock(require_clean=True)
    command = ['gz', 'sim', '-r']
    if value('gui') == 'false':
        command.append('-s')
    command.append(inputs['world_sdf'])
    gazebo = ExecuteProcess(cmd=command, cwd=str(Path(inputs['world_sdf']).parent), output='screen')
    topic = f'/world/{inputs["world_name"]}/clock'
    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge', name='mge_gazebo_clock_bridge',
                  output='screen', arguments=[topic + '@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
                  remappings=[(topic, '/clock')], parameters=[{'use_sim_time': True}])
    return [
        SetEnvironmentVariable('GZ_PARTITION', 'mge-' + inputs['run_id']),
        RegisterEventHandler(OnProcessExit(target_action=gazebo,
            on_exit=[EmitEvent(event=Shutdown(reason='Gazebo server exited'))])),
        RegisterEventHandler(OnProcessExit(target_action=bridge,
            on_exit=[EmitEvent(event=Shutdown(reason='Gazebo clock bridge exited'))])),
        gazebo, bridge,
        TimerAction(period=0.1, actions=[OpaqueFunction(function=_consumers, args=[inputs])]),
    ]


def generate_launch_description():
    required = ('run_id', 'world_sdf', 'world_json', 'agents_file')
    defaults = {
        'rover_id': 'rover_1', 'gui': 'false', 'host': '127.0.0.1', 'port': '8000',
        'record': 'false', 'record_dir': 'evidence', 'profiles_file': '',
        'exploration_policy_file': '', 'allow_continuous_starts': 'false',
        'allow_legacy_cost_model': 'false',
        'budget_fallback': 'false', 'complete_on_return': 'false', 'completion_tolerance_m': '1.0',
        'sensor': 'false', 'sensor_scene_file': '',
    }
    booleans = {'gui', 'record', 'allow_continuous_starts', 'allow_legacy_cost_model', 'budget_fallback',
                'complete_on_return', 'sensor'}
    return LaunchDescription([
        *[DeclareLaunchArgument(name) for name in required],
        *[DeclareLaunchArgument(name, default_value=default,
              **({'choices': ['true', 'false']} if name in booleans else {}))
          for name, default in defaults.items()],
        OpaqueFunction(function=_start),
    ])
