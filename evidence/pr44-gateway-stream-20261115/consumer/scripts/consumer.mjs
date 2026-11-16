// Local integration runner: real HTTP/WebSocket producer, public MOCK replay input.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile, rename } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const harness = fileURLToPath(new URL('.', import.meta.url));
const here = JSON.parse(await readFile(resolve(harness, 'active-output.json'), 'utf8')).directory;
const root = process.env.MGE_PR44_CLIENT_ROOT;
assert(root, 'MGE_PR44_CLIENT_ROOT is required');
const require = createRequire(resolve(root, 'web/package.json'));
const { buildSync } = require('esbuild');
const read = async (name) => JSON.parse(await readFile(resolve(here, name), 'utf8'));
const ready = await read('ready.json');
const bundle = resolve(here, 'gateway-client.cjs');
buildSync({ entryPoints: [resolve(root, 'web/src/lib/gatewayLive.ts')], outfile: bundle,
  bundle: true, platform: 'node', format: 'cjs', logLevel: 'silent' });
const { createGatewayStore } = require(bundle);
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(predicate, description, timeout = 14000) {
  const end = Date.now() + timeout;
  while (!predicate()) {
    assert(Date.now() < end, `Timeout: ${description}`);
    await pause(15);
  }
}
let commandId = 0;
async function command(op, extra = {}) {
  const id = ++commandId;
  const tmp = resolve(here, `control-${id}.node.tmp`);
  await writeFile(tmp, JSON.stringify({ id, op, ...extra }));
  await rename(tmp, resolve(here, `control-${id}.json`));
  const end = Date.now() + 5000;
  while (true) {
    try { if ((await read(`ack-${id}.json`)).id === id) return; } catch {}
    assert(Date.now() < end, `No producer acknowledgement: ${op}`);
    await pause(15);
  }
}
const requests = [];
const responses = [];
const sockets = [];
const socketInstances = [];
const rawSocketMessages = [];
async function readonlyFetch(url, options) {
  assert.equal(options, undefined, 'Consumer must only use its no-options GET API');
  requests.push({ url, method: 'GET' });
  const response = await fetch(url);
  responses.push({ url, status: response.status, body: await response.clone().json() });
  return response;
}
class ActualSocket {
  constructor(url) {
    sockets.push(url);
    const socket = new WebSocket(url);
    socket.addEventListener('message', (event) => rawSocketMessages.push(event.data));
    socketInstances.push(socket);
    return socket;
  }
}

const stateHistory = [];
const clients = [];
function client() {
  const store = createGatewayStore(readonlyFetch, ActualSocket);
  store.subscribe(() => stateHistory.push({ status: store.getState().status, runId: store.getState().runId,
    label: store.getState().label, seq: store.getState().events.map((e) => e.seq), transport: store.getState().transport }));
  clients.push(store);
  return store;
}
function exactRecordedState(actual, expected = ready.expected_state) {
  assert.deepEqual(actual, expected, 'Canonical mission state must be retained without coordinate/header conversion');
  const drone = actual.agents.find((a) => a.agent_kind === 'DRONE');
  assert.equal(drone.pose.position.z, -2571.231201171875);
  assert.equal(actual.header.frame_id, 'map');
  assert(Number.isInteger(actual.header.stamp.sec) && Number.isInteger(actual.header.stamp.nanosec));
  assert(actual.active_route.outbound_path.some((p) => p.z < -2500));
}

