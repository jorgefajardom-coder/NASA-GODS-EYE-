import { describe, expect, it, vi, afterEach } from 'vitest';
import { createGatewayStore, eventsSocketUrl, gatewayBaseFrom, linkSummary } from '../src/lib/gatewayLive';

// A synthetic MOCK gateway (envelopes shaped as mge_gateway/app.py answers them); no ROS, no network.
const env = (payload: object, extra: object = {}) => ({ schema_version: '1.0.0', run_id: 'run-1', mode: 'LIVE', map_version: 1, timestamp_sim_s: 1, ...extra, ...payload });
const META = { dataset_id: 'jezero_mvp', sources: ['MRO/CTX (prior): JEZ'] };
const mission = (seq: number, state = 'PLANNING') => ({ last_event_seq: seq, mission_state: state, reason_code: '', agents: [] });
const event = (seq: number) => ({ seq, event_type: 'STATE_CHANGE', detail: `e${seq}` });

function gateway(routes: Record<string, { status?: number; body: object }>) {
  return vi.fn(async (url: string) => {
    const path = new URL(url).pathname;
    const r = routes[path];
    if (!r) throw new Error(`unexpected ${path}`);
    return { ok: (r.status ?? 200) < 400, status: r.status ?? 200, json: async () => r.body };
  });
}

class FakeSocket {
  static last: FakeSocket | null = null;
  onopen: ((e: unknown) => void) | null = null;
  onmessage: ((e: { data: unknown }) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  onclose: ((e: unknown) => void) | null = null;
  closed = false;
  constructor(public url: string) {
    FakeSocket.last = this;
  }
  close() {
    this.closed = true;
  }
  send(msg: object) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
}

const READY = {
  '/api/health': { body: env({ status: 'READY', ros_connected: true, terrain_meta_received: true }) },
  '/api/manifest': { body: env({ source_mode: 'MOCK', terrain_meta: META, agents: [] }) },
  '/api/run/run-1/snapshot': { body: env({ mission_state: mission(2), terrain_meta: META, events: [event(1), event(2)] }) },
};

const flush = () => new Promise((r) => setTimeout(r, 0));
afterEach(() => vi.useRealTimers());

describe('live gateway client', () => {
  it('accepts only http(s) gateway URLs', () => {
    expect(gatewayBaseFrom('http://127.0.0.1:8010/')).toBe('http://127.0.0.1:8010');
    expect(gatewayBaseFrom('javascript:alert(1)')).toBeNull();
    expect(gatewayBaseFrom('not a url')).toBeNull();
    expect(gatewayBaseFrom(null)).toBeNull();
    expect(eventsSocketUrl('https://gw.example', 7)).toBe('wss://gw.example/api/events?after_seq=7');
  });

  it('connects, labels a MOCK stack as MOCK (never LIVE) and streams events and states', async () => {
    const s = createGatewayStore(gateway(READY), FakeSocket as never);
    s.connect('http://127.0.0.1:8010');
    expect(s.getState().status).toBe('connecting');
    await flush();
    await flush();
    let st = s.getState();
    expect(st.status).toBe('connected');
    expect(st.runId).toBe('run-1');
    expect(st.sourceMode).toBe('MOCK');
    expect(st.label).toBe('MOCK');
    expect(st.label).not.toMatch(/LIVE/);
    expect(st.events.map((e) => e.seq)).toEqual([1, 2]);
    expect(FakeSocket.last!.url).toBe('ws://127.0.0.1:8010/api/events?after_seq=2'); // resumes after what it has

    FakeSocket.last!.onopen?.({});
    FakeSocket.last!.send(env({ type: 'event', event: event(3) }));
    FakeSocket.last!.send(env({ type: 'event', event: event(2) })); // duplicate seq: kept once
    FakeSocket.last!.send(env({ type: 'state', state: mission(3, 'BLOCKED') }));
    FakeSocket.last!.send(env({ type: 'state', state: mission(1, 'IDLE') })); // older state: dropped
    st = s.getState();
    expect(st.transport).toBe('websocket');
    expect(st.events.map((e) => e.seq)).toEqual([1, 2, 3]);
    expect(st.mission?.mission_state).toBe('BLOCKED');
  });

  it('says NOT_READY while the gateway has no active run, and does not invent one', async () => {
    const s = createGatewayStore(gateway({ '/api/health': { status: 503, body: env({ status: 'NOT_READY', reason_code: 'NO_ACTIVE_RUN' }, { mode: null, run_id: null }) } }), FakeSocket as never);
    s.connect('http://127.0.0.1:8010');
    await flush();
    const st = s.getState();
    expect(st.status).toBe('not_ready');
    expect(st.message).toBe('NO_ACTIVE_RUN');
    expect(st.runId).toBeNull();
    s.disconnect();
  });

  it('rejects another schema version and a gateway that declares itself LIVE', async () => {
    const bad = createGatewayStore(gateway({ '/api/health': { body: { schema_version: '2.0.0', status: 'READY' } } }), FakeSocket as never);
    bad.connect('http://127.0.0.1:8010');
    await flush();
    expect(bad.getState().status).toBe('error');
    expect(bad.getState().message).toMatch(/schema/);
    bad.disconnect();

    const live = createGatewayStore(gateway({ ...READY, '/api/manifest': { body: env({ source_mode: 'LIVE', terrain_meta: META }) } }), FakeSocket as never);
    live.connect('http://127.0.0.1:8010');
    await flush();
    await flush();
    expect(live.getState().status).toBe('error');
    expect(live.getState().message).toMatch(/source_mode "LIVE"/);
    live.disconnect();
  });

  it('falls back to polling the snapshot when the socket closes', async () => {
    const fetchFn = gateway(READY);
    const s = createGatewayStore(fetchFn, FakeSocket as never);
    s.connect('http://127.0.0.1:8010');
    await flush();
    await flush();
    const calls = fetchFn.mock.calls.length;
    FakeSocket.last!.onclose?.({});
    await flush();
    expect(s.getState().transport).toBe('polling');
    expect(fetchFn.mock.calls.length).toBeGreaterThan(calls);
    s.disconnect();
    expect(s.getState().status).toBe('off');
  });
});

describe('link status headline', () => {
  it('stays Offline without a gateway and follows the gateway state otherwise, never claiming LIVE', () => {
    expect(linkSummary({ status: 'off', label: 'NOT_READY', message: null })).toEqual({ text: 'Offline', detail: 'live link not available', tone: 'off' });
    expect(linkSummary({ status: 'connecting', label: 'NOT_READY', message: null }).text).toBe('Connecting');
    expect(linkSummary({ status: 'not_ready', label: 'NOT_READY', message: 'NO_ACTIVE_RUN' }).detail).toBe('ROS gateway · NO_ACTIVE_RUN');
    expect(linkSummary({ status: 'error', label: 'NOT_READY', message: 'schema 2.0.0' }).text).toBe('Link error');
    const on = linkSummary({ status: 'connected', label: 'MOCK', message: null });
    expect(on).toEqual({ text: 'Connected', detail: 'ROS gateway · MOCK', tone: 'connected' });
    expect(`${on.text} ${on.detail}`).not.toMatch(/LIVE/);
  });
});
