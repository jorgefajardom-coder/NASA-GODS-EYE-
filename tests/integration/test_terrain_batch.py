"""Real terrain providers against the real planner, over ROS.

`data_node` and `mapping_node` publish the public Jezero package; the test
checks the map batch protocol the planner requires (docs/ICD.md, section 5):
one metadata publisher, metadata and every layer of a map version under one
stamp, a new stamp per version. It then sends SIMULATED observations and asks
`mge_planning` for a route.

The observations repeat the orbital prior heights of a block of cells. They
are test inputs that exercise the plumbing, not survey results, and a route
found here is not a validated route on Mars. Profiles are the illustrative
ones in config/.
"""
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import time

import pytest

rclpy = pytest.importorskip('rclpy', reason='Requires built ROS 2 workspace')

from nav_msgs.msg import OccupancyGrid  # noqa: E402
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # noqa: E402
from sensor_msgs.msg import Image  # noqa: E402

from mge_interfaces.msg import TerrainMeta, TerrainObservation  # noqa: E402
from mge_interfaces.srv import PlanRoute  # noqa: E402

RUN_ID = 'it-terrain'
ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / 'config' / 'planner_profiles.illustrative.json'
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
RELIABLE = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
KINDS = ('human', 'rover', 'drone')
LAYERS = ('meta', 'belief', 'sigma', *KINDS)
ROWS = COLS = 32
CELL_M, ORIGIN_M = 4.0, -64.0
BLOCK = [row * COLS + col for row in range(8, 24) for col in range(8, 24)]


def centre(row, col):
    return ORIGIN_M + (col + 0.5) * CELL_M, ORIGIN_M + (row + 0.5) * CELL_M


def stamp(msg):
    return msg.header.stamp.sec, msg.header.stamp.nanosec


def floats(image):
    return struct.unpack(f'<{image.height * image.width}f', bytes(image.data))


class Probe:
    """Test-side ROS node: latest message per terrain topic, plus the clients."""

    def __init__(self):
        self.node = rclpy.create_node('terrain_batch_probe')
        self.latest = {}
        self.prior = None
        sub = self.node.create_subscription
        sub(TerrainMeta, '/mge/terrain/meta', lambda m: self.latest.update(meta=m), LATCHED)
        sub(Image, '/mge/terrain/prior', lambda m: setattr(self, 'prior', m), LATCHED)
        for name in ('belief', 'sigma'):
            sub(Image, f'/mge/terrain/{name}',
                lambda m, name=name: self.latest.update({name: m}), LATCHED)
        for kind in KINDS:
            sub(OccupancyGrid, f'/mge/terrain/traversability/{kind}',
                lambda m, kind=kind: self.latest.update({kind: m}), LATCHED)
        self.observations = self.node.create_publisher(
            TerrainObservation, '/mge/observations', RELIABLE)
        self.planner = self.node.create_client(PlanRoute, '/mge/planner/plan_route')

    def spin(self, seconds=0.1):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def wait(self, check, what, timeout_s=20.0):
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            self.spin()
            result = check()
            if result:
                return result
        raise AssertionError(f'timed out waiting for {what}')

    def batch(self, version):
        """The complete batch of one map version, once every layer shares its stamp."""
        def coherent():
            if set(self.latest) != set(LAYERS) or self.latest['meta'].map_version != version:
                return None
            stamps = {stamp(self.latest[name]) for name in LAYERS}
            return dict(self.latest) if len(stamps) == 1 else None
        return self.wait(coherent, f'coherent batch of map version {version}')

    def observe(self, observation_id, cells, elevations, base_version, run_id=RUN_ID):
        msg = TerrainObservation()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.observation_id = observation_id
        msg.run_id = run_id
        msg.agent_id = 'drone_1'
        msg.base_map_version = base_version
        msg.source_kind = TerrainObservation.SOURCE_SIMULATED
        msg.cell_indices = cells
        msg.elevation_m = elevations
        msg.sigma_m = [0.25] * len(cells)
        msg.obstacle = [TerrainObservation.OBSTACLE_FREE] * len(cells)
        self.observations.publish(msg)

    def plan(self, request_id, map_version, start, goal):
        req = PlanRoute.Request()
        req.run_id, req.request_id = RUN_ID, request_id
        req.agent_id, req.agent_kind = 'rover_1', 'ROVER'
        for name, (row, col) in (('start', start), ('goal', goal), ('return_to', start)):
            point = getattr(req, name)
            point.x, point.y = centre(row, col)
        req.require_return = True
        req.mode = 'FAST'
        req.map_version = map_version
        req.time_budget_s, req.energy_budget_wh = 14400.0, 1000.0
        req.oxygen_budget_l = req.reserve_oxygen_l = math.nan      # not a human
        self.wait(self.planner.service_is_ready, 'PlanRoute service')
        future = self.planner.call_async(req)
        self.wait(future.done, f'PlanRoute answer to {request_id}')
        return future.result().decision


