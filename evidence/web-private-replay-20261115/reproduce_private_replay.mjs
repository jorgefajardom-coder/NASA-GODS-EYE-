#!/usr/bin/env node
// AI-assisted (Claude Code, Anthropic); declared in docs/AI_USAGE.md and docs/ai_usage.json.
//
// Private-browser replay check for the built viewer (AC-08 evidence input).
//
// It serves web/dist from a file-only static server on 127.0.0.1, opens it in an
// off-the-record Chromium context with an empty profile, and compares what the viewer
// reports (window.mge.state() and the visible text) with values computed here,
// independently, from the recorded package files. Every browser request is logged, so
// "no backend" is shown by the network record and not only by a process list.
//
// It does not run ROS, Gazebo, the gateway or the planner, and it creates no mission
// result: it only reads a build and a recorded package.
//
//   node reproduce_private_replay.mjs --dist ../../web/dist --out /NEW/EMPTY/DIR
//
// Options: --chromium <path> (default: chromium on PATH), --headed (visible window),
// --screenshots (local PNG captures; add a visible "AI-generated" mark before publishing any).
// Requires Node >= 22 (global WebSocket) and no npm dependency.

import { spawn, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { extname, join, normalize, relative, resolve, sep } from 'node:path';

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const DIST = resolve(opt('dist', 'web/dist'));
const OUT = resolve(opt('out', ''));
const CHROMIUM = opt('chromium', 'chromium');
const HEADED = args.includes('--headed');
// Captures show the AI-generated base model; they are opt-in and must carry a visible
// "AI-generated" mark before being published (AGENTS.md section 11).
const SCREENSHOTS = args.includes('--screenshots');
const RECORDED_ENTRY = 'recorded-recovery-001';
const VIEWPORT = { width: 1600, height: 900 };

if (!opt('out')) throw new Error('--out <new empty directory> is required');
if (!existsSync(join(DIST, 'index.html'))) throw new Error(`No build at ${DIST}; run "npm run build" in web/ first`);
if (existsSync(OUT) && readdirSync(OUT).length > 0) throw new Error(`Refusing to overwrite a non-empty directory: ${OUT}`);
mkdirSync(OUT, { recursive: true });

const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const round = (v, d = 2) => Math.round(v * 10 ** d) / 10 ** d;

// ---------------------------------------------------------------- static server
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.jsonl': 'application/x-ndjson', '.png': 'image/png', '.webp': 'image/webp',
  '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.svg': 'image/svg+xml', '.webm': 'video/webm',
  '.glb': 'model/gltf-binary', '.woff2': 'font/woff2', '.woff': 'font/woff', '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml', '.wasm': 'application/wasm', '.bin': 'application/octet-stream',
};
const served = [];
const server = createServer((req, res) => {
  const path = decodeURIComponent((req.url ?? '/').split('?')[0]);
  let file = normalize(join(DIST, path));
  const inside = file === DIST || file.startsWith(DIST + sep);
  if (inside && existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
  const ok = req.method === 'GET' && inside && existsSync(file) && statSync(file).isFile();
  served.push({ method: req.method, url: req.url, status: ok ? 200 : 404 });
  if (!ok) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('not found');
  }
  const body = readFileSync(file);
  // Range support keeps the browser's media loader on the same file-only path.
  const range = /^bytes=(\d+)-(\d*)$/.exec(req.headers.range ?? '');
  const headers = { 'Content-Type': MIME[extname(file).toLowerCase()] ?? 'application/octet-stream', 'Cache-Control': 'no-store', 'Accept-Ranges': 'bytes' };
  if (range) {
    const start = Number(range[1]);
    const end = range[2] ? Math.min(Number(range[2]), body.length - 1) : body.length - 1;
    served[served.length - 1].status = 206;
    res.writeHead(206, { ...headers, 'Content-Range': `bytes ${start}-${end}/${body.length}`, 'Content-Length': end - start + 1 });
    return res.end(body.subarray(start, end + 1));
  }
  res.writeHead(200, { ...headers, 'Content-Length': body.length });
  res.end(body);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const ORIGIN = `http://127.0.0.1:${server.address().port}`;

// ---------------------------------------------------------------- expected values from the package
function walk(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}
const distFiles = walk(DIST).map((p) => relative(DIST, p).split(sep).join('/')).sort();
const hiddenNamed = distFiles.filter((f) => /(^|\/)(evaluator|reference)(\/|\.|_|-)|reference\.json$|hirise/i.test(f));

const pkgDir = join(DIST, 'replay', RECORDED_ENTRY);
const pkgManifest = JSON.parse(readFileSync(join(pkgDir, 'manifest.json'), 'utf8'));
const pkgHashes = Object.fromEntries(readdirSync(pkgDir).sort().map((f) => [f, sha256(readFileSync(join(pkgDir, f)))]));
const records = readFileSync(join(pkgDir, pkgManifest.files.timeline), 'utf8').split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
const t0 = pkgManifest.time_start_sim_s;
const stateRecs = records.filter((r) => r.type === 'state');
const eventRecs = records.filter((r) => r.type === 'event');
const endT = Math.max(...records.map((r) => r.timestamp_sim_s - t0));

/** What the package says at replay time t (seconds from the recorded start): the last state at or before t. */
function expectedAt(t) {
  const frame = [...stateRecs].reverse().find((r) => r.timestamp_sim_s - t0 <= t) ?? stateRecs[0];
  const s = frame.state;
  const events = eventRecs.filter((r) => r.timestamp_sim_s - t0 <= t).map((r) => r.event);
  return {
    run_id: s.run_id,
    mission_state: s.mission_state,
    map_version: s.map_version,
    active_route_id: s.route_id || null,
    active_route_status: s.active_route.status || null,
    active_route_map_version: s.route_id ? s.active_route.map_version_used : null,
    invalidated_route_ids: events.filter((e) => e.event_type === 'ROUTE_INVALIDATED').map((e) => e.route_id),
    event_types: events.map((e) => e.event_type),
    last_event_detail: events.length ? events[events.length - 1].detail : null,
    agent_modes: Object.fromEntries(s.agents.map((a) => [a.agent_id, a.mode])),
    agents: s.agents.map((a) => ({
      id: a.agent_id,
      mode: a.mode,
      position_enu_m: { x: round(a.pose.position.x), y: round(a.pose.position.y), z: round(a.pose.position.z) },
      energy_wh: a.energy_remaining_wh,
      oxygen_l: a.oxygen_remaining_l,
      time_s: a.time_remaining_s,
    })),
  };
}

// Checkpoints sit strictly inside each recorded phase; `exact` also compares poses and
// resources, which the viewer interpolates between samples everywhere but at the end.
const invalidation = eventRecs.find((r) => r.event.event_type === 'ROUTE_INVALIDATED');
const published = eventRecs.filter((r) => r.event.event_type === 'ROUTE_PUBLISHED').map((r) => r.timestamp_sim_s - t0);
const tInv = invalidation.timestamp_sim_s - t0;
const CHECKPOINTS = [
  { name: 'planning', t: (published[0] + (eventRecs[0].timestamp_sim_s - t0)) / 2 },
  { name: 'first-route', t: (published[0] + tInv) / 2 },
  { name: 'invalidated-replanning', t: (tInv + published[1]) / 2 },
  { name: 'replacement-route', t: published[1] + 20 },
  { name: 'final', t: endT, exact: true },
];

// ---------------------------------------------------------------- Chromium over the DevTools protocol
const profile = mkdtempSync(join(tmpdir(), 'mge-private-profile-'));
const chromeArgs = [
  `--user-data-dir=${profile}`, '--incognito', '--remote-debugging-port=0', '--no-first-run', '--no-default-browser-check',
  '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-extensions',
  '--disable-features=Translate,OptimizationHints,MediaRouter', '--metrics-recording-only', '--password-store=basic',
  `--window-size=${VIEWPORT.width},${VIEWPORT.height}`, '--enable-unsafe-swiftshader',
  ...(HEADED ? [] : ['--headless=new']),
  'about:blank',
];
const chrome = spawn(CHROMIUM, chromeArgs, { stdio: ['ignore', 'ignore', 'pipe'] });
const wsUrl = await new Promise((ok, fail) => {
  let buf = '';
  const timer = setTimeout(() => fail(new Error(`Chromium did not expose DevTools:\n${buf}`)), 30000);
  chrome.stderr.on('data', (d) => {
    buf += d;
    const m = /DevTools listening on (ws:\/\/\S+)/.exec(buf);
    if (m) {
      clearTimeout(timer);
      ok(m[1]);
    }
  });
  chrome.on('exit', (c) => fail(new Error(`Chromium exited (${c}):\n${buf}`)));
});

const ws = new WebSocket(wsUrl);
await new Promise((ok, fail) => {
  ws.onopen = ok;
  ws.onerror = () => fail(new Error('DevTools socket failed'));
});
let nextId = 0;
const pending = new Map();
const listeners = [];
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { ok, fail } = pending.get(msg.id);
    pending.delete(msg.id);
    return msg.error ? fail(new Error(`${msg.error.message}`)) : ok(msg.result);
  }
  for (const l of listeners) l(msg);
};
const cdp = (method, params = {}, sessionId) =>
  new Promise((ok, fail) => {
    const id = ++nextId;
    pending.set(id, { ok, fail });
    ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });

