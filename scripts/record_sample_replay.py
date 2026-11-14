#!/usr/bin/env python3
"""Record the sample replay package from the MOCK vertical.

    scripts/dev.sh python3 scripts/record_sample_replay.py [run_id]

Runs goal -> route -> simulated drone observation -> replan, then validates
the package offline. Output: data/sample/replay/<run_id>. The package holds
mock data only: a synthetic flat grid and straight-line routes.
"""
import json
import os
import signal
import subprocess
import sys
import time

import httpx

from mge_gateway.replay_check import check_package

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else 'mock-vertical-001'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'sample', 'replay')
PORT = 8770
BASE = f'http://127.0.0.1:{PORT}'


def wait_for(predicate, what, timeout_s=30.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    sys.exit(f'timed out waiting for {what}')


def mission():
    return httpx.get(f'{BASE}/api/run/{RUN_ID}/snapshot').json()['mission_state']


package = os.path.join(ROOT, RUN_ID)
if os.path.exists(package):
    sys.exit(f'{package} already exists; a recorded run is never overwritten')
proc = subprocess.Popen(
    ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}',
     f'port:={PORT}', 'record:=true', f'record_dir:={ROOT}'],
    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)
try:
    wait_for(lambda: len(httpx.get(f'{BASE}/api/manifest').json()['agents']) == 3,
             'gateway and 3 agents')
    httpx.post(f'{BASE}/api/mission/goal', json={
        'request_id': 'req-1', 'primary_agent_id': 'human_1',
        'base': {'x': 0, 'y': 0}, 'goal': {'x': 300, 'y': 400}, 'mode': 'FAST',
        'time_budget_s': 14400, 'energy_budget_wh': 1000, 'oxygen_budget_l': 1000,
        'reserve_time_s': 600, 'reserve_wh': 100, 'reserve_oxygen_l': 100,
    }).raise_for_status()
    wait_for(lambda: mission()['mission_state'] == 'READY', 'first route')
    time.sleep(2.0)
    subprocess.run(
        ['ros2', 'topic', 'pub', '--once', '--qos-reliability', 'reliable', '-w', '1',
         '/mge/observations', 'mge_interfaces/msg/TerrainObservation',
         json.dumps({'observation_id': 'obs-1', 'run_id': RUN_ID, 'agent_id': 'drone_1',
                     'base_map_version': 1, 'source_kind': 'SIMULATED'})],
        check=True, capture_output=True)
    wait_for(lambda: mission()['map_version'] == 2 and mission()['mission_state'] == 'READY',
             'replan on map version 2')
    time.sleep(2.0)
finally:
    os.killpg(proc.pid, signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)

problems = check_package(package)
for p in problems:
    print(p)
sys.exit(1 if problems else print(f'OK: recorded {os.path.normpath(package)}'))
