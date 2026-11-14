"""ROS scheduling regressions; synthetic flat grid, no mission acceptance."""
import math
from pathlib import Path
import struct
import threading
import time

import pytest

rclpy = pytest.importorskip('rclpy', reason='Requires built ROS 2 workspace')
from mge_interfaces.msg import TerrainMeta  # noqa: E402
from mge_interfaces.srv import PlanRoute  # noqa: E402
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from rclpy.parameter import Parameter  # noqa: E402
from rclpy.qos import DurabilityPolicy, QoSProfile  # noqa: E402
from sensor_msgs.msg import Image  # noqa: E402
from mge_planning import node as planning  # noqa: E402

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


def metadata(version=1):
    msg = TerrainMeta()
    msg.header.frame_id = 'map'
    msg.header.stamp.sec = version
    msg.run_id, msg.dataset_id = 'concurrency', 'synthetic-flat-test'
    msg.map_version = version
    msg.rows = msg.cols = 5
    msg.resolution_m = 4.0
    msg.nodata_value = -9999.0
    msg.crs, msg.vertical_datum = 'LOCAL_ENU_SYNTHETIC', 'illustrative'
    return msg


def request():
    msg = PlanRoute.Request()
    msg.run_id, msg.request_id = 'concurrency', 'bounded-service'
    msg.agent_id, msg.agent_kind, msg.mode = 'rover_1', 'ROVER', 'FAST'
    msg.map_version = 1
    msg.start.x = msg.start.y = msg.return_to.x = msg.return_to.y = 6.0
    msg.goal.x = msg.goal.y = 10.0
    msg.require_return = True
    msg.time_budget_s, msg.energy_budget_wh = 14400.0, 1000.0
    msg.oxygen_budget_l = msg.reserve_oxygen_l = math.nan
    return msg


def wait(client, check, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        rclpy.spin_once(client, timeout_sec=0.01)
        if check():
            return
    pytest.fail('planner concurrency deadline exceeded')


@pytest.fixture
def stack():
    rclpy.init()
    profiles = Path(__file__).resolve().parents[2] / 'config/planner_profiles.illustrative.json'
    node = planning.make_node_class()(parameter_overrides=[
        Parameter('profiles_file', value=str(profiles)),
        Parameter('allow_illustrative_profiles', value=True),
        Parameter('snapshot_contract_confirmed', value=True),
    ])
    meta = metadata()
    node.store.ingest_meta(meta)
    image = Image(header=meta.header, height=5, width=5, encoding='32FC1',
                  step=20, data=struct.pack('<25f', *([0.0] * 25)))
    node.store.ingest_image('belief', image)
    node.store.ingest_image('sigma', image)
    mask = OccupancyGrid(header=meta.header, data=[0] * 25)
    mask.info.height = mask.info.width = 5
    mask.info.resolution = 4.0
    mask.info.origin.orientation.w = 1.0
    node.store.ingest_mask('rover', mask)
    client = rclpy.create_node('planner_concurrency_probe')
    service = client.create_client(PlanRoute, '/mge/planner/plan_route')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    failures = []
    def spin():
        try:
            executor.spin()
        except Exception as error:
            failures.append(error)
    thread = threading.Thread(target=spin, daemon=True)
    thread.start()
    releases = []
    try:
        wait(client, service.service_is_ready)
        yield node, client, service, releases
    finally:
        for event in releases:
            event.set()
        executor.shutdown(timeout_sec=10)
        thread.join(timeout=10)
        node.destroy_node()
        client.destroy_node()
        rclpy.shutdown()
        assert not thread.is_alive()
        assert not failures


def test_map_callbacks_cannot_occupy_all_service_workers(stack):
    node, client, service, releases = stack
    release, entered = threading.Event(), threading.Event()
    releases.append(release)
    count = 0
    guard = threading.Lock()
    def slow_ingest(*args):
        nonlocal count
        with guard:
            count += 1
        entered.set()
        release.wait(timeout=10)
    # Hold validation before it takes the snapshot lock. Multiple ready topics
    # must not reserve all workers while one map callback is in flight.
    node._ingest = slow_ingest
    publishers = [client.create_publisher(Image, f'/mge/terrain/{name}', LATCHED)
                  for name in ('belief', 'sigma')]
    publishers += [client.create_publisher(OccupancyGrid,
                   f'/mge/terrain/traversability/{kind}', LATCHED)
                   for kind in ('human', 'rover', 'drone')]
    wait(client, lambda: all(pub.get_subscription_count() for pub in publishers))
    for pub in publishers[:2]:
        pub.publish(Image())
    for pub in publishers[2:]:
        pub.publish(OccupancyGrid())
    wait(client, entered.is_set)
    future = service.call_async(request())
    wait(client, future.done, timeout=3.0)
    assert future.result().decision.status == 'FEASIBLE'
    assert count == 1, 'ingestion callbacks consumed multiple executor workers'


def test_map_updates_during_search_still_discard_stale_routes(stack, monkeypatch):
    node, client, service, releases = stack
    entered, release = threading.Event(), threading.Event()
    updated = threading.Event()
    releases.append(release)
    original = planning.plan_route
    def paused_search(**kwargs):
        entered.set()
        assert release.wait(timeout=10)
        return original(**kwargs)
    monkeypatch.setattr(planning, 'plan_route', paused_search)
    ingest = node.store.ingest_meta
    def track_meta(msg):
        ingest(msg)
        updated.set()
    node.store.ingest_meta = track_meta
    publisher = client.create_publisher(TerrainMeta, '/mge/terrain/meta', LATCHED)
    wait(client, lambda: publisher.get_subscription_count() == 1)
    future = service.call_async(request())
    wait(client, entered.is_set)
    publisher.publish(metadata(version=2))
    wait(client, updated.is_set, timeout=3.0)
    release.set()
    wait(client, future.done)
    decision = future.result().decision
    assert decision.status == 'STALE_MAP'
    assert decision.reason_code == 'SNAPSHOT_CHANGED_DURING_SEARCH'
    assert not decision.route_id and not decision.outbound_path