const browserVersion = await cdp('Browser.getVersion');

/** One private window: a new off-the-record browser context with its own empty storage. */
async function privateWindow(label, url, body) {
  const { browserContextId } = await cdp('Target.createBrowserContext', { disposeOnDetach: true });
  const { targetId } = await cdp('Target.createTarget', { url: 'about:blank', browserContextId, ...VIEWPORT });
  const { sessionId } = await cdp('Target.attachToTarget', { targetId, flatten: true });
  const send = (m, p) => cdp(m, p, sessionId);
  const net = { requests: [], webSockets: [], failed: [], console: [], exceptions: [] };
  const byId = new Map();
  const listener = (msg) => {
    if (msg.sessionId !== sessionId) return;
    const p = msg.params;
    if (msg.method === 'Network.requestWillBeSent') {
      const r = { url: p.request.url, method: p.request.method, type: p.type, status: null };
      byId.set(p.requestId, r);
      net.requests.push(r);
    } else if (msg.method === 'Network.responseReceived') {
      const r = byId.get(p.requestId);
      if (r) r.status = p.response.status;
    } else if (msg.method === 'Network.loadingFailed') {
      const r = byId.get(p.requestId);
      net.failed.push({ url: r?.url ?? null, error: p.errorText, canceled: !!p.canceled });
    } else if (msg.method === 'Network.webSocketCreated') net.webSockets.push(p.url);
    else if (msg.method === 'Network.eventSourceMessageReceived') net.webSockets.push(`eventsource:${p.requestId}`);
    else if (msg.method === 'Runtime.exceptionThrown') net.exceptions.push(p.exceptionDetails.exception?.description ?? p.exceptionDetails.text);
    else if (msg.method === 'Runtime.consoleAPICalled' && (p.type === 'error' || p.type === 'warning')) {
      net.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 300) });
    }
  };
  listeners.push(listener);
  await send('Network.enable');
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.bringToFront');
  await send('Emulation.setDeviceMetricsOverride', { ...VIEWPORT, deviceScaleFactor: 1, mobile: false });

  const evaluate = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(`${label}: ${r.exceptionDetails.exception?.description ?? r.exceptionDetails.text}`);
    return r.result.value;
  };
  const waitFor = async (expression, what, timeoutMs = 60000) => {
    const until = Date.now() + timeoutMs;
    for (;;) {
      if (await evaluate(expression)) return;
      if (Date.now() > until) throw new Error(`${label}: timed out waiting for ${what}`);
      await sleep(200);
    }
  };
  const screenshot = async (name) => {
    if (!SCREENSHOTS) return null;
    const { data } = await send('Page.captureScreenshot', { format: 'png' });
    const file = join(OUT, 'screenshots', `${name}.png`);
    mkdirSync(join(OUT, 'screenshots'), { recursive: true });
    writeFileSync(file, Buffer.from(data, 'base64'));
    return file;
  };

  const cookiesBefore = (await cdp('Storage.getCookies', { browserContextId })).cookies.length;
  await send('Page.navigate', { url });
  const shot = async (name) => { const f = await screenshot(name); return f ? relative(OUT, f) : null; };
  const result = await body({ evaluate, waitFor, shot, send });
  await sleep(500);
  const cookiesAfter = (await cdp('Storage.getCookies', { browserContextId })).cookies.length;
  listeners.splice(listeners.indexOf(listener), 1);
  await cdp('Target.closeTarget', { targetId });
  await cdp('Target.disposeBrowserContext', { browserContextId });

  const offOrigin = net.requests.filter((r) => !r.url.startsWith(`${ORIGIN}/`) && !/^(data|blob|about):/.test(r.url));
  const notOk = net.requests.filter((r) => r.url.startsWith(ORIGIN) && r.status !== null && ![200, 206, 304].includes(r.status));
  return {
    label,
    url,
    off_the_record_context: true,
    cookies_before: cookiesBefore,
    cookies_after: cookiesAfter,
    request_count: net.requests.length,
    off_origin_requests: offOrigin,
    websocket_or_eventsource: net.webSockets,
    non_ok_same_origin: notOk,
    failed_requests: net.failed,
    page_exceptions: net.exceptions,
    console_errors: net.console.filter((c) => c.type === 'error'),
    requests: net.requests.map((r) => `${r.status ?? '-'} ${r.method} ${r.url.startsWith('data:') ? 'data:' : r.url.replace(ORIGIN, '')}`),
    ...result,
  };
}

