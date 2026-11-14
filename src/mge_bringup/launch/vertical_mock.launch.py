"""Minimal end-to-end vertical with MOCK producers.

agents -> terrain meta -> mission -> planner -> gateway (REST / WebSocket).
`record:=true` also writes a replay package to <record_dir>/<run_id>.
`planner:=real profiles_file:=<json>` replaces the mock planner by mge_planning;
terrain and mission stay MOCK unless `mission:=real` is selected explicitly.
The real mission needs an external /clock, use_sim_time=true and explicit
mission configuration. This synthetic vertical never establishes a LIVE mission.
Model agreement and scientific approval are never inferred from availability.
"""
import os
from pathlib import Path
from time import monotonic

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import EqualsSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _check_real_configuration(context):
    """Fail before starting nodes if a real mission lacks explicit inputs."""
    if LaunchConfiguration('mission').perform(context) != 'real':
        return False
    if LaunchConfiguration('use_sim_time').perform(context).lower() != 'true':
        raise RuntimeError('NOT_READY: REAL_MISSION_REQUIRES_SIM_TIME')
    for argument in ('mission_profiles_path', 'mission_path'):
        value = LaunchConfiguration(argument).perform(context)
        if not value or not Path(value).is_file():
            raise RuntimeError('NOT_READY: REAL_MISSION_CONFIGURATION_REQUIRED: ' + argument)
    return True


def _require_external_clock():
    """Observe a real clock message; no clock or mission provider is fabricated."""
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from rosgraph_msgs.msg import Clock

    ros_context = Context()
    rclpy.init(args=[], context=ros_context)
    probe = rclpy.create_node('mge_real_mission_preflight', context=ros_context)
    executor = SingleThreadedExecutor(context=ros_context)
    executor.add_node(probe)
    received = []
    def on_clock(message):
        if message.clock.sec >= 0 and 0 <= message.clock.nanosec < 10**9:
            received.append(True)
    subscription = probe.create_subscription(Clock, '/clock', on_clock,
        QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
    try:
        deadline = monotonic() + 2.0
        while monotonic() < deadline:
            executor.spin_once(timeout_sec=0.1)
        # Keep a bounded discovery window even if the first clock arrives early.
        # This is preflight, not a DDS lock; each run still needs its own domain.
        existing = {name for name, _ in probe.get_service_names_and_types()}
        if '/mge/mission/set_goal' in existing:
            raise RuntimeError('PROVIDER_COLLISION: mission service already active')
        if not received:
            raise RuntimeError('NOT_READY: EXTERNAL_SIMULATION_CLOCK_REQUIRED')
    finally:
        executor.shutdown(timeout_sec=2.0)
        executor.remove_node(probe)
        probe.destroy_subscription(subscription)
        probe.destroy_node()
        ros_context.shutdown()


def _real_mission_preflight(context):
    if _check_real_configuration(context):
        _require_external_clock()
    return []


def generate_launch_description():
    default_agents = os.path.join(
        get_package_share_directory('mge_bringup'), 'config', 'agents.yaml')
    common = {
        'run_id': LaunchConfiguration('run_id'),
        'use_sim_time': LaunchConfiguration('use_sim_time'),
    }
    with_agents = {**common, 'agents_file': LaunchConfiguration('agents_file')}
    return LaunchDescription([
        DeclareLaunchArgument('run_id', default_value='mock-run'),
        DeclareLaunchArgument('agents_file', default_value=default_agents),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('host', default_value='127.0.0.1'),
        DeclareLaunchArgument('port', default_value='8000'),
        DeclareLaunchArgument('planner', default_value='mock', choices=['mock', 'real']),
        DeclareLaunchArgument('profiles_file', default_value=''),
        DeclareLaunchArgument('mission', default_value='mock', choices=['mock', 'real']),
        DeclareLaunchArgument('mission_profiles_path', default_value=''),
        DeclareLaunchArgument('mission_path', default_value=''),
        DeclareLaunchArgument('base_enu_m', default_value='[]'),
        DeclareLaunchArgument('allow_illustrative', default_value='false'),
        DeclareLaunchArgument('model_agreement_confirmed', default_value='false'),
        DeclareLaunchArgument('approved_model_id', default_value=''),
        DeclareLaunchArgument('record', default_value='false'),
        DeclareLaunchArgument('record_dir', default_value='evidence'),
        OpaqueFunction(function=_real_mission_preflight),
        Node(package='mge_sim', executable='mock_agents', output='screen',
             parameters=[with_agents]),
        Node(package='mge_sim', executable='mock_terrain', output='screen',
             parameters=[common]),
        Node(package='mge_sim', executable='mock_planner', output='screen',
             condition=IfCondition(EqualsSubstitution(LaunchConfiguration('planner'), 'mock')),
             parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]),
        # planner:=real runs mge_planning against the MOCK terrain batch. The
        # profiles are illustrative and the batch contract is switched on here
        # because mock_terrain implements it; neither is a scientific approval.
        Node(package='mge_planning', executable='planning_node', output='screen',
             condition=IfCondition(EqualsSubstitution(LaunchConfiguration('planner'), 'real')),
             parameters=[{
                 'use_sim_time': LaunchConfiguration('use_sim_time'),
                 'profiles_file': LaunchConfiguration('profiles_file'),
                 'allow_illustrative_profiles': True,
                 'snapshot_contract_confirmed': True,
             }]),
        Node(package='mge_sim', executable='mock_mission', output='screen',
             condition=IfCondition(EqualsSubstitution(LaunchConfiguration('mission'), 'mock')),
             parameters=[with_agents]),
        Node(package='mge_mission', executable='mission_node', output='screen',
             condition=IfCondition(EqualsSubstitution(LaunchConfiguration('mission'), 'real')),
             parameters=[{
                 **common,
                 'profiles_path': LaunchConfiguration('mission_profiles_path'),
                 'mission_path': LaunchConfiguration('mission_path'),
                 'base_enu_m': ParameterValue(LaunchConfiguration('base_enu_m')),
                 'allow_illustrative': ParameterValue(LaunchConfiguration('allow_illustrative'), value_type=bool),
                 'model_agreement_confirmed': ParameterValue(LaunchConfiguration('model_agreement_confirmed'), value_type=bool),
                 'approved_model_id': ParameterValue(LaunchConfiguration('approved_model_id'), value_type=str),
             }]),
        Node(package='mge_gateway', executable='gateway', output='screen',
             parameters=[{
                 **common,
                 'host': LaunchConfiguration('host'),
                 'port': ParameterValue(LaunchConfiguration('port'), value_type=int),
             }]),
        Node(package='mge_gateway', executable='replay_recorder', output='screen',
             condition=IfCondition(LaunchConfiguration('record')),
             parameters=[{**common, 'record_dir': LaunchConfiguration('record_dir')}]),
    ])
