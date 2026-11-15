"""ROS side of the gateway and its launch, without a running graph.

Needs the ROS 2 Python packages (rclpy, mge_interfaces, launch_ros); skipped
where they are not installed, as in the ROS-free Python job.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip('rclpy')
pytest.importorskip('mge_interfaces')
from mge_gateway.ros_bridge import RosBridge  # noqa: E402
from mge_gateway.store import RunStore  # noqa: E402


def bridge_for(run_id):
    notified = []
    fake = SimpleNamespace(store=RunStore(run_id), notified=notified)
    fake._convert = lambda kind, msg: msg
    fake._notify = lambda kind, payload: notified.append((kind, payload['map_version']))
    return fake


def test_a_new_map_version_is_pushed_to_web_clients():
    fake = bridge_for('run-a')
    RosBridge._on_meta(fake, {'run_id': 'run-a', 'map_version': 1})
    RosBridge._on_meta(fake, {'run_id': 'run-a', 'map_version': 2})
    RosBridge._on_meta(fake, {'run_id': 'run-a', 'map_version': 1})   # older: not pushed
    RosBridge._on_meta(fake, {'run_id': 'run-b', 'map_version': 9})   # other run: not pushed
    assert fake.notified == [('terrain_meta', 1), ('terrain_meta', 2)]


def test_vertical_launch_lets_the_caller_set_the_cors_origins():
    pytest.importorskip('launch_ros')
    from launch.actions import DeclareLaunchArgument
    import importlib.util

    path = Path(__file__).resolve().parents[2] / 'src/mge_bringup/launch/vertical_mock.launch.py'
    spec = importlib.util.spec_from_file_location('vertical_mock_launch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        description = module.generate_launch_description()
    except Exception as error:  # package share not installed (workspace not sourced)
        pytest.skip(f'launch description needs the built workspace: {error}')
    names = {a.name: a for a in description.entities if isinstance(a, DeclareLaunchArgument)}
    assert 'cors_origins' in names
    default = ''.join(getattr(s, 'text', '') for s in names['cors_origins'].default_value)
    assert 'http://localhost:5173' in default and 'http://127.0.0.1:5173' in default