const READ_PAGE = `(() => {
  const text = document.body.innerText;
  const s = window.mge.state();
  return { state: s, text_has: {
    replay_label: text.includes(s.source.label),
    offline: /Offline/i.test(text),
    live_claim: /\\bLIVE\\b(?! LINK NOT AVAILABLE)/.test(text.replace(/NOT VALIDATED LIVE/g, '')),
  }, label: s.source.label, disclaimer: s.source.disclaimer, about: window.mge.about, title: document.title, storage_keys: Object.keys(localStorage), text };
})()`;

const SEEK = (t, toEnd) => `(() => {
  const el = document.querySelector('input[type="range"][aria-label="Simulated time"]');
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  set.call(el, ${toEnd ? 'el.max' : JSON.stringify(String(t))});
  el.dispatchEvent(new Event('input', { bubbles: true }));
  return el.value;
})()`;

const checks = [];
const check = (name, pass, detail) => checks.push({ name, pass: !!pass, ...(detail === undefined ? {} : { detail }) });
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ---- window 1: the exact recorder package, compared phase by phase with its own records
const recorded = await privateWindow('recorded-package', `${ORIGIN}/?run=${RECORDED_ENTRY}`, async ({ evaluate, waitFor, shot }) => {
  const storageAtOpen = await evaluate('({ local: localStorage.length, session: sessionStorage.length, cookie: document.cookie })');
  await waitFor('!!(window.mge && window.mge.state)', 'the viewer to open the recorded run');
  const renderer = await evaluate(`(() => { const c = document.createElement('canvas'); const gl = c.getContext('webgl2') || c.getContext('webgl'); if (!gl) return null; const e = gl.getExtension('WEBGL_debug_renderer_info'); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'webgl'; })()`);
  const opened = await evaluate(READ_PAGE);
  // The event explanation lives on the replay tab; the viewer opens on the exploration tab.
  const tab = await evaluate(`(() => { const b = [...document.querySelectorAll('[role="tab"]')].find((x) => /replay/i.test(x.textContent) && !x.disabled); if (!b) return null; b.click(); return b.textContent.trim(); })()`);
  await waitFor(`!!document.querySelector('section[aria-label="Mission events"]')`, 'the mission events panel');
  const phases = [];
  for (const cp of CHECKPOINTS) {
    const sliderValue = await evaluate(SEEK(cp.t, cp.exact));
    await sleep(900);
    const page = await evaluate(READ_PAGE);
    const want = expectedAt(cp.t);
    const got = page.state;
    const diffs = [];
    const cmp = (field, a, b) => same(a, b) || diffs.push({ field, viewer: a, package: b });
    cmp('run_id', got.source.run_id, want.run_id);
    cmp('mission_state', got.mission.state, want.mission_state);
    cmp('map_version', got.mission.map_version, want.map_version);
    cmp('active_route_id', got.active_route?.id ?? null, want.active_route_id);
    cmp('active_route_status', got.active_route?.status ?? null, want.active_route_status);
    cmp('active_route_map_version', got.active_route?.map_version_used ?? null, want.active_route_map_version);
    cmp('invalidated_route_ids', got.invalidated_routes, want.invalidated_route_ids);
    cmp('recent_event_types', got.recent_events.map((e) => e.type), want.event_types.slice(-got.recent_events.length || want.event_types.length));
    cmp('agent_modes', Object.fromEntries(got.agents.map((a) => [a.id, a.mode])), want.agent_modes);
    if (cp.exact) {
      cmp('agents_pose_and_resources', got.agents.map(({ id, mode, position_enu_m, energy_wh, oxygen_l, time_s }) => ({ id, mode, position_enu_m, energy_wh, oxygen_l, time_s })), want.agents);
      cmp('time', got.time.sim_s, round(endT, 1));
    }
    const explains = want.last_event_detail ? page.text.includes(want.last_event_detail) : null;
    phases.push({
      checkpoint: cp.name, t_s: round(cp.t, 3), slider_value: sliderValue, matches_package: diffs.length === 0, differences: diffs,
      viewer: { mission: got.mission, active_route: got.active_route, invalidated_routes: got.invalidated_routes, agents: got.agents, recent_events: got.recent_events, time: got.time },
      latest_event_detail_visible: explains, text_has: page.text_has,
      screenshot: await shot(`recorded-${cp.name}`),
    });
  }
  return { events_tab_opened: tab, storage_at_open: storageAtOpen, webgl_renderer: renderer, label: opened.label, disclaimer: opened.disclaimer, about: opened.about, title: opened.title, storage_keys_after: opened.storage_keys, phases };
});

