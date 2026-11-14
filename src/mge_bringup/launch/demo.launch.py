"""Launch scaffold processes only; this does not establish an E2E mission."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    nodes = [
        ("mge_data", "data_node"),
        ("mge_mapping", "mapping_node"),
        ("mge_planning", "planning_node"),
        ("mge_mission", "mission_node"),
        ("mge_sim", "sim_node"),
        ("mge_gateway", "gateway"),
    ]
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        LogInfo(msg="Scaffold startup only: no simulator clock, data or mission is implemented"),
        *[
            Node(
                package=package,
                executable=executable,
                output="screen",
                parameters=[{"use_sim_time": use_sim_time}],
            )
            for package, executable in nodes
        ],
    ])
