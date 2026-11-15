"""MOCK kinematic execution on the public Jezero terrain, end to end.

`vertical_mock.launch.py terrain:=real planner:=real agents:=kinematic` runs
the real data, mapping and planner providers with the MOCK mission and the
MOCK kinematic executor. The test checks that the primary agent follows only
the authorized path, spends resources without replenishing them, and halts
in place, acknowledged through AgentState, when a new map version invalidates
its route.

SIMULATED observations repeat the orbital prior heights of a block of cells;
they are test inputs. Motion is constant speed derived from the planner's
estimates, not dynamics. Nothing here is a validated mission or route.
"""
import json
import math
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

from mge_gateway.contract_replay import (  # noqa: E402
    read_package, read_public_rasters, to_viewer)
from mge_gateway.replay_check import check_package  # noqa: E402
from mge_interfaces.msg import AgentState, TerrainObservation  # noqa: E402
from tests.integration.test_vertical_mock import wait_for  # noqa: E402
from tests.integration.ground_fixture import (  # noqa: E402
    initialize_ground_agents, observed_public_scene, simulated_ground_point)

RUN_ID = 'it-execution'
PORT = 8769
BASE = f'http://127.0.0.1:{PORT}'
ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / 'config' / 'planner_profiles.illustrative.json'
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
RELIABLE = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)
ROWS = COLS = 32
CELL_M, ORIGIN_M = 4.0, -64.0
BLOCK = [row * COLS + col for row in range(8, 24) for col in range(8, 24)]


def centre(row, col):
    return ORIGIN_M + (col + 0.5) * CELL_M, ORIGIN_M + (row + 0.5) * CELL_M


HOME = centre(12, 12)                       # human_1 in agents_jezero.yaml
REQUEST = {
    'primary_agent_id': 'human_1', 'base': {'x': HOME[0], 'y': HOME[1]}, 'mode': 'FAST',
    'time_budget_s': 14400.0, 'energy_budget_wh': 1000.0, 'oxygen_budget_l': 1000.0,
    'reserve_time_s': 600.0, 'reserve_wh': 100.0, 'reserve_oxygen_l': 100.0,
}


def get(path):
    r = httpx.get(f'{BASE}{path}')
    r.raise_for_status()
    return r.json()


def mission():
    return get(f'/api/run/{RUN_ID}/snapshot')['mission_state']


def rasters_cover(package, versions):
    """True once the package's raster attachment holds these map versions."""
    try:
        with open(os.path.join(package, 'manifest.json'), encoding='utf-8') as f:
            name = json.load(f)['files'].get('public_rasters')
        if name is None:
            return False
        with open(os.path.join(package, name), encoding='utf-8') as f:
            return set(versions) <= set(json.load(f)['versions'])
    except (OSError, ValueError):
        return False


def submit(request_id, goal):
    r = httpx.post(f'{BASE}/api/mission/goal', json={
        **REQUEST, 'request_id': request_id, 'goal': {'x': goal[0], 'y': goal[1]}})
    assert r.json()['accepted'] is True, r.text
    return wait_for(lambda: (m := mission())['mission_state'] in ('READY', 'BLOCKED') and m,
                    timeout_s=30.0, what=f'{request_id} to settle')


def polyline(route):
    out = [(p['x'], p['y'], p['z']) for p in route['outbound_path']]
    back = [(p['x'], p['y'], p['z']) for p in route['return_path']]
    return out + back


def on_polyline(p, points, tol=1e-5):
    for a, b in zip(points, points[1:]):
        d = [y - x for x, y in zip(a, b)]
        n2 = sum(c * c for c in d)
        t = 0.0 if n2 == 0 else sum((pi - ai) * di for pi, ai, di in zip(p, a, d)) / n2
        t = min(1.0, max(0.0, t))
        if math.dist(p, [ai + t * di for ai, di in zip(a, d)]) <= tol:
            return True
    return False