const results = [];
let failure;
try {
  // These responses come from the unmodified Python gateway, before any replay state is loaded.
  const absent = await fetch(`${ready.base}/api/run/${ready.source_run_id}/snapshot`);
  const unavailable = await absent.json();
  assert.equal(absent.status, 503);
  assert.equal(unavailable.status, 'NOT_READY');
  assert.equal(unavailable.mode, null);
  const first = client();
  first.connect(ready.base);
  await until(() => first.getState().status === 'not_ready', '503/unavailable startup');
  assert.equal(first.getState().mission, null);
  assert.equal(first.getState().runId, null);
  await command('activate', { seed_event: false, initial: true });
  await until(() => first.getState().status === 'connected' && first.getState().transport === 'websocket', 'recorded producer connection');
  assert.equal(first.getState().sourceMode, 'MOCK');
  assert.equal(first.getState().label, 'MOCK');
  assert.deepEqual(first.getState().mission, ready.expected_initial_state);
  await command('state_ready');
  await until(() => first.getState().mission?.active_route?.status === 'FEASIBLE', 'real READY state after ROS-default IDLE');
  exactRecordedState(first.getState().mission);
  await command('event', { seq: 1 });
  await until(() => first.getState().events.some((e) => e.seq === 1), 'event 1 over real WebSocket');
  await command('event', { seq: 3 });
  await until(() => first.getState().events.some((e) => e.seq === 3), 'event 3 before event 2');
  assert.deepEqual(first.getState().events.map((e) => e.seq), [1, 3]);
  await command('event', { seq: 2 });
  await until(() => first.getState().events.some((e) => e.seq === 2), 'late event 2');
  assert.deepEqual(first.getState().events.map((e) => e.seq), [1, 2, 3]);
  results.push({ name: '503 startup, real producer compatibility, live arrival 1→3→2', status: 'PASS' });
  first.disconnect();

  // Start a fresh store with a genuine event gap; latest seq must not be the resume cursor.
  await command('reset', { run: 'A' });
  await command('activate');
  await command('event', { seq: 3 });
  const second = client();
  second.connect(ready.base);
  await until(() => second.getState().status === 'connected' && second.getState().transport === 'websocket', 'gapped snapshot connection');
  assert.deepEqual(second.getState().events.map((e) => e.seq), [1, 3]);
  assert.equal(new URL(sockets.at(-1)).searchParams.get('after_seq'), '1');
  await command('event', { seq: 2, notify: false });
  await command('meta', { version: 2 });
  await until(() => second.getState().terrainVersion === 2 && second.getState().transport === 'websocket', 'terrain_meta dynamically pushed over existing real socket');
  assert.equal(second.getState().mission.map_version, 1);
  await command('close_streams');
  await until(() => second.getState().events.some((e) => e.seq === 2), 'full snapshot fills disconnected gap');
  assert.deepEqual(second.getState().events.map((e) => e.seq), [1, 2, 3]);
  exactRecordedState(second.getState().mission);
  assert.equal(second.getState().mission.map_version, 1);
  assert.equal(second.getState().terrainVersion, 2);
  results.push({ name: 'contiguous resume cursor and snapshot recovery of missing event', status: 'PASS' });

  // A new application/RunStore under the same loopback address. B is an explicit test identity clone.
  await command('reset', { run: 'B' });
  await until(() => second.getState().status === 'not_ready', 'application restart clears stale A');
  assert.equal(second.getState().mission, null);
  assert.equal(second.getState().runId, null);
  assert.deepEqual(second.getState().events, []);
  await command('activate');
  await until(() => second.getState().status === 'connected' && second.getState().runId === ready.restart_run_id, 'discover new run B');
  assert.equal(second.getState().mission.run_id, ready.restart_run_id);
  const expectedB = JSON.parse(JSON.stringify(ready.expected_state), (key, value) => key === 'run_id' && value === ready.source_run_id ? ready.restart_run_id : value);
  exactRecordedState(second.getState().mission, expectedB);
  assert.deepEqual(second.getState().events.map((e) => e.seq), [1]);
  assert.equal(second.getState().terrainVersion, 1);
  assert.equal(second.getState().label, 'MOCK');
  results.push({ name: 'application restart A→B rediscovers manifest without mixing runs', status: 'PASS' });

  // Reusing the configured run ID is not proof of continuity across a fresh handshake.
  await command('meta', { version: 2 });
  for (let seq = 2; seq <= 9; seq++) await command('event', { seq });
  await command('state_latest_ready');
  await until(() => second.getState().mission?.last_event_seq === 9 && second.getState().events.length === 9, 'old same-ID high-water state');
  const retiredCallback = socketInstances.at(-1).onmessage;
  const retiredMessage = rawSocketMessages.at(-1);
  assert.equal(typeof retiredCallback, 'function');
  await command('close_streams');
  await until(() => second.getState().terrainVersion === 2, 'old metadata high-water version 2');
  await command('reset', { run: 'B' });
  await until(() => second.getState().status === 'not_ready', 'same-ID restart unavailable boundary');
  assert.equal(second.getState().mission, null);
  assert.equal(second.getState().runId, null);
  assert.deepEqual(second.getState().events, []);
  await command('activate', { seed_event: false, initial: true });
  await until(() => second.getState().status === 'connected' && second.getState().transport === 'websocket'
    && second.getState().mission?.last_event_seq === 0, 'fresh same-ID zero-history handshake');
  const initialB = JSON.parse(JSON.stringify(ready.expected_initial_state), (key, value) => key === 'run_id' && value === ready.source_run_id ? ready.restart_run_id : value);
  assert.deepEqual(second.getState().mission, initialB);
  assert.deepEqual(second.getState().events, []);
  assert.equal(second.getState().terrainVersion, 1);
  assert.equal(second.getState().mission.map_version, 1);
  assert.equal(new URL(sockets.at(-1)).searchParams.get('after_seq'), '0');
  const beforeRetiredCallback = second.getState();
  retiredCallback({ data: retiredMessage });
  assert.equal(second.getState(), beforeRetiredCallback, 'Retired websocket handler must not publish into the fresh session');
  results.push({ name: 'same-run-ID restart clears seq9/meta2 ledger and rejects retired WS callback', status: 'PASS' });

  assert(requests.every((r) => r.method === 'GET' && !r.url.includes('/api/mission/goal')));
  for (const [path, hash] of Object.entries(ready.source_sha256)) {
    assert.equal(createHash('sha256').update(await readFile(resolve(ready.source_roots[path], path))).digest('hex'), hash, `Source changed during run: ${path}`);
  }
  results.push({ name: 'XYZ/path/header exact preservation; MOCK labels; readonly requests; source frozen', status: 'PASS' });
} catch (error) {
  failure = error;
  results.push({ name: 'consumer integration', status: 'FAIL', message: error.stack });
} finally {
  for (const c of clients) c.disconnect();
  await command('stop').catch((error) => { failure ??= error; });
  const report = { status: failure ? 'FAIL' : 'PASS', mode: ready.mode, source_run_id: ready.source_run_id,
    restart_identity: ready.restart_identity, producer_head: ready.head, source_sha256: ready.source_sha256,
    public_package_sha256: ready.public_package_sha256, results, requests, socket_urls: sockets, state_history: stateHistory };
  await writeFile(resolve(here, 'consumer-report.json'), JSON.stringify(report, null, 2));
  await writeFile(resolve(here, 'actual-responses.json'), JSON.stringify({ source: ready, responses }, null, 2));
  console.log(JSON.stringify({ status: report.status, results, requests: requests.length, sockets: sockets.length }, null, 2));
}
if (failure) process.exitCode = 1;
