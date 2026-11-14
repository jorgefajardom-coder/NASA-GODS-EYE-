"""Minimal end-to-end vertical with MOCK producers.

agents -> terrain meta -> mission -> planner -> gateway (REST / WebSocket).
`record:=true` also writes a replay package to <record_dir>/<run_id>.
`planner:=real profiles_file:=<json>` replaces the mock planner by mge_planning;
terrain and mission stay MOCK.
Every node except the gateway is a labelled stand-in to be replaced by the
owning module (mge_data / mge_mapping, mge_planning, mge_mission, mge_sim).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import EqualsSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    default_agents = os.path.join(
        get_package_share_directory('mge_bringup'), 'config', 'agents.yaml')
    common = {
        'run_id': LaunchConfiguration('run_id'),
        'use_sim_time': LaunchConfiguration('use_sim_time'),
    }
    with_agents = {**common, 'agents_file': LaunchConfiguration('agents_file')}
    # Terrain, agents and mission are MOCK here even with planner:=real.
    web = {**common, 'source_mode': 'MOCK'}
    return LaunchDescription([
        DeclareLaunchArgument('run_id', default_value='mock-run'),
        DeclareLaunchArgument('agents_file', default_value=default_agents),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('host', default_value='127.0.0.1'),
        DeclareLaunchArgument('port', default_value='8000'),
        DeclareLaunchArgument('planner', default_value='mock', choices=['mock', 'real']),
        DeclareLaunchArgument('profiles_file', default_value=''),
        DeclareLaunchArgument('record', default_value='false'),
        DeclareLaunchArgument('record_dir', default_value='evidence'),
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