class Stack:

    def __init__(self, record_dir, extra_launch_args=()):
        # Declare initial conditions for this SIMULATED scene in the public
        # terrain datum, using the same observations the fixture publishes below.
        self.surface, self.vertical_datum = observed_public_scene(RUN_ID, BLOCK)
        template = yaml.safe_load((ROOT / 'src/mge_bringup/config/agents_jezero.yaml').read_text())
        agents_file = Path(record_dir) / 'simulated-ground-agents.yaml'
        agents_file.write_text(yaml.safe_dump(initialize_ground_agents(template, self.surface)))
        self.package = os.path.join(record_dir, RUN_ID)
        self.proc = subprocess.Popen(
            ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}',
             f'port:={PORT}', 'terrain:=real', 'planner:=real', f'profiles_file:={PROFILES}',
             f'agents_file:={agents_file}',
             'agents:=kinematic', 'allow_continuous_starts:=true',
             'record:=true', f'record_dir:={record_dir}', *extra_launch_args],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        rclpy.init()
        self.node = rclpy.create_node('execution_probe')
        self.belief = None
        self.human = []                     # every human_1 AgentState received
        self.node.create_subscription(
            Image, '/mge/terrain/belief', lambda m: setattr(self, 'belief', m), LATCHED)
        self.node.create_subscription(
            AgentState, '/mge/agents/human_1/state', self.human.append, RELIABLE)
        self.observations = self.node.create_publisher(
            TerrainObservation, '/mge/observations', QoSProfile(
                depth=10, reliability=ReliabilityPolicy.RELIABLE))

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def until(self, check, what, timeout_s=30.0):
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            result = check()
            if result:
                return result
        raise AssertionError(f'timed out waiting for {what}')

    def observe_block(self, observation_id, base_version):
        self.until(lambda: self.belief is not None, 'belief layer')
        self.until(lambda: self.observations.get_subscription_count() >= 1, 'mapping subscriber')
        heights = struct.unpack(f'<{ROWS * COLS}f', bytes(self.belief.data))
        assert all(heights[i] == self.surface.elevation_m.flat[i] for i in BLOCK)
        msg = TerrainObservation()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.observation_id, msg.run_id, msg.agent_id = observation_id, RUN_ID, 'drone_1'
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


def position(state):
    p = state.pose.position
    return (p.x, p.y, p.z)


def speed(state):
    v = state.velocity.linear
    return math.hypot(v.x, v.y, v.z)


def stamp_seconds(header):
    stamp = header['stamp'] if isinstance(header, dict) else header.stamp
    sec, ns = (stamp['sec'], stamp['nanosec']) if isinstance(stamp, dict) else (stamp.sec, stamp.nanosec)
    return sec + ns * 1e-9


def movement_costs(route):
    """Independent ledger for this service-free illustrative human request."""
    profile = json.loads(PROFILES.read_text())['profiles']['human_1']
    seconds = energy = 0.0
    for name in ('outbound_path', 'return_path'):
        points = [tuple(p[k] for k in ('x', 'y', 'z')) for p in route[name]]
        for a, b in zip(points, points[1:]):
            horizontal = math.dist(a[:2], b[:2])
            if not horizontal:
                assert a == b
                continue
            dz = b[2] - a[2]
            length = math.dist(a, b)
            uphill, downhill = max(dz, 0.0) / horizontal, max(-dz, 0.0) / horizontal
            seconds += length / profile['speed_m_s'] * (
                1 + profile.get('uphill_time_factor', 0) * uphill
                + profile.get('downhill_time_factor', 0) * downhill)
            energy += length * profile['energy_wh_per_m'] * (
                1 + profile.get('uphill_energy_factor', 0) * uphill
                + profile.get('downhill_energy_factor', 0) * downhill)
    return seconds, energy, seconds * profile['oxygen_l_per_s']


@pytest.fixture(scope='module')
def stack(tmp_path_factory, planner_ready):
    stack = Stack(str(tmp_path_factory.mktemp('replay')))
    try:
        wait_for(lambda: len(get('/api/manifest').get('agents', [])) == 3,
                 timeout_s=30.0, what='gateway and 3 agents')
        # Record version 1 before the observation supersedes its latched batch.
        wait_for(lambda: mission()['map_version'] >= 1, timeout_s=30.0, what='mission map')
        wait_for(lambda: rasters_cover(stack.package, {'1'}), timeout_s=30.0,
                 what='public rasters of map version 1')
        planner_ready()
        stack.observe_block('obs-block', base_version=1)
        wait_for(lambda: mission()['map_version'] == 2, timeout_s=30.0, what='map version 2')
        yield stack
    finally:
        stack.stop()


def test_agents_wait_idle_until_a_route_is_authorized(stack):
    stack.until(lambda: stack.human, 'human state')
    first = stack.human[-1]
    assert first.mode == AgentState.MODE_IDLE and speed(first) == 0.0
    assert position(first)[:2] == HOME
    assert position(first) == simulated_ground_point(stack.surface, HOME)
    assert stack.node.count_publishers('/mge/agents/human_1/state') == 1


