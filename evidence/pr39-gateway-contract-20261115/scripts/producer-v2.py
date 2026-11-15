"""Local test harness: actual gateway API fed by public MOCK replay, never ROS."""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

HARNESS = Path(__file__).resolve().parent
ROOT = HARNESS.parents[1]
HERE = Path(tempfile.mkdtemp(prefix='cut-2-', dir=HARNESS))
sys.path[:0] = [str(HARNESS / 'python-deps'), str(ROOT / 'src/mge_gateway')]

import uvicorn
from mge_gateway.app import create_app
from mge_gateway.store import RunStore

PUBLIC = ROOT / 'web/public/replay/recorded-recovery-002'
RECORDS = [json.loads(line) for line in (PUBLIC / 'timeline.jsonl').read_text().splitlines()]
RUN = json.loads((PUBLIC / 'manifest.json').read_text())['run_id']
RESTART_RUN = RUN + '-test-restart-B'
EVENTS = {r['event']['seq']: r['event'] for r in RECORDS if r['type'] == 'event'}
STATE = next(r['state'] for r in RECORDS if r['type'] == 'state' and r['state']['active_route']['status'] == 'FEASIBLE')
INITIAL_STATE = next(r['state'] for r in RECORDS if r['type'] == 'state')
LATEST_READY = next(r['state'] for r in RECORDS if r['type'] == 'state' and r['state']['last_event_seq'] == 9 and r['state']['active_route']['status'] == 'FEASIBLE')
META = next(r['terrain_meta'] for r in RECORDS if r['type'] == 'terrain_meta' and r['terrain_meta']['map_version'] == STATE['map_version'])


def relabel(value, run):
    """Only the restart test clones identity; all coordinate/stamp bytes remain."""
    if isinstance(value, dict):
        return {k: (run if k == 'run_id' and v == RUN else relabel(v, run)) for k, v in value.items()}
    if isinstance(value, list):
        return [relabel(v, run) for v in value]
    return value


class Bridge:
    cors_origins = []

    def __init__(self, run):
        self.store = RunStore(run, source_mode='MOCK')
        self.on_update = None
        self.goals = []

    def now_s(self):
        return max(r['timestamp_sim_s'] for r in RECORDS)

    def set_goal(self, fields):
        self.goals.append(fields)
        raise AssertionError('Readonly consumer must never submit a goal')

    def activate(self, seed_event=True, initial=False):
        run = self.store.run_id
        assert self.store.apply_meta(relabel(META, run))
        assert self.store.apply_state(relabel(INITIAL_STATE if initial else STATE, run))
        if seed_event:
            assert self.store.apply_event(relabel(EVENTS[1], run))

    def event(self, seq, notify=True):
        payload = relabel(EVENTS[seq], self.store.run_id)
        if self.store.apply_event(payload) and notify and self.on_update:
            self.on_update('event', payload)


