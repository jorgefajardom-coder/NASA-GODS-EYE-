"""Actual generated PlanRoute service over a coherent, illustrative ROS batch."""

import json
import math
import time
from threading import Thread

import pytest

pytest.importorskip("rclpy", reason="Requires ROS 2 Jazzy and a sourced workspace")
import rclpy
from builtin_interfaces.msg import Time
from mge_interfaces.msg import TerrainMeta
from mge_interfaces.srv import PlanRoute
from nav_msgs.msg import OccupancyGrid
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

from mge_planning.node import make_node_class


@pytest.fixture
def ros_pair(tmp_path):
    profiles = tmp_path / "profiles.json"
    profiles.write_text(json.dumps({"status": "illustrative", "profiles": {"rover_1": {
        "agent_kind": "rover", "speed_m_s": 1.0, "max_slope_deg": 30.0,
        "max_step_m": 1.0, "radius_m": 0.0, "localization_error_m": 0.0,
        "energy_wh_per_m": 1.0}}}))
    rclpy.init()
    planner = make_node_class()(parameter_overrides=[
        Parameter("profiles_file", value=str(profiles)),
        Parameter("allow_illustrative_profiles", value=True),
        Parameter("snapshot_contract_confirmed", value=True),
        Parameter("search_timeout_s", value=5.0),
    ])
    producer = Node("planner_contract_test")
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(planner)
    executor.add_node(producer)
    thread = Thread(target=executor.spin, daemon=True)
    thread.start()
    try:
        client = producer.create_client(PlanRoute, "/mge/planner/plan_route")
        assert client.wait_for_service(timeout_sec=10.0)
        yield planner, producer, client
    finally:
        executor.shutdown(timeout_sec=5.0)
        thread.join(timeout=5.0)
        producer.destroy_node()
        planner.destroy_node()
        rclpy.shutdown()


def request(version=1, request_id="request-1"):
    msg = PlanRoute.Request()
    msg.run_id, msg.request_id = "illustrative-ros-test", request_id
    msg.agent_id, msg.agent_kind, msg.mode = "rover_1", "ROVER", "FAST"
    msg.map_version, msg.require_return = version, True
    msg.start.x = msg.start.y = 1.5
    msg.goal.x = msg.goal.y = 3.5
    msg.return_to.x = msg.return_to.y = 1.5
    msg.time_budget_s = msg.energy_budget_wh = 100.0
    msg.oxygen_budget_l = msg.reserve_oxygen_l = float("nan")
    return msg


def call(client, message):
    future = client.call_async(message)
    deadline = time.monotonic() + 10
    while not future.done() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert future.done(), "PlanRoute response timed out"
    return future.result().decision


def publish_batch(planner, producer, version=1):
    import struct

    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
    meta_pub = producer.create_publisher(TerrainMeta, "/mge/terrain/meta", qos)
    belief_pub = producer.create_publisher(Image, "/mge/terrain/belief", qos)
    sigma_pub = producer.create_publisher(Image, "/mge/terrain/sigma", qos)
    mask_pub = producer.create_publisher(OccupancyGrid, "/mge/terrain/traversability/rover", qos)
    stamp = Time(sec=version)
    meta = TerrainMeta()
    meta.header.frame_id, meta.header.stamp = "map", stamp
    meta.run_id, meta.dataset_id = "illustrative-ros-test", "synthetic-flat"
    meta.map_version, meta.rows, meta.cols, meta.resolution_m = version, 5, 5, 1.0
    meta.crs, meta.vertical_datum = "LOCAL_ENU_SYNTHETIC", "illustrative"
    meta.nodata_value = float("nan")
    for _ in range(5):
        meta_pub.publish(meta)
        time.sleep(0.05)
    image = Image()
    image.header.frame_id, image.header.stamp = "map", stamp
    image.height = image.width = 5
    image.encoding, image.step = "32FC1", 20
    image.data = list(struct.pack("<25f", *([0.0] * 25)))
    mask = OccupancyGrid()
    mask.header.frame_id, mask.header.stamp = "map", stamp
    mask.info.height = mask.info.width = 5
    mask.info.resolution = 1.0
    mask.info.origin.orientation.w = 1.0
    mask.data = [0] * 25
    for _ in range(10):
        belief_pub.publish(image)
        sigma_pub.publish(image)
        mask_pub.publish(mask)
        time.sleep(0.05)
        if planner.store.snapshot("rover")[0] is not None:
            break
    assert planner.store.snapshot("rover")[0] is not None
    return [meta_pub, belief_pub, sigma_pub, mask_pub]


def test_ros_service_rejects_missing_data_then_serializes_a_feasible_roundtrip(ros_pair):
    planner, producer, client = ros_pair
    missing = call(client, request())
    assert missing.status == "UNKNOWN" and not missing.route_id
    publishers = publish_batch(planner, producer)
    result = call(client, request())
    assert result.status == "FEASIBLE", result.detail
    assert result.outbound_path and result.return_path
    assert result.run_id == "illustrative-ros-test"
    assert result.map_version_used == 1
    assert math.isnan(result.oxygen_est_l)
    assert result.travel_time_s > 0
    assert result.header.frame_id == "map"
    assert result.header.stamp.sec == 1
    assert result.outbound_path[0].x == 1.5
    assert result.return_path[-1].x == 1.5
    assert publishers


def test_ros_service_rejects_a_request_for_an_obsolete_map(ros_pair):
    planner, producer, client = ros_pair
    publishers = publish_batch(planner, producer, version=2)
    result = call(client, request(version=1))
    assert result.status == "STALE_MAP"
    assert not result.route_id and not result.outbound_path
    assert publishers


def test_ros_service_discards_result_if_snapshot_is_invalidated_during_search(ros_pair, monkeypatch):
    import mge_planning.node as module
    planner, producer, client = ros_pair
    publishers = publish_batch(planner, producer)
    original = module.plan_route

    def compute_then_invalidate(**kwargs):
        result = original(**kwargs)
        planner.store.invalidate()
        return result

    monkeypatch.setattr(module, "plan_route", compute_then_invalidate)
    result = call(client, request())
    assert result.status == "STALE_MAP"
    assert not result.route_id and not result.outbound_path
    assert publishers