def test_agent_follows_the_authorized_route_and_returns(stack):
    initial = stack.human[-1]
    ms = submit('req-short', centre(14, 12))
    assert ms['mission_state'] == 'READY', ms['active_route']
    path = polyline(ms['active_route'])
    assert path[0] == position(initial)
    start = len(stack.human)
    stack.until(lambda: any(s.mode == AgentState.MODE_MOVING for s in stack.human[start:]),
                'human moving')
    stack.until(lambda: stack.human[-1].mode == AgentState.MODE_IDLE
                and stack.human[-1].velocity.linear.x == 0.0, 'human back at base', 60.0)
    states = stack.human[start:]
    # From the first motion on; before it the agent still has its configured z.
    trip = states[next(i for i, s in enumerate(states) if s.mode == AgentState.MODE_MOVING):]
    assert all(on_polyline(position(s), path) for s in trip)
    assert position(trip[-1]) == pytest.approx(path[-1])
    assert position(trip[-1])[:2] == pytest.approx(HOME)
    moving = [s for s in trip if s.mode == AgentState.MODE_MOVING]
    assert len({round(speed(s), 6) for s in moving if speed(s) > 0}) == 1   # constant speed
    for a, b in zip(trip, trip[1:]):                     # nothing is replenished
        assert b.time_remaining_s <= a.time_remaining_s
        assert b.energy_remaining_wh <= a.energy_remaining_wh
        assert b.oxygen_remaining_l <= a.oxygen_remaining_l
    route = ms['active_route']
    assert initial.energy_remaining_wh - trip[-1].energy_remaining_wh == pytest.approx(
        route['energy_est_wh'], rel=1e-3)
    assert initial.oxygen_remaining_l - trip[-1].oxygen_remaining_l == pytest.approx(
        route['oxygen_est_l'], rel=1e-3)


