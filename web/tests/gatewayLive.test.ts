import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createGatewayStore, eventsSocketUrl, gatewayBaseFrom } from '../src/lib/gatewayLive';

// Actual canonical recorded payloads; only run identifiers, sequence and scenario fields are varied.
// These are software tests of a read-only MOCK connection, never evidence of a validated LIVE mission.
const recorded = JSON.parse(readFileSync(join(__dirname, '../public/replay/recorded-recovery-002/snapshot.json'), 'utf8'));
const initialState = readFileSync(join(__dirname, '../public/replay/recorded-recovery-002/timeline.jsonl'), 'utf8')
  .trim().split(/\r?\n/).map((line) => JSON.parse(line)).find((r) => r.type === 'state').state;
function forRun(value: any, run = 'run-1'): any {
  if (Array.isArray(value)) return value.map((v) => forRun(v, run));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, k === 'run_id' ? run : forRun(v, run)]));
  return value;
}
const env = (payload: object, extra: object = {}) => ({
  schema_version: '1.0.0', run_id: 'run-1', mode: 'LIVE', map_version: 1,
  timestamp_sim_s: recorded.timestamp_sim_s, ...extra, ...payload,
});
function mission(seq = 2, state = 'READY') {
  const m = forRun(recorded.mission_state);
  m.last_event_seq = seq; m.mission_state = state; m.map_version = 1;
  m.active_route.map_version_used = 1;
  return m;
}
function event(seq: number) {
  return { ...forRun(recorded.events[0]), seq, event_id: 'event-' + seq, detail: 'event ' + seq, map_version: 1 };
}
function meta(version = 1) {
  return { ...forRun(recorded.terrain_meta), map_version: version };
}
type Reply = { status?: number; body: any };
function ready(): Record<string, Reply> {
  return {
    '/api/health': { body: env({ status: 'READY', ros_connected: true, terrain_meta_received: true }) },
    '/api/manifest': { body: env({ source_mode: 'MOCK', terrain_meta: meta(), agents: mission().agents.map(({ agent_id, agent_kind }: any) => ({ agent_id, agent_kind })) }) },
    '/api/run/run-1/snapshot': { body: env({ mission_state: mission(), terrain_meta: meta(), events: [event(1), event(2)] }) },
  };
}
function gateway(routes: Record<string, Reply>) {
  return vi.fn(async (url: string) => {
    const path = new URL(url).pathname, r = routes[path];
    if (!r) throw new Error('unexpected ' + path);
    return { ok: (r.status ?? 200) < 400, status: r.status ?? 200, json: async () => structuredClone(r.body) };
  });
}
class FakeSocket {
  static last: FakeSocket | null = null;
  onopen: ((e: unknown) => void) | null = null;
  onmessage: ((e: { data: unknown }) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  onclose: ((e: unknown) => void) | null = null;
  closed = false;
  constructor(public url: string) { FakeSocket.last = this; }
  close() { this.closed = true; }
  send(msg: unknown) { this.onmessage?.({ data: JSON.stringify(msg) }); }
}
const stores: ReturnType<typeof createGatewayStore>[] = [];
function store(fetchFn = gateway(ready()), Socket: any = FakeSocket) {
  const s = createGatewayStore(fetchFn, Socket);
  stores.push(s); s.connect('http://127.0.0.1:8010');
  return s;
}
const flush = () => vi.advanceTimersByTimeAsync(0);
const inactive = (status = 'NOT_READY') => ({ schema_version: '1.0.0', run_id: null, mode: null, map_version: null, timestamp_sim_s: null, status, reason_code: 'NO_ACTIVE_RUN' });
beforeEach(() => { vi.useFakeTimers(); FakeSocket.last = null; });
afterEach(() => { stores.splice(0).forEach((s) => s.disconnect()); vi.useRealTimers(); });

describe('read-only gateway client', () => {
  it('restricts URLs to http(s), removes credentials/query/fragment and forms the websocket URL', () => {
    expect(gatewayBaseFrom('http://127.0.0.1:8010/')).toBe('http://127.0.0.1:8010');
    expect(gatewayBaseFrom('https://user:secret@gw.example/prefix/?token=secret#x')).toBe('https://gw.example/prefix');
    for (const v of ['javascript:alert(1)', 'file:///tmp/gw', 'not a url', null]) expect(gatewayBaseFrom(v)).toBeNull();
    expect(eventsSocketUrl('https://gw.example', 7)).toBe('wss://gw.example/api/events?after_seq=7');
  });

  it('consumes canonical headers, XYZ, resources and typed null without changing them or sending commands', async () => {
    const fetchFn = gateway(ready()), s = store(fetchFn);
    await flush();
    expect(s.getState()).toMatchObject({ status: 'connected', runId: 'run-1', sourceMode: 'MOCK', label: 'MOCK', datasetId: 'jezero_mvp', terrainVersion: 1 });
    expect(s.getState().mission).toEqual(mission());
    const drone = s.getState().mission!.agents.find((a) => a.agent_kind === 'DRONE')!;
    expect(drone.pose.position.z).toBe(-2571.231201171875);
    expect(drone.oxygen_remaining_l).toBeNull();
    expect(s.getState().events.map((e) => e.seq)).toEqual([1, 2]);
    expect(FakeSocket.last!.url).toBe('ws://127.0.0.1:8010/api/events?after_seq=2');
    expect(fetchFn.mock.calls.map(([url]) => new URL(url).pathname)).toEqual(['/api/health', '/api/manifest', '/api/run/run-1/snapshot']);
    FakeSocket.last!.send(env({ type: 'state', state: mission(3, 'BLOCKED') }));
    FakeSocket.last!.send(env({ type: 'state', state: mission(1, 'IDLE') }));
    expect(s.getState().mission!.mission_state).toBe('BLOCKED');
  });

  it.each(['/api/health', '/api/manifest', '/api/run/run-1/snapshot'])('keeps inactive %s NOT_READY and retries a complete handshake', async (path) => {
    const r = ready(); r[path] = { status: path === '/api/health' ? 200 : 503, body: inactive() };
    const s = store(gateway(r)); await flush();
    expect(s.getState()).toMatchObject({ status: 'not_ready', label: 'NOT_READY', runId: null, mission: null, message: 'NO_ACTIVE_RUN' });
    expect(FakeSocket.last).toBeNull();
    r[path] = ready()[path];
    await vi.advanceTimersByTimeAsync(3000);
    expect(s.getState().status).toBe('connected');
  });

  it.each(['/api/health', '/api/manifest', '/api/run/run-1/snapshot'])('rejects HTTP failure at %s even with a plausible body', async (path) => {
    const r = ready(); r[path].status = 500;
    const s = store(gateway(r)); await flush();
    expect(s.getState()).toMatchObject({ status: 'error', label: 'ERROR', mission: null });
    expect(s.getState().message).toContain('HTTP 500');
  });

  it('keeps ERROR different from NOT_READY, including a failed polling snapshot', async () => {
    const r = ready(), s = store(gateway(r)); await flush();
    r['/api/run/run-1/snapshot'] = { status: 503, body: inactive('ERROR') };
    FakeSocket.last!.onclose?.({}); await flush();
    expect(s.getState()).toMatchObject({ status: 'error', label: 'ERROR', mission: null, events: [] });
  });

  it.each(['schema', 'run', 'mode', 'map', 'clock'])('rejects an inconsistent snapshot envelope: %s', async (field) => {
    const r = ready(), b = r['/api/run/run-1/snapshot'].body;
    if (field === 'schema') b.schema_version = '2.0.0';
    if (field === 'run') b.run_id = 'other-run';
    if (field === 'mode') b.mode = 'REPLAY';
    if (field === 'map') b.map_version = 1.5;
    if (field === 'clock') b.timestamp_sim_s = Infinity;
    const s = store(gateway(r)); await flush();
    expect(s.getState().status).toBe('error');
    expect(s.getState().mission).toBeNull();
  });

  it.each(['LIVE', 'REAL', 'incorrect'])('rejects declarable source_mode %s and never invents LIVE', async (source) => {
    const r = ready(); r['/api/manifest'].body.source_mode = source;
    const s = store(gateway(r)); await flush();
    expect(s.getState().status).toBe('error');
    expect(s.getState().message).toContain('source_mode');
  });

  it('allows absent provenance as UNKNOWN and labels REPLAY independently', async () => {
    const r = ready(); delete r['/api/manifest'].body.source_mode;
    Object.values(r).forEach((v) => { v.body.mode = 'REPLAY'; });
    const s = store(gateway(r)); await flush();
    expect(s.getState()).toMatchObject({ status: 'connected', sourceMode: 'UNKNOWN', label: 'REPLAY · UNKNOWN' });
  });

  it.each([
    ['payload run', (m: any) => { m.run_id = 'other'; }],
    ['sequence float', (m: any) => { m.last_event_seq = 2.5; }],
    ['missing agents', (m: any) => { delete m.agents; }],
    ['agent run', (m: any) => { m.agents[0].run_id = 'other'; }],
    ['agent kind', (m: any) => { m.agents[0].agent_kind = 'SUBMARINE'; }],
    ['XYZ', (m: any) => { m.agents[0].pose.position.z = NaN; }],
    ['orientation', (m: any) => { m.agents[0].pose.orientation.w = '1'; }],
    ['velocity', (m: any) => { m.agents[0].velocity.linear = []; }],
    ['resource type', (m: any) => { m.agents[0].energy_remaining_wh = '100'; }],
    ['human oxygen', (m: any) => { m.agents.find((a: any) => a.agent_kind === 'HUMAN').oxygen_remaining_l = null; }],
    ['robot oxygen', (m: any) => { m.agents.find((a: any) => a.agent_kind === 'DRONE').oxygen_remaining_l = 0; }],
    ['frame', (m: any) => { m.agents[0].header.frame_id = 'odom'; }],
    ['stamp range', (m: any) => { m.header.stamp.sec = 2 ** 31; }],
    ['stamp nanos', (m: any) => { m.header.stamp.nanosec = 1e9; }],
    ['route identity', (m: any) => { m.active_route.run_id = 'other'; }],
    ['route agent', (m: any) => { m.active_route.agent_id = 'unknown-agent'; }],
    ['route map', (m: any) => { m.active_route.map_version_used = 0; }],
  ])('quarantines malformed mission data before the panel: %s', async (_name, change) => {
    const r = ready(); change(r['/api/run/run-1/snapshot'].body.mission_state);
    const s = store(gateway(r)); await flush();
    expect(s.getState()).toMatchObject({ status: 'error', mission: null, events: [] });
  });

  it.each([
    null, {}, env({ type: 'state' }), env({ type: 'state', state: { last_event_seq: 3 } }),
    env({ type: 'event', event: event(2.5) }), env({ type: 'event', event: event(2 ** 53) }),
    env({ type: 'state', state: mission(3) }, { run_id: 'other' }),
    env({ type: 'state', state: { ...mission(3), run_id: 'other' } }),
    env({ type: 'event', event: event(3), source_mode: 'LIVE' }),
    env({ type: 'unexpected' }),
  ])('rejects malformed or cross-run socket message %# without leaking it to UI', async (bad) => {
    const s = store(); await flush();
    const ws = FakeSocket.last!; ws.send(bad);
    expect(s.getState()).toMatchObject({ status: 'error', mission: null, events: [] });
    expect(ws.closed).toBe(true);
  });

  it('requires typed null oxygen for a feasible nonhuman route, preserving human and empty defaults', async () => {
    const r = ready(), route = r['/api/run/run-1/snapshot'].body.mission_state.active_route;
    route.agent_id = 'drone_1'; route.oxygen_est_l = 5; route.reserve_oxygen_l = 5;
    const bad = store(gateway(r)); await flush();
    expect(bad.getState().status).toBe('error');
    route.oxygen_est_l = null; route.reserve_oxygen_l = null;
    const good = store(gateway(r)); await flush();
    expect(good.getState().status).toBe('connected');
    expect(good.getState().mission!.active_route!.oxygen_est_l).toBeNull();
  });

  it('rejects reused event identities with conflicting content, while exact duplicates are idempotent', async () => {
    const s = store(); await flush();
    FakeSocket.last!.send(env({ type: 'event', event: event(2) }));
    expect(s.getState().events).toHaveLength(2);
    FakeSocket.last!.send(env({ type: 'event', event: { ...event(2), detail: 'altered' } }));
    expect(s.getState().status).toBe('error');
    const second = store(); await flush();
    FakeSocket.last!.send(env({ type: 'event', event: { ...event(3), event_id: event(2).event_id } }));
    expect(second.getState().status).toBe('error');
  });

  it('resumes at the contiguous cursor and retains late 1→3→2 delivery', async () => {
    const r = ready(); r['/api/run/run-1/snapshot'].body.events = [event(1), event(3)];
    const s = store(gateway(r)); await flush();
    expect(FakeSocket.last!.url).toContain('after_seq=1');
    FakeSocket.last!.send(env({ type: 'event', event: event(2) }));
    expect(s.getState().events.map((e) => e.seq)).toEqual([1, 2, 3]);
  });

  it('reconciles a gap below its high-water mark from a complete snapshot on disconnect', async () => {
    const r = ready(); r['/api/run/run-1/snapshot'].body.events = [event(1), event(3)];
    const s = store(gateway(r)); await flush();
    r['/api/run/run-1/snapshot'].body.events = [event(1), event(2), event(3)];
    FakeSocket.last!.onclose?.({}); await flush();
    expect(s.getState().events.map((e) => e.seq)).toEqual([1, 2, 3]);
    expect(s.getState().transport).toBe('polling');
  });

  it('keeps gap reconciliation independent of the 60-event display limit', async () => {
    const r = ready(); r['/api/run/run-1/snapshot'].body.events = Array.from({ length: 65 }, (_, i) => event(i + 1)).filter((e) => e.seq !== 2);
    const s = store(gateway(r)); await flush();
    expect(s.getState().events).toHaveLength(60);
    expect(FakeSocket.last!.url).toContain('after_seq=1');
    r['/api/run/run-1/snapshot'].body.events = Array.from({ length: 65 }, (_, i) => event(i + 1));
    FakeSocket.last!.onclose?.({}); await flush();
    expect(s.getState().status).toBe('connected');
    expect(s.getState().events[0].seq).toBe(6);
  });

  it('rediscovers run B after a gateway restart instead of polling run A forever', async () => {
    const r = ready(), fetchFn = gateway(r), s = store(fetchFn); await flush();
    r['/api/run/run-1/snapshot'] = { status: 404, body: { detail: 'Unknown run' } };
    for (const path of ['/api/health', '/api/manifest']) r[path].body = forRun(r[path].body, 'run-B');
    r['/api/run/run-B/snapshot'] = { body: forRun(ready()['/api/run/run-1/snapshot'].body, 'run-B') };
    FakeSocket.last!.onclose?.({}); await flush();
    expect(s.getState().status).toBe('error');
    await vi.advanceTimersByTimeAsync(3000);
    expect(s.getState()).toMatchObject({ status: 'connected', runId: 'run-B' });
    expect(s.getState().mission!.run_id).toBe('run-B');
    expect(FakeSocket.last!.url).toContain('after_seq=2');
  });

  it('accepts late metadata from a snapshot and a WS update without replacing mission authority', async () => {
    const r = ready();
    r['/api/health'].body.terrain_meta_received = false;
    r['/api/manifest'].body.terrain_meta = null;
    r['/api/run/run-1/snapshot'].body.map_version = 3;
    r['/api/run/run-1/snapshot'].body.terrain_meta = meta(3);
    const s = store(gateway(r)); await flush();
    expect(s.getState()).toMatchObject({ status: 'connected', datasetId: 'jezero_mvp', terrainVersion: 3 });
    expect(s.getState().mission!.map_version).toBe(1);
    FakeSocket.last!.send(env({ type: 'terrain_meta', terrain_meta: meta(4) }, { map_version: 4 }));
    expect(s.getState().terrainVersion).toBe(4);
    expect(s.getState().mission!.map_version).toBe(1);
    FakeSocket.last!.send(env({ type: 'terrain_meta', terrain_meta: meta(2) }, { map_version: 4 }));
    expect(s.getState().terrainVersion).toBe(4);
  });

  it('rebuilds a fresh authoritative view after a same-ID restart, including the ROS default route', async () => {
    const r = ready();
    Object.values(r).forEach((reply) => { reply.body.map_version = 2; });
    r['/api/manifest'].body.terrain_meta = meta(2);
    const old = mission(9); old.map_version = 2; old.active_route.map_version_used = 2;
    r['/api/run/run-1/snapshot'].body = env({ mission_state: old, terrain_meta: meta(2), events: Array.from({ length: 9 }, (_, i) => event(i + 1)) }, { map_version: 2 });
    const s = store(gateway(r)); await flush();
    const oldCallback = FakeSocket.last!.onmessage!;
    expect(s.getState().events).toHaveLength(9);
    r['/api/run/run-1/snapshot'] = { status: 503, body: inactive() };
    FakeSocket.last!.onclose?.({}); await flush();
    Object.assign(r, ready());
    r['/api/run/run-1/snapshot'].body = env({ mission_state: forRun(initialState), terrain_meta: meta(), events: [] });
    await vi.advanceTimersByTimeAsync(3000);
    expect(s.getState()).toMatchObject({ status: 'connected', runId: 'run-1', terrainVersion: 1, events: [] });
    expect(s.getState().mission).toEqual(forRun(initialState));
    expect(s.getState().mission!.last_event_seq).toBe(0);
    expect(FakeSocket.last!.url).toContain('after_seq=0');
    const rebuilt = s.getState();
    oldCallback({ data: JSON.stringify(env({ type: 'state', state: old }, { map_version: 2 })) });
    expect(s.getState()).toBe(rebuilt);
  });

  it('reconciles snapshot gaps anew when an inactive connection becomes ready', async () => {
    const r = ready(); r['/api/run/run-1/snapshot'].body.events = [event(1), event(3)];
    const s = store(gateway(r)); await flush();
    expect(FakeSocket.last!.url).toContain('after_seq=1');
    r['/api/run/run-1/snapshot'] = { status: 503, body: inactive() };
    FakeSocket.last!.onclose?.({}); await flush();
    r['/api/run/run-1/snapshot'] = { body: env({ mission_state: mission(3), terrain_meta: meta(), events: [event(1), event(2), event(3)] }) };
    await vi.advanceTimersByTimeAsync(3000);
    expect(s.getState().events.map((e) => e.seq)).toEqual([1, 2, 3]);
    expect(FakeSocket.last!.url).toContain('after_seq=3');
  });

  it('ignores an old pending HTTP response after a new connection is established', async () => {
    let active = ready();
    let release: (reply: any) => void = () => {};
    let held = false;
    const fetchFn = vi.fn(async (url: string) => {
      const path = new URL(url).pathname;
      if (path === '/api/run/run-1/snapshot' && !held) {
        held = true;
        return await new Promise<any>((resolve) => { release = resolve; });
      }
      const reply = active[path];
      return { ok: true, status: 200, json: async () => structuredClone(reply.body) };
    });
    const s = store(fetchFn); await flush();
    expect(held).toBe(true);
    active = Object.fromEntries(Object.entries(ready()).map(([path, reply]) => [path.replace('run-1', 'run-B'), { body: forRun(reply.body, 'run-B') }]));
    s.connect('http://127.0.0.1:8010'); await flush();
    expect(s.getState()).toMatchObject({ status: 'connected', runId: 'run-B' });
    const fresh = s.getState();
    release({ ok: true, status: 200, json: async () => ready()['/api/run/run-1/snapshot'].body });
    await flush();
    expect(s.getState()).toBe(fresh);
  });

  it('shows unavailable terrain when both metadata reads are absent, without inferring a raster', async () => {
    const r = ready(); r['/api/manifest'].body.terrain_meta = null; r['/api/run/run-1/snapshot'].body.terrain_meta = null;
    const s = store(gateway(r)); await flush();
    expect(s.getState()).toMatchObject({ status: 'connected', datasetId: null, terrainVersion: null });
    expect(s.getState().mission).toEqual(mission());
    expect(s.getState()).not.toHaveProperty('rasters');
  });

  it('uses newly received MOCK evidence to strengthen the provenance label', async () => {
    const r = ready(); r['/api/manifest'].body.source_mode = 'SIMULATION';
    const s = store(gateway(r)); await flush();
    expect(s.getState().label).toBe('SIMULATION · NOT VALIDATED LIVE');
    const m = meta(2); m.sources = [...m.sources, 'MOCK observation source'];
    FakeSocket.last!.send(env({ type: 'terrain_meta', terrain_meta: m }, { map_version: 2 }));
    expect(s.getState().label).toBe('MOCK');
  });

  it.each(['run', 'geometry', 'version content', 'sources'])('rejects inconsistent terrain %s', async (field) => {
    const s = store(); await flush();
    const m = meta(field === 'version content' ? 1 : 2);
    if (field === 'run') m.run_id = 'other';
    if (field === 'geometry') m.origin_x_m += 1;
    if (field === 'version content') m.sources = ['altered same version'];
    if (field === 'sources') m.sources = {};
    FakeSocket.last!.send(env({ type: 'terrain_meta', terrain_meta: m }, { map_version: 2 }));
    expect(s.getState().status).toBe('error');
  });

  it('polls without WebSocket support, and cancels in-flight callbacks/timers on disconnect', async () => {
    const fetchFn = gateway(ready()), s = store(fetchFn, null); await flush();
    expect(s.getState().transport).toBe('polling');
    const before = fetchFn.mock.calls.length; s.disconnect();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(fetchFn.mock.calls).toHaveLength(before);
    expect(s.getState()).toMatchObject({ status: 'off', mission: null });
  });
});