@pytest.fixture(scope='module')
def probe():
    def run(package, executable, **parameters):
        args = [item for key, value in {'run_id': RUN_ID, **parameters}.items()
                for item in ('-p', f'{key}:={value}')]
        return subprocess.Popen(
            ['ros2', 'run', package, executable, '--ros-args', *args],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)

    processes = [
        run('mge_data', 'data_node'),
        run('mge_mapping', 'mapping_node', repeat_period_s=1.0),
        # This checks coherent-batch routing, not the production latency limit.
        # Keep search bounded while allowing shared CI runners scheduling slack.
        run('mge_planning', 'planning_node', profiles_file=PROFILES,
            allow_illustrative_profiles='true', snapshot_contract_confirmed='true',
            search_timeout_s=10.0),
    ]
    rclpy.init()
    probe = Probe()
    try:
        yield probe
    finally:
        probe.node.destroy_node()
        rclpy.shutdown()
        for proc in processes:
            os.killpg(proc.pid, signal.SIGINT)
        for proc in processes:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)


def test_one_metadata_publisher_and_one_stamp_per_batch(probe):
    batch = probe.batch(1)
    meta = batch['meta']
    assert probe.node.count_publishers('/mge/terrain/meta') == 1
    assert (meta.run_id, meta.dataset_id, meta.header.frame_id) == (RUN_ID, 'jezero_mvp', 'map')
    assert (meta.rows, meta.cols, meta.resolution_m) == (ROWS, COLS, CELL_M)
    assert (meta.origin_x_m, meta.origin_y_m) == (ORIGIN_M, ORIGIN_M)
    assert all('evaluation_reference' not in source for source in meta.sources)
    for name in ('belief', 'sigma'):
        assert (batch[name].encoding, batch[name].height, batch[name].width) == ('32FC1', ROWS, COLS)
    # The orbital prior is not a local observation: nothing is admissible yet.
    assert all(set(batch[kind].data) == {-1} for kind in KINDS)
    probe.wait(lambda: probe.prior, 'the immutable prior layer')
    assert floats(probe.prior) == floats(batch['belief'])


def test_batch_is_repeated_with_the_same_stamp(probe):
    first = probe.batch(1)
    probe.latest.clear()
    again = probe.batch(1)                      # a late subscriber still gets it whole
    assert stamp(again['meta']) == stamp(first['meta'])


def test_planner_accepts_the_batch_and_reports_unknown_terrain(probe):
    probe.batch(1)
    decision = probe.plan('req-unobserved', 1, (10, 10), (20, 20))
    assert decision.map_version_used == 1
    assert decision.status != 'FEASIBLE'        # no observed cell, so no route
    assert decision.reason_code not in (
        'MAP_NOT_READY', 'SNAPSHOT_INCOMPLETE', 'SNAPSHOT_CONTRACT_UNCONFIRMED',
        'PROFILE_NOT_READY', 'IMMUTABLE_BATCH_CHANGED'), decision.detail


def test_observation_makes_one_new_version_with_a_new_stamp(probe):
    first = probe.batch(1)
    heights = floats(first['belief'])
    probe.wait(lambda: probe.observations.get_subscription_count() == 1, 'mapping subscription')
    probe.observe('obs-1', BLOCK, [heights[i] for i in BLOCK], base_version=1)
    second = probe.batch(2)
    assert stamp(second['meta']) > stamp(first['meta'])
    assert floats(second['sigma'])[BLOCK[0]] == pytest.approx(0.25)
    observed = {i for i, value in enumerate(second['rover'].data) if value != -1}
    assert observed and observed <= set(BLOCK)  # nothing outside the footprint changed

    probe.observe('obs-1', BLOCK, [heights[i] for i in BLOCK], base_version=1)     # duplicate
    probe.spin(1.5)
    assert probe.batch(2)['meta'].map_version == 2
    assert stamp(probe.latest['meta']) == stamp(second['meta'])


def test_invalid_observations_are_dropped_and_the_node_survives(probe):
    probe.batch(2)
    probe.observe('obs-foreign', [0], [0.0], base_version=2, run_id='another-run')
    probe.observe('obs-outside', [ROWS * COLS], [0.0], base_version=2)
    probe.observe('obs-future', [0], [0.0], base_version=99)
    probe.spin(1.5)
    assert probe.node.count_publishers('/mge/terrain/meta') == 1      # still running
    assert probe.batch(2)['meta'].map_version == 2


def test_planner_routes_inside_the_observed_block(probe):
    batch = probe.batch(2)
    free = [i for i, value in enumerate(batch['rover'].data) if value == 0]
    assert free, 'no admissible observed cell for the rover'
    decision = probe.plan('req-observed', 2, (12, 12), (19, 19))
    assert decision.map_version_used == 2
    assert decision.status == 'FEASIBLE', (decision.reason_code, decision.detail)
    inside = {(round(x), round(y)) for x, y in (centre(i // COLS, i % COLS) for i in BLOCK)}
    for point in [*decision.outbound_path, *decision.return_path]:
        assert (round(point.x), round(point.y)) in inside
