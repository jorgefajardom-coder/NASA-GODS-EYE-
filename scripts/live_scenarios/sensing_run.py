"""Drone scouting + astronaut sortie where only the SIMULATED scene sensor reports obstacles.

Launches the MOCK vertical stack with the estimated-terrain policy (D-EST-01),
the budget fallback and the scene_sensor node over a seeded obstacle scene. The
driver only sends the two mission goals and logs the mission events; every map
update comes from what the agents' simulated sensors see.

Run from a built, sourced workspace root:
  python3 scripts/live_scenarios/sensing_run.py <run_id> <port> <record_dir> [seed]
"""
import json, math, os, subprocess, sys, time
from pathlib import Path

import httpx, yaml

from mge_sim.obstacle_field import generate_field
from mge_sim.scene_sensing import SCENE_SCHEMA

sys.path.insert(0, os.getcwd())
from tests.integration.ground_fixture import initialize_ground_agents, observed_public_scene

RUN_ID, PORT, RECORD_DIR = sys.argv[1], int(sys.argv[2]), sys.argv[3]
SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 7
BASE = f'http://127.0.0.1:{PORT}'
ROOT = Path.cwd()
ROWS = COLS = 32
WINDOW = (4, 27, 4, 27)
HOME_RC, TARGET_RC = (12, 12), (21, 21)
AGENT_CELLS = [(12, 12), (12, 13), (13, 12)]
journal = []


def centre(rc):
    return -64.0 + (rc[1] + 0.5) * 4.0, -64.0 + (rc[0] + 0.5) * 4.0


HOME = centre(HOME_RC)


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(time.strftime('%H:%M:%S'), line, flush=True)
    journal.append({'t': time.time(), 'msg': line})


def get(path):
    return httpx.get(BASE + path, timeout=5).json()


def mission():
    return get(f'/api/run/{RUN_ID}/snapshot')['mission_state']