class Harness:
    def __init__(self):
        self.bridge = Bridge(RUN)
        self.app = create_app(self.bridge)
        self.context = None
        self.streams = set()
        self.requests = []
        self.messages = []
        self.controls = []
        self.bridges = [self.bridge]

    async def start(self):
        self.context = self.app.router.lifespan_context(self.app)
        await self.context.__aenter__()

    async def close_streams(self):
        for send in list(self.streams):
            try:
                await send({'type': 'websocket.close', 'code': 1012, 'reason': 'Replay-fed application restart test'})
            except (RuntimeError, OSError):
                pass

    async def reset(self, run):
        await self.close_streams()
        await self.context.__aexit__(None, None, None)
        self.bridge = Bridge(run)
        self.bridges.append(self.bridge)
        self.app = create_app(self.bridge)
        await self.start()

    async def __call__(self, scope, receive, send):
        kind = scope['type']
        if kind not in ('http', 'websocket'):
            raise AssertionError(kind)
        self.requests.append({'type': kind, 'method': scope.get('method'), 'path': scope['path'], 'query': scope['query_string'].decode()})
        app = self.app
        if kind == 'websocket':
            self.streams.add(send)

        async def traced(message):
            if message['type'] == 'websocket.send' and 'text' in message:
                self.messages.append(json.loads(message['text']))
            await send(message)

        try:
            await app(scope, receive, traced)
        finally:
            if kind == 'websocket':
                self.streams.discard(send)

    async def command_loop(self, server):
        seen = 0
        while not server.should_exit:
            path = HERE / f'control-{seen + 1}.json'
            if path.exists():
                command = json.loads(path.read_text())
                if command['id'] != seen:
                    seen = command['id']
                    op = command['op']
                    self.controls.append(command)
                    if op == 'activate':
                        self.bridge.activate(command.get('seed_event', True), command.get('initial', False))
                    elif op == 'state_ready':
                        state = relabel(STATE, self.bridge.store.run_id)
                        assert self.bridge.store.apply_state(state)
                        if self.bridge.on_update:
                            self.bridge.on_update('state', state)
                    elif op == 'state_latest_ready':
                        state = relabel(LATEST_READY, self.bridge.store.run_id)
                        assert self.bridge.store.apply_state(state)
                        if self.bridge.on_update:
                            self.bridge.on_update('state', state)
                    elif op == 'event':
                        self.bridge.event(command['seq'], command.get('notify', True))
                    elif op == 'meta':
                        selected = next(r['terrain_meta'] for r in RECORDS if r['type'] == 'terrain_meta' and r['terrain_meta']['map_version'] == command['version'])
                        assert self.bridge.store.apply_meta(relabel(selected, self.bridge.store.run_id))
                    elif op == 'close_streams':
                        await self.close_streams()
                    elif op == 'reset':
                        await self.reset(RUN if command['run'] == 'A' else RESTART_RUN)
                    elif op == 'stop':
                        server.should_exit = True
                    else:
                        raise AssertionError(op)
                    tmp = HERE / f'ack-{seen}.tmp'
                    tmp.write_text(json.dumps({'id': seen, 'run_id': self.bridge.store.run_id}))
                    os.replace(tmp, HERE / f'ack-{seen}.json')
            await asyncio.sleep(0.01)


async def main():
    for name in ('control.json', 'ack.json', 'ready.json'):
        (HERE / name).unlink(missing_ok=True)
    harness = Harness()
    await harness.start()
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(harness, host='127.0.0.1', port=port, lifespan='off', log_level='warning', ws='websockets'))
    serve = asyncio.create_task(server.serve(sockets=[sock]))
    while not server.started:
        if serve.done():
            await serve
        await asyncio.sleep(0.01)
    sources = ['src/mge_gateway/mge_gateway/app.py', 'src/mge_gateway/mge_gateway/store.py', 'web/src/lib/gatewayLive.ts', 'web/src/lib/provenance.ts']
    ready = {'base': f'http://127.0.0.1:{port}', 'mode': 'replay-fed MOCK test; no ROS graph', 'source_run_id': RUN,
             'restart_run_id': RESTART_RUN, 'restart_identity': 'Synthetic identity clone of same public recorded payloads, not another mission execution',
             'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'source_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
             'ai_usage': {'ai_assisted': True, 'tool': 'OpenAI Codex', 'scope': 'Local producer/consumer validation harness; source mission records are unchanged public MOCK replay'},
             'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
             'public_package_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in PUBLIC.iterdir() if p.is_file()},
             'expected_state': STATE, 'expected_initial_state': INITIAL_STATE, 'expected_meta': META}
    (HERE / 'ready.json').write_text(json.dumps(ready, indent=2))
    (HARNESS / 'active-output.json').write_text(json.dumps({'directory': str(HERE)}))
    print(json.dumps({'ready': ready['base'], 'mode': ready['mode']}), flush=True)
    await harness.command_loop(server)
    await serve
    await harness.context.__aexit__(None, None, None)
    report = {'requests': harness.requests, 'websocket_messages': harness.messages, 'controls': harness.controls,
              'goal_calls': sum(len(b.goals) for b in harness.bridges),
              'source_sha256_after': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}}
    (HERE / 'producer-report.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
