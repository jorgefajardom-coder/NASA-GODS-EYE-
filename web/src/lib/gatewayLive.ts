import { useSyncExternalStore } from 'react';
import type { AgentState, MissionEvent, MissionState, RouteDecision, TerrainMeta } from '../types/icd';
import { displayState, resolveSourceMode, type SourceMode } from './provenance';

/** Read-only status client. Gateway telemetry never replaces the recorded scene or authorizes a mission. */
export const GATEWAY_SCHEMA = '1.0.0';
const POLL_MS = 2000;
const RETRY_MS = 3000;
const KEEP_EVENTS = 60;
const UINT32_MAX = 0xffff_ffff;
const FLOAT32_MAX = 3.4028234663852886e38;

type JsonObject = Record<string, unknown>;
interface Header { frame_id: string; stamp: { sec: number; nanosec: number } }
type Wire<T> = Omit<T, 'timestamp_sim_s'> & { header: Header };
type WireAgent = Wire<AgentState> & { velocity: { linear: { x: number; y: number; z: number }; angular: { x: number; y: number; z: number } } };
type WireMission = Omit<Wire<MissionState>, 'agents' | 'active_route'> & { agents: WireAgent[]; active_route: Wire<RouteDecision> | null };
type WireMeta = Omit<TerrainMeta, 'frame_id'> & { header: Header };
type WireEvent = Wire<MissionEvent>;
interface ActiveEnvelope extends JsonObject { run_id: string; mode: 'LIVE' | 'REPLAY'; map_version: number; timestamp_sim_s: number }
interface Identity { runId: string; mode: 'LIVE' | 'REPLAY'; source: SourceMode }
export type GatewayStatus = 'off' | 'connecting' | 'connected' | 'not_ready' | 'error';
export interface GatewayLiveState {
  status: GatewayStatus;
  base: string | null;
  message: string | null;
  runId: string | null;
  sourceMode: SourceMode | null;
  label: string;
  datasetId: string | null;
  /** Latest metadata version; distinct from the mission authority's map_version. No rasters are inferred. */
  terrainVersion: number | null;
  mission: WireMission | null;
  events: WireEvent[];
  transport: 'websocket' | 'polling' | null;
  updatedAt: number | null;
}
const OFF: GatewayLiveState = { status: 'off', base: null, message: null, runId: null, sourceMode: null, label: 'NOT_READY', datasetId: null, terrainVersion: null, mission: null, events: [], transport: null, updatedAt: null };

type FetchLike = (url: string) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;
interface SocketLike {
  onopen: ((e: unknown) => void) | null;
  onmessage: ((e: { data: unknown }) => void) | null;
  onerror: ((e: unknown) => void) | null;
  onclose: ((e: unknown) => void) | null;
  close(): void;
}
type SocketCtor = new (url: string) => SocketLike;

export function gatewayBaseFrom(param: string | null): string | null {
  if (!param) return null;
  try {
    const u = new URL(param);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
    return u.origin + u.pathname.replace(/\/+$/, '');
  } catch { return null; }
}
export function eventsSocketUrl(base: string, afterSeq: number): string {
  return base.replace(/^http/, 'ws') + '/api/events?after_seq=' + afterSeq;
}

