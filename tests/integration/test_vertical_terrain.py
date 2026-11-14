"""End-to-end vertical on the public Jezero terrain package.

`vertical_mock.launch.py terrain:=real planner:=real` runs `mge_data`,
`mge_mapping` and `mge_planning` behind the MOCK mission and agents, with the
gateway and the replay recorder. The test checks that the real map batch,
the planner's answer and the replan on a new map version reach the web
contract and the recorded package with their IDs and versions intact.

The SIMULATED observation repeats the orbital prior heights of a block of
cells. It is a test input that exercises the plumbing, not a survey result,
and the route found here is not a validated route on Mars. Agent positions
and budgets are placeholders; profiles are the illustrative ones in config/.
"""
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import time
import yaml

import httpx
import pytest

rclpy = pytest.importorskip('rclpy', reason='Requires built ROS 2 workspace')

from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # noqa: E402
from sensor_msgs.msg import Image  # noqa: E402

from mge_gateway.replay_check import check_package  # noqa: E402
from mge_interfaces.msg import TerrainObservation  # noqa: E402
from tests.integration.test_vertical_mock import wait_for  # noqa: E402
from tests.integration.ground_fixture import (  # noqa: E402
    initialize_ground_agents, observed_public_scene, simulated_ground_point)

RUN_ID = 'it-terrain-vertical'
PORT = 8768
BASE = f'http://127.0.0.1:{PORT}'
ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / 'config' / 'planner_profiles.illustrative.json'
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
RELIABLE = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
ROWS = COLS = 32
CELL_M, ORIGIN_M = 4.0, -64.0
BLOCK = [row * COLS + col for row in range(8, 24) for col in range(8, 24)]


def centre(row, col):
    return ORIGIN_M + (col + 0.5) * CELL_M, ORIGIN_M + (row + 0.5) * CELL_M


HUMAN_START = centre(12, 12)                # human_1 in agents_jezero.yaml
GOAL_CELL = centre(19, 19)
GOAL = {
    'primary_agent_id': 'human_1',
    'base': {'x': HUMAN_START[0], 'y': HUMAN_START[1]},
    'goal': {'x': GOAL_CELL[0], 'y': GOAL_CELL[1]},
    'mode': 'FAST',
    'time_budget_s': 14400.0,
    'energy_budget_wh': 1000.0,
    'oxygen_budget_l': 1000.0,
    'reserve_time_s': 600.0,
    'reserve_wh': 100.0,
    'reserve_oxygen_l': 100.0,
}


def get(path):
    r = httpx.get(f'{BASE}{path}')
    r.raise_for_status()
    return r.json()


def mission():
    return get(f'/api/run/{RUN_ID}/snapshot')['mission_state']


class Stack:
    """The launched vertical plus a test-side node that plays the drone sensor."""

    def __init__(self, record_dir):
        # Initialize the static MOCK scene, rather than projecting any live pose.
        # These same explicit SIMULATED values will be published by this fixture;
        # the production belief remains unobserved until then.
        self.surface, self.vertical_datum = observed_public_scene(RUN_ID, BLOCK)
        template = yaml.safe_load((ROOT / 'src/mge_bringup/config/agents_jezero.yaml').read_text())
        agents_file = Path(record_dir) / 'simulated-ground-agents.yaml'
        agents_file.write_text(yaml.safe_dump(initialize_ground_agents(template, self.surface)))
        self.goal = {**GOAL,
                     'base': dict(zip(('x', 'y', 'z'), simulated_ground_point(self.surface, HUMAN_START))),
                     'goal': dict(zip(('x', 'y', 'z'), simulated_ground_point(self.surface, GOAL_CELL)))}
        self.package = os.path.join(record_dir, RUN_ID)
        self.proc = subprocess.Popen(
            ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}',
             f'port:={PORT}', 'terrain:=real', 'planner:=real', f'profiles_file:={PROFILES}',
             f'agents_file:={agents_file}',
             'record:=true', f'record_dir:={record_dir}'],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        rclpy.init()
        self.node = rclpy.create_node('terrain_vertical_probe')
        self.belief = None
        self.node.create_subscription(
            Image, '/mge/terrain/belief', lambda m: setattr(self, 'belief', m), LATCHED)
        self.observations = self.node.create_publisher(
            TerrainObservation, '/mge/observations', RELIABLE)

    def spin_until(self, check, what, timeout_s=20.0):
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if check():
                return
        raise AssertionError(f'timed out waiting for {what}')

    def observe_prior_block(self, observation_id, base_version):
        self.spin_until(lambda: self.belief is not None, 'belief layer')
        self.spin_until(lambda: self.observations.get_subscription_count() >= 1,
                        'mapping_node observation subscription')
        heights = struct.unpack(f'<{ROWS * COLS}f', bytes(self.belief.data))
        # The initial scene and simulated sensor share one public vertical datum.
        assert all(heights[i] == self.surface.elevation_m.flat[i] for i in BLOCK)
        msg = TerrainObservation()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.observation_id = observation_id
        msg.run_id = RUN_ID
        msg.agent_id = 'drone_1'
        msg.base_map_version = base_version
        msg.source_kind = TerrainObservation.SOURCE_SIMULATED
        msg.cell_indices = BLOCK
        msg.elevation_m = [heights[i] for i in BLOCK]
        msg.sigma_m = [0.25] * len(BLOCK)
        msg.obstacle = [TerrainObservation.OBSTACLE_FREE] * len(BLOCK)
        self.observations.publish(msg)

    def stop(self):
        if self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGINT)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)
        if rclpy.ok():
            self.node.destroy_node()
            rclpy.shutdown()


