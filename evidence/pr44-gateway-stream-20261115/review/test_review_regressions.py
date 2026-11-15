"""Independent PR44 consumer regressions. Inputs: unchanged public MOCK replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from mge_gateway.app import create_app
from mge_gateway.store import RunStore

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPLAY = ROOT / 'web/public/replay/recorded-recovery-002'
RECORDS = [json.loads(line) for line in (REPLAY / 'timeline.jsonl').read_text(encoding='utf-8').splitlines()]
STATE = next(r['state'] for r in RECORDS if r['type'] == 'state' and r['state']['active_route']['status'] == 'FEASIBLE')
METAS = {r['terrain_meta']['map_version']: r['terrain_meta'] for r in RECORDS if r['type'] == 'terrain_meta'}
EVENTS = {r['event']['seq']: r['event'] for r in RECORDS if r['type'] == 'event'}
RUN = STATE['run_id']


class Bridge:
    cors_origins = []

    def __init__(self):
        self.store = RunStore(RUN, source_mode='MOCK')
        self.on_update = None
        self.goals = []
        assert self.store.apply_meta(deepcopy(METAS[1]))
        assert self.store.apply_state(deepcopy(STATE))
        assert self.store.apply_event(deepcopy(EVENTS[1]))

    def now_s(self):
        return RECORDS[-1]['timestamp_sim_s']

    def set_goal(self, fields):
        self.goals.append(fields)
        raise AssertionError('Readonly test never calls the goal service')

    def event(self, seq):
        payload = deepcopy(EVENTS[seq])
        assert self.store.apply_event(payload)
        self.on_update('event', payload)


def test_late_sequence_two_is_not_discarded_after_sequence_three():
    bridge = Bridge()
    with TestClient(create_app(bridge)) as client:
        with client.websocket_connect('/api/events') as socket:
            first = socket.receive_json()
            assert first['event']['seq'] == 1
            assert socket.receive_json()['state'] == STATE
            bridge.event(3)
            third = socket.receive_json()
            assert third['event']['seq'] == 3
            bridge.event(2)
            bridge.event(4)  # A later marker makes loss observable without hanging.
            next_message = socket.receive_json()
            snapshot = client.get(f'/api/run/{RUN}/snapshot').json()
            app_sha = hashlib.sha256(Path(create_app.__code__.co_filename).read_bytes()).hexdigest()
            original_sha = json.loads((HERE / 'source-lock.json').read_text(encoding='utf-8'))['source_files']['src/mge_gateway/mge_gateway/app.py']['sha256']
            variant = 'original' if app_sha == original_sha else 'fixed'
            evidence = {'original_pr_head': 'ef8f3ac2b49505d1ddebe3fdc05d6b7f2e8605bf',
                        'tested_variant': variant, 'tested_app_sha256': app_sha,
                        'websocket_observed': [1, 3, next_message['event']['seq']],
                        'snapshot_retained': [e['seq'] for e in snapshot['events']],
                        'late_event_2_accepted_by_store': any(e['seq'] == 2 for e in snapshot['events'])}
            (HERE / f'late-event-{variant}-reproduction.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
            assert next_message['event']['seq'] == 2, evidence


def test_actual_metadata_push_preserves_full_xyz_headers_and_mock_source():
    bridge = Bridge()
    with TestClient(create_app(bridge)) as client:
        before = client.get(f'/api/run/{RUN}/snapshot').json()
        assert before['mission_state'] == STATE
        assert client.get('/api/manifest').json()['source_mode'] == 'MOCK'
        with client.websocket_connect('/api/events') as socket:
            socket.receive_json()
            assert socket.receive_json()['state'] == STATE
            meta = deepcopy(METAS[2])
            assert bridge.store.apply_meta(meta)
            bridge.on_update('terrain_meta', meta)
            pushed = socket.receive_json()
            assert pushed['type'] == 'terrain_meta'
            assert pushed['map_version'] == 2
            assert pushed['terrain_meta'] == meta
            after = client.get(f'/api/run/{RUN}/snapshot').json()
            assert after['mission_state'] == STATE
            assert after['mission_state']['map_version'] == 1
            assert after['terrain_meta']['map_version'] == 2
            drone = next(a for a in after['mission_state']['agents'] if a['agent_kind'] == 'DRONE')
            assert drone['pose']['position']['z'] == -2571.231201171875
            assert drone['header'] == next(a for a in STATE['agents'] if a['agent_kind'] == 'DRONE')['header']
            assert after['mission_state']['active_route']['outbound_path'] == STATE['active_route']['outbound_path']
            assert after['mission_state']['active_route']['return_path'] == STATE['active_route']['return_path']
        assert bridge.goals == []
