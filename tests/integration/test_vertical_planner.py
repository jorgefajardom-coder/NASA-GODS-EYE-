"""End-to-end test of the vertical with the real planner (mge_planning).

Terrain and mission are still MOCK: a synthetic flat grid where every cell is
admissible, and a goal -> route -> replan mission. So this checks that the
planner is reachable through the contract and that its answers travel intact
to the web; it says nothing about routes on Mars terrain. Profiles are the
illustrative ones in config/.
"""
import json
import os
from pathlib import Path
import signal
import subprocess

import httpx
import pytest

pytest.importorskip('rclpy', reason='Requires built ROS 2 workspace')

from tests.integration.test_vertical_mock import wait_for  # noqa: E402

RUN_ID = 'it-planner'
PORT = 8767
BASE = f'http://127.0.0.1:{PORT}'
PROFILES = Path(__file__).resolve().parents[2] / 'config' / 'planner_profiles.illustrative.json'
CELL_M = 5.0
GOAL = {
    'primary_agent_id': 'human_1',
    'base': {'x': 2.5, 'y': 2.5},            # cell centres of the 5 m mock grid
    'goal': {'x': 152.5, 'y': 202.5},        # 250 m away
    'mode': 'FAST',
    'time_budget_s': 14400.0,
    'energy_budget_wh': 1000.0,
    'oxygen_budget_l': 1000.0,
    'reserve_time_s': 600.0,
    'reserve_wh': 100.0,
    'reserve_oxygen_l': 100.0,
}


def mission():
    return httpx.get(f'{BASE}/api/run/{RUN_ID}/snapshot').json()['mission_state']


def submit(request_id, **changes):
    """Send a goal and return the mission state once it settles."""
    r = httpx.post(f'{BASE}/api/mission/goal',
                   json={**GOAL, 'request_id': request_id, **changes})
    assert r.json()['accepted'] is True, r.text

    def settled():
        ms = mission()
        return ms if ms['mission_state'] in ('READY', 'BLOCKED') else None

    return wait_for(settled, timeout_s=30.0, what=f'{request_id} to settle')


def assert_connected(path):
    """Consecutive points are neighbouring cells: no jumps, no skipped cells."""
    for a, b in zip(path, path[1:]):
        dx, dy = abs(a['x'] - b['x']), abs(a['y'] - b['y'])
        assert max(dx, dy) == pytest.approx(CELL_M) and min(dx, dy) in (
            pytest.approx(0.0), pytest.approx(CELL_M)), (a, b)


@pytest.fixture(scope='module')
def stack(planner_ready):
    proc = subprocess.Popen(
        ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}',
         f'port:={PORT}', 'planner:=real', f'profiles_file:={PROFILES}'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        wait_for(lambda: len(httpx.get(f'{BASE}/api/manifest').json().get('agents', [])) == 3,
                 what='gateway and 3 agents')
        planner_ready()
        yield
    finally:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)


def test_real_planner_route_reaches_the_web(stack):
    ms = submit('req-1')
    route = ms['active_route']
    assert ms['mission_state'] == 'READY'
    assert route['status'] == 'FEASIBLE'
    assert route['reason_code'] == 'FEASIBLE_UNDER_MODEL'      # not the mock planner
    assert route['map_version_used'] == 1
    assert ms['route_id'] == route['route_id'] != ''
    out, back = route['outbound_path'], route['return_path']
    assert (out[0]['x'], out[0]['y']) == (2.5, 2.5)
    assert (out[-1]['x'], out[-1]['y']) == (152.5, 202.5)
    assert (back[0]['x'], back[0]['y']) == (152.5, 202.5)
    assert (back[-1]['x'], back[-1]['y']) == (2.5, 2.5)
    assert_connected(out)
    assert_connected(back)
    # Reserves reported by the planner respect what the request asked to keep.
    assert route['reserve_time_s'] >= GOAL['reserve_time_s']
    assert route['reserve_wh'] >= GOAL['reserve_wh']
    assert route['reserve_oxygen_l'] >= GOAL['reserve_oxygen_l']
    assert route['travel_time_s'] > 0 and route['energy_est_wh'] > 0


def test_new_map_version_replans_with_the_real_planner(stack):
    old_route = mission()['route_id']
    obs = json.dumps({'observation_id': 'obs-1', 'run_id': RUN_ID, 'agent_id': 'drone_1',
                      'base_map_version': 1, 'source_kind': 'SIMULATED'})
    subprocess.run(
        ['ros2', 'topic', 'pub', '--once', '--qos-reliability', 'reliable', '-w', '1',
         '/mge/observations', 'mge_interfaces/msg/TerrainObservation', obs],
        check=True, capture_output=True, timeout=30)

    def replanned():
        ms = mission()
        return ms if ms['map_version'] == 2 and ms['mission_state'] in ('READY', 'BLOCKED') \
            else None

    ms = wait_for(replanned, timeout_s=40.0, what='replan on map version 2')
    assert ms['mission_state'] == 'READY', ms['active_route']
    assert ms['active_route']['map_version_used'] == 2
    assert ms['route_id'] not in ('', old_route)


def test_rover_has_no_oxygen(stack):
    ms = submit('req-rover', primary_agent_id='rover_1', base={'x': 2.5, 'y': 7.5},
                goal={'x': 102.5, 'y': 102.5}, energy_budget_wh=2000.0)
    route = ms['active_route']
    assert route['status'] == 'FEASIBLE'
    assert route['oxygen_est_l'] is None and route['reserve_oxygen_l'] is None


def test_planner_errors_stay_explicit(stack):
    ms = submit('req-off-centre', goal={'x': 150.0, 'y': 200.0})
    assert ms['mission_state'] == 'BLOCKED'
    assert (ms['active_route']['status'], ms['active_route']['reason_code']) == (
        'ERROR', 'NON_CELL_CENTER')
    assert ms['route_id'] == '' and ms['active_route']['outbound_path'] == []

    ms = submit('req-efficient', mode='EFFICIENT')
    assert ms['mission_state'] == 'BLOCKED'
    assert (ms['active_route']['status'], ms['active_route']['reason_code']) == (
        'ERROR', 'MODE_NOT_SUPPORTED')