def test_real_terrain_refuses_the_mock_planner():
    # Straight mock routes would cross unknown cells as if they were known.
    proc = subprocess.run(
        ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}-refused',
         f'port:={PORT + 100}', 'terrain:=real', 'planner:=mock'],
        cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert 'NOT_READY: REAL_TERRAIN_REQUIRES_REAL_PLANNER' in proc.stdout + proc.stderr


@pytest.fixture(scope='module')
def stack(tmp_path_factory):
    stack = Stack(str(tmp_path_factory.mktemp('replay')))
    try:
        wait_for(lambda: len(get('/api/manifest').get('agents', [])) == 3
                 and get('/api/manifest').get('terrain_meta'),
                 timeout_s=30.0, what='gateway, 3 agents and terrain metadata')
        yield stack
    finally:
        stack.stop()


def test_jezero_batch_reaches_the_gateway_as_a_mock_run(stack):
    manifest = get('/api/manifest')
    meta = manifest['terrain_meta']
    # Mission and agents are MOCK, so the whole run is MOCK despite real terrain.
    assert manifest['source_mode'] == 'MOCK'
    assert (meta['run_id'], meta['dataset_id'], meta['map_version']) == (RUN_ID, 'jezero_mvp', 1)
    assert (meta['rows'], meta['cols'], meta['resolution_m']) == (ROWS, COLS, CELL_M)
    assert (meta['origin_x_m'], meta['origin_y_m']) == (ORIGIN_M, ORIGIN_M)
    assert all('evaluation_reference' not in source for source in meta['sources'])
    # Exactly one terrain provider set: no mock terrain beside mapping_node.
    # Wait for discovery, then leave time for a second publisher to show up.
    count = lambda: stack.node.count_publishers('/mge/terrain/meta')  # noqa: E731
    stack.spin_until(lambda: count() >= 1, 'discovery of the metadata publisher')
    end = time.monotonic() + 1.0
    while time.monotonic() < end:
        rclpy.spin_once(stack.node, timeout_sec=0.1)
    assert count() == 1


def test_unobserved_terrain_is_unknown_not_infeasible(stack):
    r = httpx.post(f'{BASE}/api/mission/goal', json={**stack.goal, 'request_id': 'req-unobserved'})
    assert r.json()['accepted'] is True, r.text
    ms = wait_for(lambda: (m := mission())['mission_state'] == 'BLOCKED' and m,
                  timeout_s=30.0, what='BLOCKED on unobserved terrain')
    route = ms['active_route']
    assert route['map_version_used'] == 1
    assert route['status'] == 'UNKNOWN', (route['reason_code'], route['detail'])
    assert ms['route_id'] == '' and route['outbound_path'] == []


def test_simulated_observation_replans_on_the_new_map_version(stack):
    stack.observe_prior_block('obs-block', base_version=1)

    def replanned():
        m = mission()
        return m if m['map_version'] == 2 and m['mission_state'] in ('READY', 'BLOCKED') else None

    ms = wait_for(replanned, timeout_s=40.0, what='replan on map version 2')
    route = ms['active_route']
    assert ms['mission_state'] == 'READY', (route['status'], route['reason_code'], route['detail'])
    assert route['status'] == 'FEASIBLE'
    assert route['reason_code'] == 'FEASIBLE_UNDER_MODEL'
    assert route['map_version_used'] == 2
    assert ms['route_id'] == route['route_id'] != ''
    out, back = route['outbound_path'], route['return_path']
    assert (out[0]['x'], out[0]['y']) == HUMAN_START
    assert out[0]['z'] == simulated_ground_point(stack.surface, HUMAN_START)[2] != 0.0
    assert (out[-1]['x'], out[-1]['y']) == GOAL_CELL
    assert (back[-1]['x'], back[-1]['y']) == HUMAN_START
    # Only observed cells are admissible, so the route stays inside the block.
    inside = {(round(x), round(y)) for x, y in (centre(i // COLS, i % COLS) for i in BLOCK)}
    assert all((round(p['x']), round(p['y'])) in inside for p in out + back)
    events = get(f'/api/run/{RUN_ID}/events')['events']
    assert 'MAP_UPDATED' in {e['event_type'] for e in events}


def test_recorded_package_is_complete_after_the_run_stops(stack):
    route_id = mission()['route_id']

    def recorded():
        with open(os.path.join(stack.package, 'snapshot.json'), encoding='utf-8') as f:
            ms = json.load(f)['mission_state']
        return ms and ms['route_id'] == route_id

    wait_for(recorded, what='route in the recorded snapshot')
    stack.stop()
    assert check_package(stack.package) == []
    with open(os.path.join(stack.package, 'manifest.json'), encoding='utf-8') as f:
        manifest = json.load(f)
    assert manifest['source_mode'] == 'MOCK'
    with open(os.path.join(stack.package, 'snapshot.json'), encoding='utf-8') as f:
        snap = json.load(f)
    assert snap['terrain_meta']['dataset_id'] == 'jezero_mvp'
    assert snap['terrain_meta']['map_version'] == 2
