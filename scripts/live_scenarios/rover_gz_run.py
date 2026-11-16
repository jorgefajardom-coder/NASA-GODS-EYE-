"""Physical rover in Gazebo: rover_1 is driven by physics along the authorized routes.

Builds the Gazebo world with rover_1 as a six-wheel DiffDrive rover, opens Gazebo, launches
the MOCK vertical stack with the kinematic executor leaving rover_1 to gz_rover_driver,
the scene sensor, the budget fallback and goal completion, then sends one rover sortie and
logs the mission events and the rover's physical track. Observations are SIMULATED; the
mission is MOCK; motion comes from the Gazebo physics (DART, Mars gravity).

Run from a built, sourced workspace root:
  python3 scripts/live_scenarios/rover_gz_run.py <run_id> <port> <record_dir> [seed]
"""
import json, math, os, subprocess, sys, time
from pathlib import Path

import httpx, yaml

from mge_sim.obstacle_field import generate_field
from mge_sim.scene_sensing import SCENE_SCHEMA

sys.path.insert(0, os.getcwd())
from tests.integration.ground_fixture import initialize_ground_agents, observed_public_scene

RUN_ID, PORT, RECORD_DIR = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 7
BASE = f'http://127.0.0.1:{PORT}'
ROOT = Path.cwd()
ROWS = COLS = 32
ROVER_RC, TARGET_RC = (13, 12), (21, 21)
AGENT_CELLS = [(12, 12), (12, 13), (13, 12)]
journal, procs = [], []


def centre(rc):
    return -64.0 + (rc[1] + 0.5) * 4.0, -64.0 + (rc[0] + 0.5) * 4.0


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(time.strftime('%H:%M:%S'), line, flush=True)
    journal.append({'t': time.time(), 'msg': line})


def get(path):
    return httpx.get(BASE + path, timeout=5).json()


def mission():
    return get(f'/api/run/{RUN_ID}/snapshot')['mission_state']


def rover():
    return next(a for a in mission()['agents'] if a['agent_id'] == 'rover_1')


def wait(check, what, timeout=120.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            r = check()
            if r:
                return r
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit(f'timed out waiting for {what}')


def start(name, cmd, cwd=None, env=None):
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=open(RECORD_DIR / f'{RUN_ID}-{name}.log', 'w'),
                         stderr=subprocess.STDOUT, start_new_session=True)
    (RECORD_DIR / f'{RUN_ID}-{name}.pid').write_text(str(p.pid))
    procs.append(p)
    return p


RECORD_DIR.mkdir(parents=True, exist_ok=True)
field = generate_field(ROWS, COLS, (4, 27, 4, 27), ROVER_RC, TARGET_RC, protected=AGENT_CELLS, seed=SEED, rock_clusters=10)
scene_file = RECORD_DIR / f'{RUN_ID}-scene.json'
scene_file.write_text(json.dumps({'schema_version': SCENE_SCHEMA, 'source_kind': 'SIMULATED', 'rows': ROWS, 'cols': COLS,
                                  'seed': SEED, 'note': 'Synthetic test scene; not a NASA observation.',
                                  'blocked': sorted(r * COLS + c for r, c in field.blocked)}, indent=1))
surface, _ = observed_public_scene(RUN_ID, [r * COLS + c for r, c in AGENT_CELLS])
template = yaml.safe_load((ROOT / 'src/mge_bringup/config/agents_jezero.yaml').read_text())
agents_file = RECORD_DIR / f'{RUN_ID}-simulated-ground-agents.yaml'
agents_file.write_text(yaml.safe_dump(initialize_ground_agents(template, surface)))
world = RECORD_DIR / f'{RUN_ID}-gazebo'
subprocess.run([sys.executable, 'scripts/live_scenarios/gazebo_world.py', str(scene_file), str(agents_file),
                str(world), 'rover_1', os.environ.get('MGE_WEB_MODELS', 'web/public/assets/models')], check=True)
