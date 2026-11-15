"""Actual data_node auxiliary topics, with the unchanged public Jezero control."""

import os
from pathlib import Path
import signal
import subprocess
import time

import numpy as np
import pytest

rclpy = pytest.importorskip("rclpy", reason="Requires ROS 2 Jazzy and a sourced workspace")
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

from mge_data.core import load_auxiliary_terrain_layers, load_public_terrain

ROOT = Path(__file__).resolve().parents[2]


def test_real_data_provider_publishes_the_bound_optional_visual_layers(tmp_path, monkeypatch):
    # A separate DDS domain keeps this static-provider test independent of other stacks.
    monkeypatch.setenv("ROS_DOMAIN_ID", "96")
    monkeypatch.setenv("ROS_LOG_DIR", str(tmp_path / "ros-logs"))
    tile = load_public_terrain(ROOT / "data/sample/manifest.json")
    aux = load_auxiliary_terrain_layers(ROOT / "data/sample/manifest.json", tile=tile, strict=True)
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
    received = {}
    rclpy.init()
    node = rclpy.create_node("auxiliary_visual_contract_probe")
    topics = {"prior": (Image, "/mge/terrain/prior"),
              "ctx": (Image, "/mge/terrain/aux/ctx_ortho"),
              "surface": (OccupancyGrid, "/mge/terrain/aux/surface_zones"),
              "geology": (OccupancyGrid, "/mge/terrain/aux/geology_zones")}
    subscriptions = [node.create_subscription(kind, topic,
                     lambda message, name=name: received.update({name: message}), qos)
                     for name, (kind, topic) in topics.items()]
    process = None
    log_path = tmp_path / "data-node.log"
    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                ["ros2", "run", "mge_data", "data_node", "--ros-args", "-p",
                 f"manifest_path:={ROOT / 'data/sample/manifest.json'}", "-p", "publish_aux_layers:=true"],
                cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
            deadline = time.monotonic() + 20
            while len(received) < len(topics) and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=.1)
                assert process.poll() is None, log_path.read_text(encoding="utf-8")
            assert set(received) == set(topics), log_path.read_text(encoding="utf-8")
            stamp = lambda msg: (msg.header.stamp.sec, msg.header.stamp.nanosec)
            assert len({stamp(msg) for msg in received.values()}) == 1
            assert all(msg.header.frame_id == tile.metadata.frame_id for msg in received.values())
            prior = received["prior"]
            assert prior.encoding == "32FC1"
            np.testing.assert_array_equal(
                np.frombuffer(bytes(prior.data), dtype="<f4").reshape(tile.prior.shape), tile.prior)
            image = received["ctx"]
            assert (image.height, image.width, image.encoding, image.step) == (32, 32, "mono8", 32)
            assert bytes(image.data) == aux.ctx_ortho_dn.tobytes()
            for name, expected in (("surface", aux.surface_zone_rviz_occupancy),
                                   ("geology", aux.geology_rviz_occupancy)):
                message = received[name]
                assert (message.info.height, message.info.width) == tile.prior.shape
                assert message.info.resolution == tile.metadata.resolution_m
                assert message.info.origin.position.x == tile.metadata.origin_x_m
                assert message.info.origin.position.y == tile.metadata.origin_y_m
                assert message.info.origin.position.z == 0.0  # Categorical XY grid, not terrain altitude.
                np.testing.assert_array_equal(np.asarray(message.data).reshape(tile.prior.shape), expected)
            assert aux.manifest["navigation_authorization"] is False
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        node.destroy_node()
        rclpy.shutdown()
