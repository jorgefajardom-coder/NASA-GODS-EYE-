import { useSyncExternalStore } from 'react';
import type { MissionEvent, MissionState } from '../types/icd';
import { displayState, resolveSourceMode, type SourceMode } from './provenance';

/**
 * Read-only client of a running ROS gateway (docs/ICD.md section 6.1): health, manifest, snapshot and the
 * `/api/events` WebSocket, with snapshot polling when the socket fails. Opt-in: nothing is requested until
 * `connect()` (the page asks only with `?gateway=<url>`). It never sends goals and never labels data LIVE by
 * itself: the label comes from the gateway's `source_mode` through the viewer's provenance rules, so a MOCK
 * stack shows MOCK and a source that is not a validated real one never shows LIVE.
 */

export const GATEWAY_SCHEMA = '1.0.0';
const POLL_MS = 2000;
const RETRY_MS = 3000;
const KEEP_EVENTS = 60;

export type GatewayStatus = 'off' | 'connecting' | 'connected' | 'not_ready' | 'error';

export interface GatewayLiveState {
  status: GatewayStatus;
  base: string | null;
  /** Why it is not connected (NOT_READY reason, error), for the panel. */
  message: string | null;
  runId: string | null;
  sourceMode: SourceMode | null;
  /** Provenance label from displayState (MOCK, SIMULATION · NOT VALIDATED LIVE, NOT_READY...). */
  label: string;
  datasetId: string | null;
  mission: MissionState | null;
  /** Newest events first is the panel's job; kept here in sequence order, the last KEEP_EVENTS. */
  events: MissionEvent[];
  transport: 'websocket' | 'polling' | null;
  /** Wall-clock time of the last message (ms), for "updated n s ago". */
  updatedAt: number | null;
}

/**
 * Headline of the viewer's link status (top right) from the gateway store. Connected means a running gateway
 * answers, labelled with its own provenance (a MOCK stack says MOCK); it never claims a validated live mission,
 * and the replay on screen stays a replay.
 */
export function linkSummary(s: Pick<GatewayLiveState, 'status' | 'label' | 'message'>): { text: string; detail: string; tone: GatewayStatus } {
  switch (s.status) {
    case 'connected':
      return { text: 'Connected', detail: `ROS gateway · ${s.label}`, tone: 'connected' };
    case 'connecting':
      return { text: 'Connecting', detail: 'ROS gateway', tone: 'connecting' };
    case 'not_ready':
      return { text: 'Not ready', detail: `ROS gateway · ${s.message ?? 'NOT_READY'}`, tone: 'not_ready' };
    case 'error':
      return { text: 'Link error', detail: `ROS gateway · ${s.message ?? 'error'}`, tone: 'error' };
    default:
      return { text: 'Offline', detail: 'live link not available', tone: 'off' };
  }
}

const OFF: GatewayLiveState = { status: 'off', base: null, message: null, runId: null, sourceMode: null, label: 'NOT_READY', datasetId: null, mission: null, events: [], transport: null, updatedAt: null };

type FetchLike = (url: string) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;
interface SocketLike {
  onopen: ((e: unknown) => void) | null;
  onmessage: ((e: { data: unknown }) => void) | null;
  onerror: ((e: unknown) => void) | null;
  onclose: ((e: unknown) => void) | null;
  close(): void;
}
type SocketCtor = new (url: string) => SocketLike;

/** The gateway's base URL from `?gateway=`, only http(s) and without a trailing slash; null otherwise. */
export function gatewayBaseFrom(param: string | null): string | null {
  if (!param) return null;
  try {
    const u = new URL(param);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
    return `${u.origin}${u.pathname.replace(/\/+$/, '')}`;
  } catch {
    return null;
  }
}

/** ws:// or wss:// URL of the event stream for an http(s) base. */
export function eventsSocketUrl(base: string, afterSeq: number): string {
  return `${base.replace(/^http/, 'ws')}/api/events?after_seq=${afterSeq}`;
}

type Envelope = Record<string, unknown> & { schema_version?: unknown; status?: unknown; reason_code?: unknown };