def test_new_map_version_halts_then_replans_from_the_acknowledged_pose(stack):
    ms = submit('req-long', centre(19, 19))
    assert ms['mission_state'] == 'READY', ms['active_route']
    path, route_id = polyline(ms['active_route']), ms['route_id']
    start = len(stack.human)
    stack.until(lambda: any(s.mode == AgentState.MODE_MOVING and math.dist(position(s), HOME[:2]
                + (position(s)[2],)) > 6.0 for s in stack.human[start:]), 'human under way')
    stack.observe_block('obs-again', base_version=2)
    halted = stack.until(lambda: next((s for s in stack.human[start:]
                                       if s.mode == AgentState.MODE_HALTED), None),
                         'stop acknowledgement in AgentState')
    assert speed(halted) == 0.0
    assert on_polyline(position(halted), path)          # stopped on the old route
    assert position(halted) != pytest.approx(path[-1])
    m = wait_for(lambda: (x := mission())['map_version'] == 3
                 and x['mission_state'] in ('READY', 'BLOCKED') and x,
                 timeout_s=30.0, what='mission settled on map version 3')
    assert m['mission_state'] == 'READY', m['active_route']
    assert m['route_id'] and m['route_id'] != route_id
    route = m['active_route']
    assert (route['status'], route['map_version_used']) == ('FEASIBLE', 3)
    resumed_path = polyline(route)
    assert resumed_path[0] == position(halted)  # all XYZ preserved, no pose projection
    containing_centre = stack.surface.point(stack.surface.cell(position(halted)))
    assert math.dist(position(halted)[:2], containing_centre[:2]) > 1e-3
    assert abs(position(halted)[2] - containing_centre[2]) > 1e-6
    assert resumed_path[1] == containing_centre
    costs = movement_costs(route)  # Includes the explicit first connector.
    for key, value in zip(('travel_time_s', 'energy_est_wh', 'oxygen_est_l'), costs):
        assert route[key] == pytest.approx(value, rel=1e-5)
    for budget, field, reserve, cost in zip(
            ('time_budget_s', 'energy_budget_wh', 'oxygen_budget_l'),
            ('time_remaining_s', 'energy_remaining_wh', 'oxygen_remaining_l'),
            ('reserve_time_s', 'reserve_wh', 'reserve_oxygen_l'), costs):
        available = min(REQUEST[budget], getattr(halted, field))
        assert cost + REQUEST[reserve] <= available + 1e-4
        assert route[reserve] == pytest.approx(available - cost, rel=1e-5)
    events = get(f'/api/run/{RUN_ID}/events')['events']
    invalidated = next(e for e in events if e['event_type'] == 'ROUTE_INVALIDATED'
                       and e['route_id'] == route_id)
    published = next(e for e in events if e['event_type'] == 'ROUTE_PUBLISHED'
                     and e['route_id'] == m['route_id'])
    assert invalidated['seq'] < published['seq']
    invalidated_s, halted_s, published_s = (
        stamp_seconds(invalidated['header']), stamp_seconds(halted.header),
        stamp_seconds(published['header']))
    assert invalidated_s <= halted_s <= published_s
    stack.until(lambda: any(s.mode == AgentState.MODE_MOVING
                            and stamp_seconds(s.header) >= published_s for s in stack.human[start:]),
                'movement after the new route authorization')
    stopped = [s for s in stack.human[start:]
               if halted_s <= stamp_seconds(s.header) < published_s]
    assert stopped and all(position(s) == position(halted) and speed(s) == 0.0 for s in stopped)
    # Await the actual resumed trip/return rather than treating FEASIBLE as motion.
    stack.until(lambda: stack.human[-1].mode == AgentState.MODE_IDLE
                and speed(stack.human[-1]) == 0.0
                and position(stack.human[-1]) == pytest.approx(resumed_path[-1]),
                'resumed route back at base', timeout_s=120.0)
    assert position(stack.human[-1])[:2] == pytest.approx(HOME)
    after = stack.human[next(i for i, s in enumerate(stack.human) if s is halted):]
    assert any(s.mode == AgentState.MODE_MOVING for s in after)
    assert all(on_polyline(position(s), resumed_path) for s in after)
    for a, b in zip(after, after[1:]):
        assert b.time_remaining_s <= a.time_remaining_s
        assert b.energy_remaining_wh <= a.energy_remaining_wh
        assert b.oxygen_remaining_l <= a.oxygen_remaining_l
        assert b.time_remaining_s >= REQUEST['reserve_time_s']
        assert b.energy_remaining_wh >= REQUEST['reserve_wh']
        assert b.oxygen_remaining_l >= REQUEST['reserve_oxygen_l']
    for field, cost in zip(('time_remaining_s', 'energy_remaining_wh', 'oxygen_remaining_l'), costs):
        assert getattr(halted, field) - getattr(after[-1], field) == pytest.approx(cost, rel=1e-3)
    wait_for(lambda: any(a['agent_id'] == 'human_1' and a['mode'] == 'IDLE'
                        and tuple(a['pose']['position'][k] for k in ('x', 'y')) == pytest.approx(HOME)
                        for a in mission()['agents']),
             timeout_s=10.0, what='recordable final agent state at base')
    stack.replanned_route = route
    stack.halted_pose = position(halted)


def test_recorded_package_shows_the_motion(stack):
    # Stop only once every map version the mission used has its rasters.
    wait_for(lambda: rasters_cover(stack.package, {'1', '2', '3'}), timeout_s=30.0,
             what='public rasters of map versions 1-3')
    stack.stop()
    problems = check_package(stack.package)
    assert problems == [], problems
    with open(os.path.join(stack.package, 'timeline.jsonl'), encoding='utf-8') as f:
        states = [json.loads(line)['state'] for line in f if '"type": "state"' in line]
    poses = {(a['pose']['position']['x'], a['pose']['position']['y'])
             for s in states for a in s['agents'] if a['agent_id'] == 'human_1'}
    assert len(poses) > 2                               # recorded while moving
    manifest, records, snapshot = read_package(stack.package)
    rasters = read_public_rasters(stack.package, manifest)
    assert set(rasters['versions']) == {'1', '2', '3'}
    converted = to_viewer(manifest, records, snapshot, rasters)
    assert converted['status'] == 'READY'
    assert all(value is None for value in converted['rasters']['reference'])
    revised = [s for s in states if s['map_version'] == 3
               and s['route_id'] == stack.replanned_route['route_id']]
    assert revised and revised[-1]['active_route']['outbound_path'][0] == dict(zip(
        ('x', 'y', 'z'), stack.halted_pose))
    active_humans = [a for s in revised for a in s['agents'] if a['agent_id'] == 'human_1']
    assert any(a['mode'] == 'MOVING' for a in active_humans)
    assert active_humans[-1]['mode'] == 'IDLE'
    assert tuple(active_humans[-1]['pose']['position'][k] for k in ('x', 'y')) == pytest.approx(HOME)
