"""I-06: record a run of the MOCK vertical, stop every process, and check that
the replay package alone is complete and consistent."""
import json
import os
import signal
import subprocess

import httpx
import pytest

pytest.importorskip('rclpy', reason='Requires built ROS 2 workspace')

from mge_gateway.contract_replay import read_package, read_public_rasters, to_viewer
from mge_gateway.replay_check import check_package
from tests.integration.test_vertical_mock import GOAL, wait_for

RUN_ID = 'it-replay'
PORT = 8766
BASE = f'http://127.0.0.1:{PORT}'


def test_recorded_run_is_readable_without_backend(tmp_path):
    proc = subprocess.Popen(
        ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}',
         f'port:={PORT}', 'record:=true', f'record_dir:={tmp_path}'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        wait_for(lambda: len(httpx.get(f'{BASE}/api/manifest').json().get('agents', [])) == 3,
                 what='gateway and 3 agents')
        r = httpx.post(f'{BASE}/api/mission/goal', json={**GOAL, 'request_id': 'req-1'})
        assert r.json()['accepted'] is True

        def ready():
            ms = httpx.get(f'{BASE}/api/run/{RUN_ID}/snapshot').json()['mission_state']
            return ms if ms['mission_state'] == 'READY' else None

        live = wait_for(ready, what='READY')
        package = os.path.join(tmp_path, RUN_ID)

        def recorded():
            with open(os.path.join(package, 'snapshot.json'), encoding='utf-8') as f:
                ms = json.load(f)['mission_state']
            return ms and ms['route_id'] == live['route_id']

        wait_for(recorded, what='route in the recorded snapshot')

        def rasters_recorded():
            with open(os.path.join(package, 'manifest.json'), encoding='utf-8') as f:
                return json.load(f)['files'].get('public_rasters')

        # The 200 x 200 attachment is written after the batch completes; wait
        # for it rather than stopping the run first.
        wait_for(rasters_recorded, what='public rasters in the package')
    finally:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)

    # Everything is stopped: the gateway no longer answers.
    try:
        httpx.get(f'{BASE}/api/health', timeout=1.0)
        raise AssertionError('gateway still running')
    except httpx.HTTPError:
        pass

    assert check_package(package) == []
    with open(os.path.join(package, 'manifest.json'), encoding='utf-8') as f:
        manifest = json.load(f)
    assert manifest['mode'] == 'REPLAY' and manifest['recorded_from'] == 'LIVE'
    assert manifest['source_mode'] == 'MOCK'      # recorded off a running MOCK graph
    assert manifest['clock_source'] == 'system'
    assert len(manifest['agents']) == 3
    with open(os.path.join(package, 'snapshot.json'), encoding='utf-8') as f:
        snap = json.load(f)
    assert snap['mission_state']['active_route']['status'] == 'FEASIBLE'
    assert snap['mission_state']['route_id'] == live['route_id']
    assert [e['event_type'] for e in snap['events']] == [
        'GOAL_ACCEPTED', 'MISSION_STATE_CHANGED', 'ROUTE_PUBLISHED', 'MISSION_STATE_CHANGED']
    # mock_terrain publishes a flat prior and marks every cell observed, so the
    # MOCK package carries its public raster attachment and converts READY.
    assert manifest['files'].get('public_rasters') == 'public_rasters.json'
    m, records, snapshot = read_package(package)
    rasters = read_public_rasters(package, m)
    assert set(rasters['prior']) == {0.0}
    assert rasters['versions']['1']['observed'] == list(range(rasters['rows'] * rasters['cols']))
    assert to_viewer(m, records, snapshot, public_rasters=rasters)['status'] == 'READY'