function need(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}
const object = (x: unknown): x is JsonObject => !!x && typeof x === 'object' && !Array.isArray(x);
const finite = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x);
const uint = (x: unknown): x is number => typeof x === 'number' && Number.isSafeInteger(x) && x >= 0;
const mapVersion = (x: unknown): x is number => uint(x) && x <= UINT32_MAX;
const text = (x: unknown): x is string => typeof x === 'string';
const nonempty = (x: unknown): x is string => text(x) && x.length > 0;
const enumValue = (value: unknown, values: readonly string[]) => text(value) && values.includes(value);
const point = (p: unknown): boolean => object(p) && finite(p.x) && finite(p.y) && finite(p.z);
const resource = (x: unknown): boolean => finite(x) && Math.abs(x) <= FLOAT32_MAX;
function jsonNumbers(value: unknown): void {
  if (typeof value === 'number') need(Number.isFinite(value), 'Non-finite gateway value');
  else if (Array.isArray(value)) value.forEach(jsonNumbers);
  else if (object(value)) Object.values(value).forEach(jsonNumbers);
}
function header(value: unknown, frame: 'map' | null): void {
  need(object(value) && text(value.frame_id) && (frame === null || value.frame_id === frame), 'Invalid payload frame');
  const stamp = value.stamp;
  need(object(stamp) && Number.isInteger(stamp.sec) && (stamp.sec as number) >= -(2 ** 31) && (stamp.sec as number) < 2 ** 31
    && uint(stamp.nanosec) && stamp.nanosec < 1e9, 'Invalid ROS stamp');
}
function identityBody(value: unknown, run: string, frame: 'map' | null = 'map'): asserts value is JsonObject {
  need(object(value) && value.run_id === run, 'Payload run mismatch');
  header(value.header, frame);
}
function strings(value: JsonObject, keys: string[]): void {
  need(keys.every((key) => text(value[key])), 'Invalid payload text fields');
}
function baseEnvelope(value: unknown): asserts value is JsonObject {
  need(object(value), 'Gateway envelope must be an object');
  need(value.schema_version === GATEWAY_SCHEMA, 'Unsupported gateway schema ' + String(value.schema_version));
  jsonNumbers(value);
  if (value.source_mode !== undefined) need(resolveSourceMode(value.source_mode) !== null, 'Invalid source_mode "' + String(value.source_mode) + '"');
}
function activeEnvelope(value: unknown, identity?: Identity): asserts value is ActiveEnvelope {
  baseEnvelope(value);
  need(nonempty(value.run_id) && enumValue(value.mode, ['LIVE', 'REPLAY']) && mapVersion(value.map_version) && finite(value.timestamp_sim_s), 'Invalid active gateway envelope');
  if (identity) {
    need(value.run_id === identity.runId && value.mode === identity.mode, 'Gateway run or mode mismatch');
    if (value.source_mode !== undefined) need(value.source_mode === identity.source, 'Gateway source_mode changed');
  }
}
class Unavailable extends Error {
  constructor(public status: 'not_ready' | 'error', reason: string) { super(reason); }
}
function checkUnavailable(body: JsonObject): void {
  if (body.status !== 'NOT_READY' && body.status !== 'ERROR') return;
  need((body.run_id === null || nonempty(body.run_id)) && body.mode === null && body.map_version === null && body.timestamp_sim_s === null
    && nonempty(body.reason_code), 'Invalid unavailable envelope');
  throw new Unavailable(body.status === 'ERROR' ? 'error' : 'not_ready', body.reason_code);
}
function checkAgent(value: unknown, run: string): asserts value is WireAgent {
  identityBody(value, run);
  need(nonempty(value.agent_id) && enumValue(value.agent_kind, ['HUMAN', 'DRONE', 'ROVER'])
    && enumValue(value.mode, ['IDLE', 'MOVING', 'OBSERVING', 'WORKING', 'RETURNING', 'HALTED']), 'Invalid agent identity or mode');
  const pose = value.pose, velocity = value.velocity;
  need(object(pose) && point(pose.position) && object(pose.orientation)
    && ['x', 'y', 'z', 'w'].every((key) => finite((pose.orientation as JsonObject)[key])), 'Invalid agent pose');
  need(object(velocity) && point(velocity.linear) && point(velocity.angular), 'Invalid agent velocity');
  need(resource(value.time_remaining_s) && resource(value.energy_remaining_wh)
    && (value.agent_kind === 'HUMAN' ? resource(value.oxygen_remaining_l) : value.oxygen_remaining_l === null)
    && finite(value.confidence) && value.confidence >= 0 && value.confidence <= 1, 'Invalid agent resources');
}
function checkRoute(value: unknown, run: string, agents: WireAgent[], routeId: string): void {
  need(object(value), 'Invalid active_route');
  // A ROS default-initialized route is present before any planner decision.
  if (value.route_id === '' && value.status === '' && routeId === '') {
    need(Array.isArray(value.outbound_path) && !value.outbound_path.length && Array.isArray(value.return_path) && !value.return_path.length, 'Invalid empty route');
    return;
  }
  identityBody(value, run);
  strings(value, ['request_id', 'route_id', 'agent_id', 'reason_code', 'detail']);
  need(enumValue(value.mode, ['FAST', 'EFFICIENT', 'SAFE'])
    && enumValue(value.status, ['FEASIBLE', 'UNKNOWN', 'NO_PATH', 'INSUFFICIENT_BUDGET', 'STALE_MAP', 'ERROR'])
    && mapVersion(value.map_version_used), 'Invalid route decision');
  need(Array.isArray(value.outbound_path) && value.outbound_path.every(point) && Array.isArray(value.return_path) && value.return_path.every(point), 'Invalid route paths');
  const agent = agents.find((a) => a.agent_id === value.agent_id);
  if (value.status === 'FEASIBLE') need(agent, 'Unknown route agent');
  const human = agent?.agent_kind === 'HUMAN';
  for (const key of ['travel_time_s', 'energy_est_wh', 'oxygen_est_l', 'min_clearance_m', 'reserve_time_s', 'reserve_wh', 'reserve_oxygen_l']) {
    const oxygen = key === 'oxygen_est_l' || key === 'reserve_oxygen_l';
    need(value.status === 'FEASIBLE' && oxygen && !human ? value[key] === null
      : value.status !== 'FEASIBLE' && value[key] === null || resource(value[key]), 'Invalid route metric ' + key);
  }
  need(routeId === '' || value.route_id === routeId && value.status === 'FEASIBLE', 'Active route identity mismatch');
}
function checkMission(value: unknown, env: ActiveEnvelope): asserts value is WireMission {
  identityBody(value, env.run_id);
  need(uint(value.last_event_seq) && mapVersion(value.map_version) && value.map_version <= env.map_version
    && enumValue(value.mission_state, ['IDLE', 'PLANNING', 'READY', 'ACTIVE', 'REPLAN', 'RETURNING', 'COMPLETE', 'BLOCKED', 'ABORTED']), 'Invalid mission state');
  strings(value, ['reason_code', 'primary_agent_id', 'active_task_id', 'active_task_kind', 'active_task_state', 'route_id']);
  need(enumValue(value.active_task_state, ['', 'DISCOVERED', 'ELIGIBLE', 'ASSIGNED', 'EXECUTING', 'DONE', 'REJECTED', 'BLOCKED'])
    && point(value.base) && point(value.primary_goal) && Array.isArray(value.agents), 'Invalid mission payload');
  const ids = new Set<string>();
  for (const agent of value.agents) {
    checkAgent(agent, env.run_id);
    need(!ids.has(agent.agent_id), 'Duplicate agent identity');
    ids.add(agent.agent_id);
  }
  if (value.active_route !== null && value.active_route !== undefined) {
    checkRoute(value.active_route, env.run_id, value.agents, value.route_id as string);
    if (value.route_id) need(object(value.active_route) && value.active_route.map_version_used === value.map_version, 'Active route map mismatch');
  }
  else need(value.route_id === '', 'Missing active route');
}
function checkEvent(value: unknown, env: ActiveEnvelope): asserts value is WireEvent {
  identityBody(value, env.run_id, null);
  need(nonempty(value.event_id) && uint(value.seq) && value.seq > 0 && mapVersion(value.map_version) && value.map_version <= env.map_version
    && enumValue(value.event_type, ['MISSION_STATE_CHANGED', 'GOAL_ACCEPTED', 'GOAL_REJECTED', 'MAP_UPDATED', 'ROUTE_PUBLISHED', 'ROUTE_INVALIDATED', 'TASK_DISCOVERED', 'TASK_STATE_CHANGED', 'ERROR']), 'Invalid event identity or sequence');
  strings(value, ['causality_id', 'task_id', 'agent_id', 'route_id', 'previous_state', 'new_state', 'reason_code', 'detail']);
}
function checkMeta(value: unknown, env: ActiveEnvelope): asserts value is WireMeta {
  identityBody(value, env.run_id);
  need(nonempty(value.dataset_id) && mapVersion(value.map_version) && value.map_version <= env.map_version
    && mapVersion(value.rows) && value.rows > 0 && mapVersion(value.cols) && value.cols > 0
    && finite(value.resolution_m) && value.resolution_m > 0 && finite(value.origin_x_m) && finite(value.origin_y_m)
    && finite(value.origin_lat_deg) && finite(value.origin_lon_deg)
    && (value.nodata_value === null || resource(value.nodata_value)), 'Invalid terrain metadata');
  strings(value, ['crs', 'vertical_datum', 'checksum_sha256']);
  need(Array.isArray(value.sources) && value.sources.every(text), 'Invalid terrain sources');
}
/** Stable comparison keeps immutable IDs independent of JSON object-key ordering. */
function canonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (object(value)) return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
}
function metaContent(meta: WireMeta): string {
  const { header: _header, ...content } = meta;
  return canonical(content);
}
const GEOMETRY = ['dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m', 'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum', 'checksum_sha256'] as const;