def wait(check, what, timeout=90.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            r = check()
            if r:
                return r
        except Exception:
            pass
        time.sleep(0.25)
    raise SystemExit(f'timed out waiting for {what}')


def agent(agent_id):
    return next(a for a in mission()['agents'] if a['agent_id'] == agent_id)


seen = 0


def follow(agent_id, timeout):
    """Log mission events until the agent is idle at home, or the mission blocks with it stopped."""
    global seen
    end = time.monotonic() + timeout
    moved = False
    while time.monotonic() < end:
        for e in get(f'/api/run/{RUN_ID}/events?after_seq={seen}')['events']:
            seen = max(seen, e['seq'])
            if e['event_type'] != 'MISSION_STATE_CHANGED' or e.get('reason_code'):
                log(f'  #{e["seq"]} {e["event_type"]} {e.get("reason_code", "")}: {(e.get("detail") or "")[:110]}')
        m, a = mission(), agent(agent_id)
        p = a['pose']['position']
        moved |= a['mode'] == 'MOVING'
        if moved and a['mode'] == 'IDLE' and math.dist((p['x'], p['y']), HOME) < 1e-3 and m['mission_state'] in ('READY', 'IDLE'):
            log(f'{agent_id} back home; map v{m["map_version"]}')
            return a
        if m['mission_state'] == 'BLOCKED' and a['mode'] != 'MOVING':
            log(f'mission BLOCKED ({m.get("reason_code")}) with {agent_id} stopped at ({p["x"]:.1f}, {p["y"]:.1f})')
            return a
        time.sleep(0.5)
    raise SystemExit(f'{agent_id} sortie did not settle')


def goal(request_id, agent_id, budgets, reserves):
    """Send a goal; returns the gateway's reason code."""
    body = {'request_id': request_id, 'primary_agent_id': agent_id, 'base': dict(zip('xy', HOME)),
            'goal': dict(zip('xy', centre(TARGET_RC))), 'mode': 'FAST', **budgets, **reserves}
    r = httpx.post(BASE + '/api/mission/goal', json=body, timeout=5).json()
    log(f'goal {request_id}: {agent_id} -> {TARGET_RC}: {r.get("reason_code")}')
    return r.get('reason_code')


def handover(request_id, agent_id, budgets, reserves, previous, tries=5):
    """The MOCK mission keeps a finished goal in force, so a map update (the drone's own report on
    landing) would send `previous` out again. Hand the mission to the next agent the moment the
    previous one is idle at home; if it already left again, wait for it and retry."""
    for attempt in range(tries):
        wait(lambda: (a := agent(previous))['mode'] == 'IDLE'
             and math.dist((a['pose']['position']['x'], a['pose']['position']['y']), HOME) < 1e-3,
             f'{previous} idle at home', 300)
        if goal(f'{request_id}-{attempt + 1}', agent_id, budgets, reserves) == 'ACCEPTED':
            return
    raise SystemExit(f'{agent_id} goal not accepted')


field = generate_field(ROWS, COLS, WINDOW, HOME_RC, TARGET_RC, protected=AGENT_CELLS, seed=SEED, rock_clusters=10)
os.makedirs(RECORD_DIR, exist_ok=True)
scene_file = Path(RECORD_DIR) / f'{RUN_ID}-scene.json'
scene_file.write_text(json.dumps({
    'schema_version': SCENE_SCHEMA, 'source_kind': 'SIMULATED', 'rows': ROWS, 'cols': COLS, 'seed': SEED,
    'note': 'Synthetic test scene (mge_sim.obstacle_field); not a NASA observation.',
    'blocked': sorted(r * COLS + c for r, c in field.blocked)}, indent=1))
surface, _ = observed_public_scene(RUN_ID, [r * COLS + c for r, c in AGENT_CELLS])
template = yaml.safe_load((ROOT / 'src/mge_bringup/config/agents_jezero.yaml').read_text())
agents_file = Path(RECORD_DIR) / f'{RUN_ID}-simulated-ground-agents.yaml'
agents_file.write_text(yaml.safe_dump(initialize_ground_agents(template, surface)))
proc = subprocess.Popen(
    ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}', f'port:={PORT}',
     'terrain:=real', 'planner:=real', 'allow_legacy_cost_model:=true', f'profiles_file:={ROOT / "config/planner_profiles.illustrative.json"}',
     f'exploration_policy_file:={ROOT / "config/exploration_policy.illustrative.json"}',
     f'agents_file:={agents_file}', 'agents:=kinematic', 'allow_continuous_starts:=true',
     'budget_fallback:=true', 'complete_on_return:=true', 'sensor:=true', f'sensor_scene_file:={scene_file}',
     'record:=true', f'record_dir:={RECORD_DIR}'],
    stdout=open(Path(RECORD_DIR) / f'{RUN_ID}-launch.log', 'w'), stderr=subprocess.STDOUT, start_new_session=True)
(Path(RECORD_DIR) / f'{RUN_ID}-launch.pid').write_text(str(proc.pid))
log(f'launch pid {proc.pid}; scene seed {SEED}: {len(field.blocked)} blocked cells, ridge gap {field.gap}')

try:
    wait(lambda: len(get('/api/manifest').get('agents', [])) == 3, 'gateway with 3 agents')
    wait(lambda: mission()['map_version'] >= 1, 'map v1')
    log('gateway ready; 15 s for the sensors to report around the idle agents')
    time.sleep(15)
    log(f'map v{mission()["map_version"]} before any sortie')

    goal('scout', 'drone_1', {'time_budget_s': 600.0, 'energy_budget_wh': 100.0},
         {'reserve_time_s': 60.0, 'reserve_wh': 10.0})
    follow('drone_1', 300)
    handover('sortie', 'human_1', {'time_budget_s': 3600.0, 'energy_budget_wh': 60.0, 'oxygen_budget_l': 4.0},
             {'reserve_time_s': 300.0, 'reserve_wh': 10.0, 'reserve_oxygen_l': 0.5}, previous='drone_1')
    h = follow('human_1', 600)
    log(f'human_1 O2 left {h.get("oxygen_remaining_l")}; final map v{mission()["map_version"]}')
    log(f'DONE; stack left running. Stop with: kill -INT -{proc.pid}')
finally:
    with open(Path(RECORD_DIR) / f'{RUN_ID}-scenario.json', 'w') as f:
        json.dump({'run_id': RUN_ID, 'source_mode': 'MOCK', 'observations': 'SIMULATED (scene_sensor)',
                   'seed': SEED, 'note': 'Synthetic scene and illustrative budgets; not a validated mission.',
                   'journal': journal}, f, indent=1)