log(f'world built: {len(field.blocked)} blocked cells, rover_1 physical')
start('gz', ['gz', 'sim', '-r', 'world.sdf'], cwd=world, env={**os.environ, 'GZ_SIM_RESOURCE_PATH': str(world)})
time.sleep(20)
start('launch', ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}', f'port:={PORT}',
                 'terrain:=real', 'planner:=real', f'profiles_file:={ROOT / "config/planner_profiles.illustrative.json"}',
                 f'exploration_policy_file:={ROOT / "config/exploration_policy.illustrative.json"}',
                 f'agents_file:={agents_file}', 'agents:=kinematic', 'allow_continuous_starts:=true',
                 'external_agents:=rover_1', 'completion_tolerance_m:=1.0',
                 'budget_fallback:=true', 'complete_on_return:=true', 'sensor:=true', f'sensor_scene_file:={scene_file}',
                 'record:=true', f'record_dir:={RECORD_DIR}'])
start('driver', ['ros2', 'run', 'mge_sim', 'gz_rover_driver', '--ros-args', '-p', f'run_id:={RUN_ID}',
                 '-p', f'world_json:={world / "world.json"}', '-p', f'agents_file:={agents_file}'])
start('mirror', ['ros2', 'run', 'mge_sim', 'gz_mirror', '--ros-args', '-p', f'run_id:={RUN_ID}',
                 '-p', f'world_json:={world / "world.json"}'])

track, seen = [], 0
try:
    wait(lambda: len(get('/api/manifest').get('agents', [])) == 3, 'gateway with 3 agents')
    r0 = wait(lambda: (a := rover())['mode'] == 'IDLE' and a, 'rover_1 at rest in Gazebo')
    p0 = r0['pose']['position']
    log(f'rover_1 settled at ({p0["x"]:.2f}, {p0["y"]:.2f}, z {p0["z"]:.2f}); energy {r0["energy_remaining_wh"]:.0f} Wh')
    time.sleep(10)                                  # let the idle sensors report around the agents
    base = centre(ROVER_RC)
    body = {'request_id': 'rover-sortie', 'primary_agent_id': 'rover_1', 'base': dict(zip('xy', base)),
            'goal': dict(zip('xy', centre(TARGET_RC))), 'mode': 'SAFE', 'time_budget_s': 3600.0,
            'energy_budget_wh': 120.0, 'reserve_time_s': 300.0, 'reserve_wh': 20.0}
    log('goal:', httpx.post(BASE + '/api/mission/goal', json=body, timeout=5).json().get('reason_code'))
    moved, end = False, time.monotonic() + 900
    while time.monotonic() < end:
        for e in get(f'/api/run/{RUN_ID}/events?after_seq={seen}')['events']:
            seen = max(seen, e['seq'])
            if e['event_type'] != 'MISSION_STATE_CHANGED' or e.get('reason_code'):
                log(f'  #{e["seq"]} {e["event_type"]} {e.get("reason_code", "")}: {(e.get("detail") or "")[:100]}')
        m, a = mission(), rover()
        p = a['pose']['position']
        track.append((round(time.time(), 1), round(p['x'], 2), round(p['y'], 2), round(p['z'], 2), a['mode']))
        moved |= a['mode'] == 'MOVING'
        if moved and m['mission_state'] == 'IDLE' and a['mode'] == 'IDLE':
            log(f'goal completed; rover_1 at ({p["x"]:.2f}, {p["y"]:.2f}); energy {a["energy_remaining_wh"]:.1f} Wh')
            break
        if m['mission_state'] == 'BLOCKED' and a['mode'] != 'MOVING':
            log(f'mission BLOCKED ({m.get("reason_code")}) with rover_1 at ({p["x"]:.2f}, {p["y"]:.2f})')
            break
        time.sleep(1.0)
    log(f'DONE; track {len(track)} samples; processes left running for inspection')
finally:
    (RECORD_DIR / f'{RUN_ID}-scenario.json').write_text(json.dumps(
        {'run_id': RUN_ID, 'source_mode': 'MOCK', 'motion': 'Gazebo physics (rover_1), kinematic (others)',
         'observations': 'SIMULATED (scene_sensor)', 'seed': SEED, 'journal': journal, 'rover_track': track}, indent=1))