export function createGatewayStore(fetchFn: FetchLike, Socket: SocketCtor | null, now: () => number = Date.now) {
  let state: GatewayLiveState = OFF;
  let identity: Identity | null = null;
  let meta: WireMeta | null = null;
  let eventLedger = new Map<number, WireEvent>();
  let eventIds = new Map<string, number>();
  let metaLedger = new Map<number, WireMeta>();
  let cursor = 0;
  let socket: SocketLike | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let session = 0;
  const listeners = new Set<() => void>();
  const set = (patch: Partial<GatewayLiveState>) => { state = { ...state, ...patch }; listeners.forEach((l) => l()); };
  function resetBinding() {
    identity = null; meta = null; eventLedger = new Map(); eventIds = new Map(); metaLedger = new Map(); cursor = 0;
  }
  function schedule(fn: () => void, ms: number, mine: number) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; if (mine === session) fn(); }, ms);
  }
  function closeSocket() {
    const s = socket; socket = null;
    if (s) { s.onopen = null; s.onmessage = null; s.onerror = null; s.onclose = null; s.close(); }
  }
  function stop() {
    session++;
    if (timer) clearTimeout(timer);
    timer = null;
    closeSocket();
  }
  function recover(error: unknown, mine: number) {
    if (mine !== session) return;
    stop();
    const status = error instanceof Unavailable ? error.status : 'error';
    set({ ...OFF, base: state.base, status, label: status === 'error' ? 'ERROR' : 'NOT_READY', message: error instanceof Error ? error.message : 'Gateway unreachable' });
    schedule(() => void start(session), RETRY_MS, session);
  }
  async function getJson(path: string): Promise<ActiveEnvelope> {
    const res = await fetchFn(state.base + path);
    // Unknown run is a plain FastAPI 404 (not a canonical inactive envelope).
    if (res.status === 404) throw new Error('Gateway run unavailable (HTTP 404); rediscovering manifest');
    const body: unknown = await res.json();
    baseEnvelope(body);
    checkUnavailable(body);
    need(res.ok && res.status >= 200 && res.status < 300, 'Gateway HTTP ' + res.status);
    activeEnvelope(body);
    return body;
  }
  function accept(env: ActiveEnvelope, updates: { mission?: unknown; events?: unknown; meta?: unknown }, nextIdentity: Identity = identity!) {
    activeEnvelope(env, nextIdentity);
    const sameRun = identity?.runId === nextIdentity.runId && identity.mode === nextIdentity.mode;
    const nextEvents = sameRun ? new Map(eventLedger) : new Map<number, WireEvent>();
    const nextIds = sameRun ? new Map(eventIds) : new Map<string, number>();
    const nextMetas = sameRun ? new Map(metaLedger) : new Map<number, WireMeta>();
    let nextMeta = sameRun ? meta : null;
    let mission = sameRun ? state.mission : null;
    if (updates.mission !== undefined) {
      checkMission(updates.mission, env);
      const candidate = updates.mission;
      if (!mission || candidate.last_event_seq >= mission.last_event_seq && candidate.map_version >= mission.map_version) mission = candidate;
    }
    if (updates.events !== undefined) {
      need(Array.isArray(updates.events), 'Events must be an array');
      for (const event of updates.events) {
        checkEvent(event, env);
        const prior = nextEvents.get(event.seq);
        need(!prior || canonical(prior) === canonical(event), 'Conflicting event sequence');
        need(!nextIds.has(event.event_id) || nextIds.get(event.event_id) === event.seq, 'Conflicting event ID');
        nextEvents.set(event.seq, event);
        nextIds.set(event.event_id, event.seq);
      }
    }
    if (updates.meta !== undefined && updates.meta !== null) {
      checkMeta(updates.meta, env);
      const candidate = updates.meta;
      if (nextMeta) need(GEOMETRY.every((key) => candidate[key] === nextMeta![key]), 'Terrain identity or geometry changed within run');
      const prior = nextMetas.get(candidate.map_version);
      need(!prior || metaContent(prior) === metaContent(candidate), 'Conflicting terrain version');
      nextMetas.set(candidate.map_version, candidate);
      if (!nextMeta || candidate.map_version >= nextMeta.map_version) nextMeta = candidate;
    }
    let nextCursor = sameRun ? cursor : 0;
    while (nextEvents.has(nextCursor + 1)) nextCursor++;
    const source = resolveSourceMode(nextIdentity.source, nextMeta);
    need(source !== null, 'Invalid source_mode');
    identity = nextIdentity; meta = nextMeta; eventLedger = nextEvents; eventIds = nextIds; metaLedger = nextMetas; cursor = nextCursor;
    set({ runId: nextIdentity.runId, sourceMode: source, label: displayState({ mode: nextIdentity.mode, source }).label,
      datasetId: meta?.dataset_id ?? null, terrainVersion: meta?.map_version ?? null, mission,
      events: [...eventLedger.values()].sort((a, b) => a.seq - b.seq).slice(-KEEP_EVENTS), updatedAt: now() });
  }
  function snapshot(body: ActiveEnvelope, nextIdentity: Identity = identity!) {
    need(Object.hasOwn(body, 'mission_state') && Object.hasOwn(body, 'terrain_meta') && Object.hasOwn(body, 'events'), 'Incomplete snapshot');
    accept(body, { mission: body.mission_state, events: body.events, meta: body.terrain_meta }, nextIdentity);
  }
  async function poll(mine: number) {
    try {
      const body = await getJson('/api/run/' + encodeURIComponent(identity!.runId) + '/snapshot');
      if (mine !== session) return;
      snapshot(body);
      set({ status: 'connected', message: null, transport: 'polling' });
      schedule(() => void poll(mine), POLL_MS, mine);
    } catch (e) { recover(e, mine); }
  }
  function openSocket(mine: number) {
    if (!Socket || !state.base) return void poll(mine);
    let candidate: SocketLike;
    try { candidate = new Socket(eventsSocketUrl(state.base, cursor)); } catch { return void poll(mine); }
    socket = candidate;
    candidate.onopen = () => { if (mine === session && socket === candidate) set({ transport: 'websocket' }); };
    candidate.onmessage = (e) => {
      if (mine !== session || socket !== candidate) return;
      try {
        const msg: unknown = JSON.parse(String(e.data));
        baseEnvelope(msg);
        checkUnavailable(msg);
        activeEnvelope(msg, identity!);
        if (msg.type === 'event') accept(msg, { events: [msg.event] });
        else if (msg.type === 'state') {
          need(msg.state !== undefined && msg.state !== null, 'Missing mission state');
          accept(msg, { mission: msg.state });
        }
        else if (msg.type === 'terrain_meta') {
          need(msg.terrain_meta !== null && msg.terrain_meta !== undefined, 'Missing terrain metadata');
          accept(msg, { meta: msg.terrain_meta });
        } else throw new Error('Unsupported gateway message type');
        set({ status: 'connected', message: null, transport: 'websocket' });
      } catch (e) { recover(e, mine); }
    };
    const fallback = () => {
      if (mine !== session || socket !== candidate) return;
      closeSocket();
      set({ status: 'connecting', message: null, transport: 'polling' });
      // Full snapshot reconciles late events, including gaps below the largest seen sequence.
      void poll(mine);
    };
    candidate.onerror = fallback;
    candidate.onclose = fallback;
  }
  async function start(mine: number) {
    if (mine !== session) return;
    // A fresh handshake reads the current gateway store, even after a same-ID
    // process restart. Without a wire epoch, continuity is only claimed inside
    // this binding; old callbacks remain invalidated by the session token.
    resetBinding();
    set({ ...OFF, base: state.base, status: 'connecting' });
    try {
      const health = await getJson('/api/health');
      if (mine !== session) return;
      need(health.status === 'READY' && health.ros_connected === true && typeof health.terrain_meta_received === 'boolean', 'Invalid gateway health');
      const manifest = await getJson('/api/manifest');
      if (mine !== session) return;
      need(manifest.run_id === health.run_id && manifest.mode === health.mode, 'Gateway changed run during bootstrap');
      const source = resolveSourceMode(manifest.source_mode);
      need(source !== null, 'Invalid source_mode "' + String(manifest.source_mode) + '"');
      need(Array.isArray(manifest.agents) && manifest.agents.every((a) => object(a) && nonempty(a.agent_id) && enumValue(a.agent_kind, ['HUMAN', 'DRONE', 'ROVER'])), 'Invalid manifest agents');
      need(Object.hasOwn(manifest, 'terrain_meta'), 'Missing manifest terrain metadata');
      const nextIdentity: Identity = { runId: manifest.run_id, mode: manifest.mode, source };
      if (manifest.terrain_meta !== null) checkMeta(manifest.terrain_meta, manifest);
      const body = await getJson('/api/run/' + encodeURIComponent(nextIdentity.runId) + '/snapshot');
      if (mine !== session) return;
      // Validate everything before publishing a connected state or replacing the current run.
      snapshot(body, nextIdentity);
      if (manifest.terrain_meta !== null) accept(manifest, { meta: manifest.terrain_meta }, nextIdentity);
      set({ status: 'connected', message: null });
      openSocket(mine);
    } catch (e) { recover(e, mine); }
  }
  return {
    getState: () => state,
    subscribe: (l: () => void) => { listeners.add(l); return () => listeners.delete(l); },
    connect(base: string) {
      stop(); resetBinding();
      state = { ...OFF, status: 'connecting', base: gatewayBaseFrom(base) };
      listeners.forEach((l) => l());
      if (!state.base) { set({ status: 'error', label: 'ERROR', message: 'Invalid gateway URL' }); return; }
      void start(session);
    },
    disconnect() { stop(); resetBinding(); set({ ...OFF }); },
  };
}
export const gatewayLive = createGatewayStore((url) => fetch(url), typeof WebSocket === 'undefined' ? null : WebSocket as unknown as SocketCtor);
export function useGatewayLive(): GatewayLiveState { return useSyncExternalStore(gatewayLive.subscribe, gatewayLive.getState); }