check('recorded: opens in an off-the-record context with empty storage', recorded.cookies_before === 0 && recorded.storage_at_open.local === 0 && recorded.storage_at_open.session === 0 && recorded.storage_at_open.cookie === '', recorded.storage_at_open);
check('recorded: every request stays on the static origin', recorded.off_origin_requests.length === 0, recorded.off_origin_requests);
check('recorded: no WebSocket or EventSource opened', recorded.websocket_or_eventsource.length === 0, recorded.websocket_or_eventsource);
check('recorded: no failed or non-OK request', recorded.non_ok_same_origin.length === 0 && recorded.failed_requests.filter((f) => !f.canceled).length === 0, { non_ok: recorded.non_ok_same_origin, failed: recorded.failed_requests });
check('recorded: no evaluator/reference request', !recorded.requests.some((r) => /\/evaluator\/|reference\.json/i.test(r)));
check('recorded: no uncaught page exception', recorded.page_exceptions.length === 0, recorded.page_exceptions);
check('recorded: label is REPLAY with the recorded producer', recorded.label === `REPLAY · ${pkgManifest.source_mode}`, recorded.label);
for (const p of recorded.phases) {
  check(`recorded/${p.checkpoint}: IDs, decisions and results match the package`, p.matches_package, p.differences);
  check(`recorded/${p.checkpoint}: REPLAY label and Offline shown, no LIVE claim`, p.text_has.replay_label && p.text_has.offline && !p.text_has.live_claim, p.text_has);
  if (p.latest_event_detail_visible !== null) check(`recorded/${p.checkpoint}: latest recorded event explanation is on screen`, p.latest_event_detail_visible);
}

