"""Fail-closed single-profile launch; never start two mission/planner providers."""
import json
import os
from pathlib import Path

from ament_index_python.packages import get_package_prefix
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from mge_bringup.launch_profiles import validate_provider_receipt, launch_parameters


def _start(context):
    profile = LaunchConfiguration("profile").perform(context)
    path = LaunchConfiguration("approval_receipt").perform(context)
    if not path:
        raise RuntimeError("NOT_READY: explicit owner-reviewed approval_receipt required")
    receipt = json.loads(Path(path).read_text(encoding="utf-8"))
    providers = validate_provider_receipt(profile, receipt)
    run_id = LaunchConfiguration("run_id").perform(context)
    parameters = launch_parameters(profile, receipt, run_id)
    for provider in providers:
        executable = Path(get_package_prefix(provider.package)) / "lib" / provider.package / provider.executable
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise RuntimeError("NOT_READY: missing provider " + str(executable))
    # Refuse an already running provider on the same domain. This is a preflight,
    # not a DDS lock: use a dedicated ROS_DOMAIN_ID per run to prevent races.
    import rclpy
    rclpy.init()
    probe = rclpy.create_node("mge_provider_preflight")
    try:
        import time
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            rclpy.spin_once(probe, timeout_sec=0.1)
        existing = {name for name, _ in probe.get_service_names_and_types()}
        if profile != "mock" and not any(name == "/clock" for name, _ in probe.get_topic_names_and_types()):
            raise RuntimeError("NOT_READY: EXTERNAL_SIMULATION_CLOCK_REQUIRED")
        if existing & {"/mge/planner/plan_route", "/mge/mission/set_goal"}:
            raise RuntimeError("PROVIDER_COLLISION: planner/mission service already active")
    finally:
        probe.destroy_node()
        rclpy.shutdown()
    return [LogInfo(msg="Profile " + profile + "; no mission validation implied"), *[
        Node(package=p.package, executable=p.executable, output="screen", parameters=[parameters[p.role]]) for p in providers]]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("profile", default_value="mock", choices=["mock", "integration", "simulation", "live"]),
        DeclareLaunchArgument("run_id", default_value=""),
        DeclareLaunchArgument("approval_receipt", default_value=""),
        OpaqueFunction(function=_start),
    ])
