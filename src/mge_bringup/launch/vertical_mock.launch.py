"""Minimal end-to-end vertical with MOCK producers.

agents -> terrain meta -> mission -> planner -> gateway (REST / WebSocket).
`record:=true` also writes a replay package to <record_dir>/<run_id>.
`planner:=real profiles_file:=<json>` replaces the mock planner by mge_planning.
`terrain:=real` replaces the mock terrain by mge_data + mge_mapping on the public
Jezero package; it requires planner:=real and defaults to agents_jezero.yaml.
Mission and agents stay MOCK stand-ins (mge_mission, mge_sim own the real ones),
so the run is still declared MOCK whatever the selection.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import EqualsSubstitution, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _check_terrain_selection(context):
    """A straight-line mock planner on real terrain would hide unknown cells."""
    if (LaunchConfiguration('terrain').perform(context) == 'real'
            and LaunchConfiguration('planner').perform(context) != 'real'):
        raise RuntimeError('NOT_READY: REAL_TERRAIN_REQUIRES_REAL_PLANNER')
    return []


def _when(argument, value):
    return IfCondition(EqualsSubstitution(LaunchConfiguration(argument), value))


def generate_launch_description():
    config = os.path.join(get_package_share_directory('mge_bringup'), 'config')
    # Agents must sit on cell centres of the selected terrain grid.
    default_agents = PythonExpression([
        "'", os.path.join(config, 'agents_jezero.yaml'), "' if '",
        LaunchConfiguration('terrain'), "' == 'real' else '",
        os.path.join(config, 'agents.yaml'), "'"])
    common = {
        'run_id': LaunchConfiguration('run_id'),
        'use_sim_time': LaunchConfiguration('use_sim_time'),
    }
    with_agents = {**common, 'agents_file': LaunchConfiguration('agents_file')}
    # Agents and mission are MOCK in every selection, so the run is MOCK.
    web = {**common, 'source_mode': 'MOCK'}
    return LaunchDescription([
        DeclareLaunchArgument('run_id', default_value='mock-run'),
        DeclareLaunchArgument('terrain', default_value='mock', choices=['mock', 'real']),
        DeclareLaunchArgument('agents_file', default_value=default_agents),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('host', default_value='127.0.0.1'),
        DeclareLaunchArgument('port', default_value='8000'),
        DeclareLaunchArgument('planner', default_value='mock', choices=['mock', 'real']),
        DeclareLaunchArgument('profiles_file', default_value=''),
        DeclareLaunchArgument('record', default_value='false'),
        DeclareLaunchArgument('record_dir', default_value='evidence'),
        OpaqueFunction(function=_check_terrain_selection),
        Node(package='mge_sim', executable='mock_agents', output='screen',
             parameters=[with_agents]),
        Node(package='mge_sim', executable='mock_terrain', output='screen',
             condition=_when('terrain', 'mock'), parameters=[common]),
        # Exactly one terrain provider set: mapping_node alone publishes the
        # map batch (metadata included); data_node only the immutable prior.
        Node(package='mge_data', executable='data_node', output='screen',
             condition=_when('terrain', 'real'), parameters=[common]),
        Node(package='mge_mapping', executable='mapping_node', output='screen',
             condition=_when('terrain', 'real'), parameters=[common]),
        Node(package='mge_sim', executable='mock_planner', output='screen',
             condition=IfCondition(EqualsSubstitution(LaunchConfiguration('planner'), 'mock')),
             parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]),
        # planner:=real runs mge_planning against the selected terrain batch.
        # The profiles are illustrative and the batch contract is switched on
        # here because both terrain providers implement it; neither is a
        # scientific approval.
        Node(package='mge_planning', executable='planning_node', output='screen',
             condition=IfCondition(EqualsSubstitution(LaunchConfiguration('planner'), 'real')),
             parameters=[{
                 'use_sim_time': LaunchConfiguration('use_sim_time'),
                 'profiles_file': LaunchConfiguration('profiles_file'),
                 'allow_illustrative_profiles': True,
                 'snapshot_contract_confirmed': True,
             }]),
        Node(package='mge_sim', executable='mock_mission', output='screen',
             parameters=[with_agents]),
        Node(package='mge_gateway', executable='gateway', output='screen',
             parameters=[{
                 **web,
                 'host': LaunchConfiguration('host'),
                 'port': ParameterValue(LaunchConfiguration('port'), value_type=int),
             }]),
        Node(package='mge_gateway', executable='replay_recorder', output='screen',
             condition=IfCondition(LaunchConfiguration('record')),
             parameters=[{**web, 'record_dir': LaunchConfiguration('record_dir')}]),
    ])
