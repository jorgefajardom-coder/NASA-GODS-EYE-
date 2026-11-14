"""Smoke launch: starts the MOCK agent publisher for the configured agents."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_agents = os.path.join(
        get_package_share_directory('mge_bringup'), 'config', 'agents.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('run_id', default_value='mock-run'),
        DeclareLaunchArgument('agents_file', default_value=default_agents),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(
            package='mge_sim',
            executable='mock_agents',
            output='screen',
            parameters=[{
                'run_id': LaunchConfiguration('run_id'),
                'agents_file': LaunchConfiguration('agents_file'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }],
        ),
    ])