export function createGatewayStore(fetchFn: FetchLike, Socket: SocketCtor | null, now: () => number = Date.now) {
  let state: GatewayLiveState = OFF;
  let socket: SocketLike | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let session = 0;
  const listeners = new Set<() => void>();
  const set = (patch: Partial<GatewayLiveState>) => {
    state = { ...state, ...patch };
    listeners.forEach((l) => l());
  };

  const lastSeq = () => (state.events.length ? state.events[state.events.length - 1].seq : 0);

  function addEvents(events: MissionEvent[]) {
    if (!events.length) return;
    const bySeq = new Map(state.events.map((e) => [e.seq, e]));
    for (const e of events) if (Number.isFinite(e?.seq) && e.seq > 0) bySeq.set(e.seq, e);
    set({ events: [...bySeq.values()].sort((a, b) => a.seq - b.seq).slice(-KEEP_EVENTS), updatedAt: now() });
  }

  function applyState(mission: MissionState | null | undefined) {
    if (!mission) return;
    // A state older than the one held is dropped, as the gateway's own store does (last_event_seq).
    if (state.mission && mission.last_event_seq < state.mission.last_event_seq) return;
    set({ mission, updatedAt: now() });
  }

  async function getJson(path: string): Promise<{ status: number; body: Envelope }> {
    const res = await fetchFn(`${state.base}${path}`);
    const body = (await res.json()) as Envelope;
    if (body?.schema_version !== GATEWAY_SCHEMA) throw new Error(`Unsupported gateway schema ${String(body?.schema_version)} (expected ${GATEWAY_SCHEMA})`);
    return { status: res.status, body };
  }

  const notReady = (body: Envelope) => body.status === 'NOT_READY' || body.status === 'ERROR';

  function schedule(fn: () => void, ms: number, mine: number) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      if (mine === session) fn();
    }, ms);
  }

  async function poll(mine: number) {
    try {
      const { body } = await getJson(`/api/run/${encodeURIComponent(state.runId ?? '')}/snapshot`);
      if (mine !== session) return;
      if (notReady(body)) {
        set({ status: 'not_ready', message: String(body.reason_code ?? 'NOT_READY') });
      } else {
        applyState(body.mission_state as MissionState);
        addEvents((body.events as MissionEvent[]) ?? []);
        set({ status: 'connected', message: null, transport: 'polling' });
      }
    } catch (e) {
      if (mine !== session) return;
      set({ status: 'error', message: e instanceof Error ? e.message : 'Gateway unreachable' });
    }
    schedule(() => void poll(mine), POLL_MS, mine);
  }

  function openSocket(mine: number) {
    if (!Socket || !state.base) return void poll(mine);
    let opened = false;
    try {
      socket = new Socket(eventsSocketUrl(state.base, lastSeq()));
    } catch {
      return void poll(mine);
    }
    socket.onopen = () => {
      opened = true;
      if (mine === session) set({ transport: 'websocket' });
    };
    socket.onmessage = (e) => {
      if (mine !== session) return;
      let msg: Envelope;
      try {
        msg = JSON.parse(String(e.data)) as Envelope;
      } catch {
        return;
      }
      if (msg.schema_version !== GATEWAY_SCHEMA) return set({ status: 'error', message: `Unsupported gateway schema ${String(msg.schema_version)}` });
      if (notReady(msg)) return set({ status: 'not_ready', message: String(msg.reason_code ?? 'NOT_READY') });
      if (msg.type === 'event') addEvents([msg.event as MissionEvent]);
      else if (msg.type === 'state') applyState(msg.state as MissionState);
      set({ status: 'connected', message: null, transport: 'websocket' });
    };
    // A socket that fails or closes falls back to polling the snapshot (the ICD's polling fallback).
    const fallback = () => {
      if (mine !== session) return;
      socket = null;
      if (!opened) set({ transport: 'polling' });
      void poll(mine);
    };
    socket.onerror = () => undefined;
    socket.onclose = fallback;
  }

  async function start(mine: number) {
    try {
      const health = await getJson('/api/health');
      if (mine !== session) return;
      if (notReady(health.body)) {
        set({ status: 'not_ready', message: String(health.body.reason_code ?? 'NOT_READY') });
        return schedule(() => void start(mine), RETRY_MS, mine);
      }
      const { body: m } = await getJson('/api/manifest');
      if (mine !== session) return;
      if (notReady(m)) {
        set({ status: 'not_ready', message: String(m.reason_code ?? 'NOT_READY') });
        return schedule(() => void start(mine), RETRY_MS, mine);
      }
      const meta = (m.terrain_meta ?? null) as { dataset_id?: string; sources?: string[] } | null;
      const source = resolveSourceMode(m.source_mode, meta);
      if (source === null) throw new Error(`The gateway declares source_mode "${String(m.source_mode)}", which the viewer does not accept`);
      const mode = m.mode === 'LIVE' || m.mode === 'REPLAY' ? m.mode : null;
      set({
        runId: String(m.run_id ?? ''),
        sourceMode: source,
        label: displayState({ mode, source }).label,
        datasetId: meta?.dataset_id ?? null,
      });
      const { body: snap } = await getJson(`/api/run/${encodeURIComponent(String(m.run_id ?? ''))}/snapshot`);
      if (mine !== session) return;
      applyState(snap.mission_state as MissionState);
      addEvents((snap.events as MissionEvent[]) ?? []);
      set({ status: 'connected', message: null });
      openSocket(mine);
    } catch (e) {
      if (mine !== session) return;
      set({ status: 'error', message: e instanceof Error ? e.message : 'Gateway unreachable' });
      schedule(() => void start(mine), RETRY_MS, mine);
    }
  }

  function stop() {
    session += 1;
    if (timer) clearTimeout(timer);
    timer = null;
    const s = socket;
    socket = null;
    if (s) {
      s.onclose = null;
      s.close();
    }
  }

  return {
    getState: () => state,
    subscribe: (l: () => void) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    /** Starts (or restarts) reading the gateway at `base`. */
    connect(base: string) {
      stop();
      const mine = session;
      state = { ...OFF, status: 'connecting', base };
      listeners.forEach((l) => l());
      void start(mine);
    },
    disconnect() {
      stop();
      set({ ...OFF });
    },
  };
}

export const gatewayLive = createGatewayStore(
  (url) => fetch(url),
  typeof WebSocket === 'undefined' ? null : (WebSocket as unknown as SocketCtor),
);

export function useGatewayLive(): GatewayLiveState {
  return useSyncExternalStore(gatewayLive.subscribe, gatewayLive.getState);
}