// ---- window 2: the default entry a visitor gets (the simulated demo), in a second private window
const visitor = await privateWindow('default-entry', `${ORIGIN}/?nointro=1`, async ({ evaluate, waitFor, shot }) => {
  await waitFor('!!(window.mge && window.mge.state)', 'the viewer to open the default run');
  await sleep(2500);
  const page = await evaluate(READ_PAGE);
  const start = page.state.time.sim_s;
  await evaluate(`document.querySelector('button[aria-label="Play"]').click()`);
  // Software rendering can take seconds per frame on the full demo scene, so wait for the
  // clock to move instead of assuming a frame rate; the wait is recorded.
  const clicked = Date.now();
  await waitFor(`window.mge.state().time.sim_s > ${start}`, 'the replay clock to advance after Play', 60000);
  const later = await evaluate('window.mge.state().time');
  return {
    label: page.label, disclaimer: page.disclaimer, title: page.title, run_id: page.state.source.run_id, text_has: page.text_has,
    plays: { from_s: start, to_s: later.sim_s, playing: later.playing, waited_ms: Date.now() - clicked },
    screenshot: await shot('default-entry'),
  };
});
check('default: every request stays on the static origin', visitor.off_origin_requests.length === 0, visitor.off_origin_requests);
check('default: no WebSocket or EventSource opened', visitor.websocket_or_eventsource.length === 0, visitor.websocket_or_eventsource);
check('default: no failed or non-OK request', visitor.non_ok_same_origin.length === 0 && visitor.failed_requests.filter((f) => !f.canceled).length === 0, { non_ok: visitor.non_ok_same_origin, failed: visitor.failed_requests });
check('default: no evaluator/reference request', !visitor.requests.some((r) => /\/evaluator\/|reference\.json/i.test(r)));
check('default: no uncaught page exception', visitor.page_exceptions.length === 0, visitor.page_exceptions);
check('default: label is REPLAY · SIMULATION, Offline, no LIVE claim', visitor.label === 'REPLAY · SIMULATION' && visitor.text_has.replay_label && visitor.text_has.offline && !visitor.text_has.live_claim, { label: visitor.label, ...visitor.text_has });
check('default: the replay plays without a backend', visitor.plays.playing && visitor.plays.to_s > visitor.plays.from_s, visitor.plays);

// ---- window 3: asking for the evaluator view on the public build must find no reference
const evaluator = await privateWindow('evaluator-probe', `${ORIGIN}/?run=${RECORDED_ENTRY}&evaluator=1`, async ({ evaluate, waitFor }) => {
  await waitFor('!!(window.mge && window.mge.state)', 'the viewer to open with ?evaluator=1');
  await sleep(1000);
  const text = await evaluate('document.body.innerText');
  return { reference_layer_offered: /Reference DEM|Evaluator reference|reference \(evaluator\)/i.test(text) };
});
const probe = evaluator.requests.filter((r) => /\/evaluator\//i.test(r));
check('evaluator probe: the public build answers 404 for the reference', probe.length > 0 && probe.every((r) => r.startsWith('404 ')), probe);
check('evaluator probe: no reference layer is offered', !evaluator.reference_layer_offered);
check('evaluator probe: the viewer still opens as REPLAY', evaluator.page_exceptions.length === 0);

check('build: no evaluator/reference/HiRISE-named file in dist', hiddenNamed.length === 0, hiddenNamed);
check('server: only GET file requests were answered', served.every((s) => s.method === 'GET'));

// ---------------------------------------------------------------- environment and write-up
ws.close();
chrome.kill();
await new Promise((r) => chrome.on('exit', r));
server.close();
rmSync(profile, { recursive: true, force: true });

const sh = (cmd, a) => {
  try {
    return execFileSync(cmd, a, { encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
};
const backendPattern = 'ros2|rosbridge|gz sim|gzserver|ign gazebo|mge_gateway|mge_mission|mge_planning|replay_recorder|colcon';
const backendProcesses = (sh('pgrep', ['-af', backendPattern]) ?? '').split('\n').filter((l) => l && !l.includes('pgrep'));
check('host: no ROS, Gazebo, gateway, planner or recorder process running', backendProcesses.length === 0, backendProcesses);

const indexHtml = readFileSync(join(DIST, 'index.html'), 'utf8');
const summary = {
  schema: 'mge.private-browser-replay-check/1',
  recorded_at_utc: new Date().toISOString(),
  ai_disclosure: 'Script and write-up AI-assisted (Claude Code, Anthropic). No mission data, observation or result generated; see docs/AI_USAGE.md.',
  result: checks.every((c) => c.pass) ? 'PASS' : 'FAIL',
  checks_passed: checks.filter((c) => c.pass).length,
  checks_total: checks.length,
  browser: {
    product: browserVersion.product, user_agent: browserVersion.userAgent,
    mode: `${HEADED ? 'headed' : 'headless (--headless=new)'} Chromium, --incognito, fresh empty --user-data-dir, one new off-the-record browser context per window`,
    automation: 'Driven over the DevTools protocol by this script; no person operated the browser',
    webgl_renderer: recorded.webgl_renderer, viewport: VIEWPORT,
  },
  host: { os: sh('uname', ['-sr']), node: process.version },
  site: {
    served_from: 'file-only static server in this script, 127.0.0.1, GET only',
    build_entry_script: /assets\/index-[\w-]+\.js/.exec(indexHtml)?.[0] ?? null,
    dist_file_count: distFiles.length,
    index_html_sha256: sha256(readFileSync(join(DIST, 'index.html'))),
  },
  source_commit: sh('git', ['-C', DIST, 'rev-parse', 'HEAD']),
  media: SCREENSHOTS ? 'Local PNG captures written; not publishable without a visible AI-generated mark' : 'No screenshot, video or audio written',
  recorded_package: {
    entry: RECORDED_ENTRY, run_id: pkgManifest.run_id, source_mode: pkgManifest.source_mode, recorded_from: pkgManifest.recorded_from,
    record_count: records.length, event_count: eventRecs.length, duration_s: endT, sha256: pkgHashes,
    route_ids: [...new Set(stateRecs.map((r) => r.state.route_id).filter(Boolean))],
  },
  backend_check: {
    process_pattern: backendPattern, matching_processes: backendProcesses,
    note: 'Local listening ports are not recorded (unrelated workstation services). The browser network log is the record that the page contacted only the static origin.',
  },
  checks,
  not_claimed: [
    'AC-08 acceptance: Jorge and Jesus decide it; this is evidence input',
    'a person operating a visible private window (this run is automated' + (HEADED ? ')' : ' and headless)'),
    'public deployed-site or two-machine acceptance',
    'step 5 / C5 same-run replay of an integrated three-role mission (step 4 is still open)',
    'scientific mission COMPLETE, approved costs or scientific model agreement',
    'a LIVE mission or live gateway link',
  ],
};
writeFileSync(join(OUT, 'result.json'), `${JSON.stringify(summary, null, 2)}\n`);
writeFileSync(join(OUT, 'windows.json'), `${JSON.stringify({ recorded, default_entry: visitor, evaluator_probe: evaluator, static_server_log: served }, null, 2)}\n`);

for (const c of checks) console.log(`${c.pass ? 'PASS' : 'FAIL'}  ${c.name}${c.pass || c.detail === undefined ? '' : `\n      ${JSON.stringify(c.detail).slice(0, 600)}`}`);
console.log(`\n${summary.result}: ${summary.checks_passed}/${summary.checks_total} checks. Output: ${relative(process.cwd(), OUT) || '.'}`);
process.exit(summary.result === 'PASS' ? 0 : 1);
