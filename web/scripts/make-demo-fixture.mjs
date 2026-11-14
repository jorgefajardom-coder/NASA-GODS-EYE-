#!/usr/bin/env node
/**
 * Generates the demo replay fixture in public/replay/demo/ on REAL terrain.
 *
 * Terrain: the 2 km crop of the Mars 2020 TRN CTX DTM in scripts/data/ctx_crop.json
 * (see extract-ctx-crop.mjs). Heights are real; the local z origin is shifted by
 * `local_z_offset_m` so values stay near zero.
 *
 * What is SIMULATED or SYNTHETIC here (and labelled as such in the manifest):
 *  - the mission (agents, times, budgets, consumption rates): illustrative values;
 *  - the routes: produced by a slope-constrained grid search that stands in for the
 *    route planner. The viewer never searches for paths;
 *  - the adverse case: a scarp ADDED to the hidden evaluator reference. It does not
 *    exist in the CTX data. A drone survey reveals it and invalidates route r1;
 *  - POIs C and D are fictitious sites.
 *
 * Frames are written every 2 s of simulated time; the viewer interpolates visually
 * between samples and never extrapolates.
 *
 * Run: npm run fixture
 */
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, '..', 'public', 'replay', 'demo');
const RUN_ID = 'demo-sim-002';
const SCHEMA = 'mge-web-0.1-draft';
const DT = 2;

// ------------------------------------------------------------------ terrain
const crop = JSON.parse(readFileSync(join(HERE, 'data', 'ctx_crop.json'), 'utf8'));
const { rows: ROWS, cols: COLS, resolution_m: RES, origin_x_m: OX, origin_y_m: OY, local_z_offset_m: ZOFF } = crop.crop;
const N = ROWS * COLS;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const r1d = (v) => Math.round(v * 10) / 10;
const r2d = (v) => Math.round(v * 100) / 100;
const even = (s) => Math.ceil(s / DT) * DT;

const prior = crop.heights.map((h) => (h == null ? null : r1d(h - ZOFF)));
const center = (r, c) => ({ x: OX + (c + 0.5) * RES, y: OY + (r + 0.5) * RES });
const cellOf = (x, y) => ({ r: clamp(Math.floor((y - OY) / RES), 0, ROWS - 1), c: clamp(Math.floor((x - OX) / RES), 0, COLS - 1) });

function heightAt(grid, x, y) {
  const fc = (x - OX) / RES - 0.5;
  const fr = (y - OY) / RES - 0.5;
  const c0 = clamp(Math.floor(fc), 0, COLS - 1);
  const r0 = clamp(Math.floor(fr), 0, ROWS - 1);
  const c1 = Math.min(COLS - 1, c0 + 1);
  const r1 = Math.min(ROWS - 1, r0 + 1);
  const tc = clamp(fc - c0, 0, 1);
  const tr = clamp(fr - r0, 0, 1);
  const g = (r, c) => grid[r * COLS + c] ?? 0;
  const s = g(r0, c0) * (1 - tc) + g(r0, c1) * tc;
  const n = g(r1, c0) * (1 - tc) + g(r1, c1) * tc;
  return s * (1 - tr) + n * tr;
}

function slopes(grid) {
  const s = new Float32Array(N);
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const self = grid[r * COLS + c] ?? 0;
      const h = (rr, cc) => grid[clamp(rr, 0, ROWS - 1) * COLS + clamp(cc, 0, COLS - 1)] ?? self;
      const dx = (h(r, c + 1) - h(r, c - 1)) / (2 * RES);
      const dy = (h(r + 1, c) - h(r - 1, c)) / (2 * RES);
      s[r * COLS + c] = (Math.atan(Math.hypot(dx, dy)) * 180) / Math.PI;
    }
  }
  return s;
}

// ------------------------------------------------------------------ geometry helpers
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const len = (pts) => pts.slice(1).reduce((s, p, k) => s + dist(p, pts[k]), 0);
function pointAlong(pts, d) {
  let rem = Math.max(0, d);
  for (let k = 1; k < pts.length; k++) {
    const seg = dist(pts[k], pts[k - 1]);
    if (rem <= seg || k === pts.length - 1) {
      const t = seg === 0 ? 0 : Math.min(1, rem / seg);
      return {
        x: pts[k - 1].x + t * (pts[k].x - pts[k - 1].x),
        y: pts[k - 1].y + t * (pts[k].y - pts[k - 1].y),
        heading: Math.atan2(pts[k].y - pts[k - 1].y, pts[k].x - pts[k - 1].x),
      };
    }
    rem -= seg;
  }
  return { ...pts[0], heading: 0 };
}
function distToSegment(p, a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const t = clamp(((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy), 0, 1);
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}
function dropCollinear(pts) {
  const out = [pts[0]];
  for (let k = 1; k < pts.length - 1; k++) {
    const a = out[out.length - 1];
    const b = pts[k];
    const c = pts[k + 1];
    if (Math.abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) > 1e-6) out.push(b);
  }
  out.push(pts[pts.length - 1]);
  return out;
}

// ------------------------------------------------------------------ grid search (planner stand-in)
class Heap {
  constructor() {
    this.a = [];
  }
  push(f, i) {
    const a = this.a;
    a.push([f, i]);
    let k = a.length - 1;
    while (k > 0) {
      const p = (k - 1) >> 1;
      if (a[p][0] <= a[k][0]) break;
      [a[p], a[k]] = [a[k], a[p]];
      k = p;
    }
  }
  pop() {
    const a = this.a;
    const top = a[0];
    const last = a.pop();
    if (a.length) {
      a[0] = last;
      let k = 0;
      for (;;) {
        const l = 2 * k + 1;
        const r = l + 1;
        let m = k;
        if (l < a.length && a[l][0] < a[m][0]) m = l;
        if (r < a.length && a[r][0] < a[m][0]) m = r;
        if (m === k) break;
        [a[m], a[k]] = [a[k], a[m]];
        k = m;
      }
    }
    return top;
  }
  get size() {
    return this.a.length;
  }
}

/** 8-neighbour search. Hard constraint: slope above the limit or NoData is never entered. No corner cutting. */
function search(grid, sigma, limitDeg, from, to) {
  const sl = slopes(grid);
  const blocked = (r, c) => grid[r * COLS + c] == null || sl[r * COLS + c] > limitDeg;
  const a = cellOf(from.x, from.y);
  const b = cellOf(to.x, to.y);
  if (blocked(a.r, a.c) || blocked(b.r, b.c)) return null;
  const g = new Float64Array(N).fill(Infinity);
  const came = new Int32Array(N).fill(-1);
  const done = new Uint8Array(N);
  const heap = new Heap();
  const s = a.r * COLS + a.c;
  const t = b.r * COLS + b.c;
  g[s] = 0;
  heap.push(RES * Math.hypot(a.r - b.r, a.c - b.c), s);
  const dirs = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [-1, 1], [1, -1], [1, 1]];
  while (heap.size) {
    const [, i] = heap.pop();
    if (done[i]) continue;
    done[i] = 1;
    if (i === t) break;
    const r = Math.floor(i / COLS);
    const c = i % COLS;
    for (const [dr, dc] of dirs) {
      const rr = r + dr;
      const cc = c + dc;
      if (rr < 0 || cc < 0 || rr >= ROWS || cc >= COLS || blocked(rr, cc)) continue;
      if (dr !== 0 && dc !== 0 && (blocked(r + dr, c) || blocked(r, c + dc))) continue;
      const j = rr * COLS + cc;
      const step = RES * (dr !== 0 && dc !== 0 ? Math.SQRT2 : 1);
      const cost = step * (1 + (sl[i] + sl[j]) / 40) + (sigma[j] > 2 ? 0.25 * step : 0);
      if (g[i] + cost < g[j]) {
        g[j] = g[i] + cost;
        came[j] = i;
        heap.push(g[j] + RES * Math.hypot(rr - b.r, cc - b.c), j);
      }
    }
  }
  if (!done[t]) return null;
  const cells = [];
  for (let i = t; i !== -1; i = came[i]) cells.push(i);
  cells.reverse();
  return dropCollinear(cells.map((i) => center(Math.floor(i / COLS), i % COLS)));
}

function nearestFree(grid, limitDeg, x, y) {
  const sl = slopes(grid);
  const o = cellOf(x, y);
  for (let rad = 0; rad < 12; rad++) {
    for (let dr = -rad; dr <= rad; dr++) {
      for (let dc = -rad; dc <= rad; dc++) {
        const r = o.r + dr;
        const c = o.c + dc;
        if (r < 0 || c < 0 || r >= ROWS || c >= COLS || Math.max(Math.abs(dr), Math.abs(dc)) !== rad) continue;
        if (grid[r * COLS + c] != null && sl[r * COLS + c] < limitDeg * 0.6) return center(r, c);
      }
    }
  }
  throw new Error('no free cell near ' + x + ',' + y);
}

// ------------------------------------------------------------------ illustrative profiles
const HUMAN = { id: 'human_1', speed: 1.0, slope: 20, time_budget_s: 14400, energy_budget_wh: 2500, oxygen_budget_l: 1000, wh_moving: 0.3, wh_idle: 0.12, l_per_s: 0.05 };
const DRONE = { id: 'drone_1', speed: 8.0, altitude_m: 40, time_budget_s: 600, energy_budget_wh: 100, wh_per_s: 0.45 };
const ROVER = { id: 'rover_1', speed: 1.0, slope: 15, time_budget_s: 14400, energy_budget_wh: 2000, wh_moving: 1.0, wh_idle: 0.05, reserve_fraction: 0.2 };
const SERVICE_B_S = 120;
const SERVICE_C_S = 60;
const FOOTPRINT_M = 70;
const WALL_HALF_M = 130;
const WALL_SIGMA_M = 22;
const WALL_HEIGHT_M = 38;

const sigma1 = new Float32Array(N).fill(1.0);

// ------------------------------------------------------------------ A, B and route r1 on the orbital prior
const slPrior = slopes(prior);
const free = (r, c, lim) => prior[r * COLS + c] != null && slPrior[r * COLS + c] < lim;
function candidates(r0, r1, c0, c1, lim) {
  const out = [];
  for (let r = r0; r < r1; r++) for (let c = c0; c < c1; c++) if (free(r, c, lim)) out.push({ r, c, s: slPrior[r * COLS + c] });
  return out.sort((a, b) => a.s - b.s).slice(0, 6).map((k) => center(k.r, k.c));
}
let A = null;
let B = null;
let r1Out = null;
outer: for (const a of candidates(8, 40, 62, 94, 5)) {
  for (const b of candidates(58, 92, 6, 38, 6)) {
    const p = search(prior, sigma1, HUMAN.slope, a, b);
    if (p && len(p) > 1300 && len(p) < 2300) {
      A = a;
      B = b;
      r1Out = p;
      break outer;
    }
  }
}
if (!r1Out) throw new Error('no base/goal pair with a 1.3-2.3 km admissible route on the prior');
const L1 = len(r1Out);
const W = pointAlong(r1Out, 0.45 * L1);
const tang = { x: Math.cos(W.heading), y: Math.sin(W.heading) };
const norm = { x: -tang.y, y: tang.x };

// ------------------------------------------------------------------ synthetic adverse scarp (evaluator reference only)
const reference = prior.map((h, i) => {
  if (h == null) return null;
  const r = Math.floor(i / COLS);
  const c = i % COLS;
  const p = center(r, c);
  const d = (p.x - W.x) * tang.x + (p.y - W.y) * tang.y; // across the wall
  const s = (p.x - W.x) * norm.x + (p.y - W.y) * norm.y; // along the wall
  const fade = Math.abs(s) <= WALL_HALF_M ? 1 : Math.exp(-(((Math.abs(s) - WALL_HALF_M) / 25) ** 2));
  return r1d(h + WALL_HEIGHT_M * Math.exp(-(d * d) / (2 * WALL_SIGMA_M ** 2)) * fade);
});

// Uncertainty of the orbital map: illustrative, larger around the crossing that the drone will survey.
for (let i = 0; i < N; i++) {
  const p = center(Math.floor(i / COLS), i % COLS);
  if (dist(p, W) < 170) sigma1[i] = 3.0;
}

// ------------------------------------------------------------------ drone survey and map update
const S0 = { x: W.x - norm.x * (WALL_HALF_M + 40), y: W.y - norm.y * (WALL_HALF_M + 40) };
const S1 = { x: W.x + norm.x * (WALL_HALF_M + 40), y: W.y + norm.y * (WALL_HALF_M + 40) };
const observed = [];
const belief2 = prior.slice();
const sigma2 = Float32Array.from(sigma1);
for (let i = 0; i < N; i++) {
  if (prior[i] == null) continue;
  const p = center(Math.floor(i / COLS), i % COLS);
  if (distToSegment(p, S0, S1) <= FOOTPRINT_M) {
    observed.push(i);
    belief2[i] = reference[i];
    sigma2[i] = 0.2;
  }
}
const slBelief2 = slopes(belief2);
const forbidden2 = [];
for (let i = 0; i < N; i++) if (slBelief2[i] > HUMAN.slope) forbidden2.push(center(Math.floor(i / COLS), i % COLS));
let maxSlopeObserved = 0;
for (const i of observed) maxSlopeObserved = Math.max(maxSlopeObserved, slBelief2[i]);

// r1 must really cross the wall, otherwise the story is not true.
function crossesForbidden(pts) {
  for (let d = 0; d <= len(pts); d += RES / 4) {
    const p = pointAlong(pts, d);
    const c = cellOf(p.x, p.y);
    if (slBelief2[c.r * COLS + c.c] > HUMAN.slope) return true;
  }
  return false;
}
if (!crossesForbidden(r1Out)) throw new Error('route r1 does not cross the scarp: adjust the wall');

// ------------------------------------------------------------------ timeline
const T_START = 10;
const DRONE_HOME = nearestFree(prior, 12, A.x - 70, A.y + 40);
const ROVER_HOME = nearestFree(prior, ROVER.slope, A.x + 40, A.y + 70);
const droneOut = [DRONE_HOME, S0];
const strip = [S0, S1];
const droneBack = [S1, DRONE_HOME];
const T_AT_S0 = even(T_START + len(droneOut) / DRONE.speed);
const T_OBS = even(T_AT_S0 + len(strip) / DRONE.speed);
const T_DRONE_HOME = even(T_OBS + DT + len(droneBack) / DRONE.speed);
const T_MAP = T_OBS + DT;
const T_INVALID = T_MAP + DT;
const T_R2 = T_INVALID + 6;

const armAtInvalid = (T_INVALID - T_START) * HUMAN.speed;
if (armAtInvalid > 0.45 * L1 - 120) throw new Error('astronaut would be too close to the scarp when the route is invalidated');
const poseInvalid = pointAlong(r1Out, armAtInvalid);
const P0 = { x: r2d(poseInvalid.x), y: r2d(poseInvalid.y) };

const mid = nearestFree(belief2, HUMAN.slope, P0.x, P0.y);
const r2OutCells = search(belief2, sigma2, HUMAN.slope, mid, B);
const r2RetCells = search(belief2, sigma2, HUMAN.slope, B, A);
if (!r2OutCells || !r2RetCells) throw new Error('no admissible route after the map update');
const r2Out = dropCollinear([P0, ...r2OutCells.filter((p, k) => k > 0 || dist(p, P0) > 1)]);
const r2Ret = r2RetCells;
r2Ret[r2Ret.length - 1] = { ...A };

const T_AT_B = even(T_R2 + len(r2Out) / HUMAN.speed);
const T_B_DONE = T_AT_B + SERVICE_B_S;
const T_HOME = even(T_B_DONE + len(r2Ret) / HUMAN.speed);
const T_END = T_HOME + 10;

// ------------------------------------------------------------------ POIs revealed by the survey (fictitious sites)
const roverSl = slBelief2;
const observedFree = observed.filter((i) => roverSl[i] < 8);
const sideOf = (i) => {
  const p = center(Math.floor(i / COLS), i % COLS);
  return (p.x - W.x) * tang.x + (p.y - W.y) * tang.y; // <0 = base side, >0 = goal side
};
function bestPoi(side) {
  let best = null;
  const pool = observedFree.filter((i) => (side < 0 ? sideOf(i) < -40 : sideOf(i) > 40)).filter((i) => i % 3 === 0);
  for (const i of pool) {
    const p = center(Math.floor(i / COLS), i % COLS);
    const path = search(belief2, sigma2, ROVER.slope, ROVER_HOME, p);
    if (!path) continue;
    const l = len(path);
    if (!best || (side < 0 ? l < best.l : l > best.l)) best = { p, l, path };
  }
  return best;
}
const C = bestPoi(-1);
const D = bestPoi(1);
if (!C || !D) throw new Error('could not place POIs inside the observed area');
const roverRoundTrip = (l) => (2 * l * ROVER.wh_moving) / ROVER.speed;
// Illustrative rover budget chosen so that C fits within a 20 % reserve and D does not.
ROVER.energy_budget_wh = Math.round(((roverRoundTrip(C.l) + roverRoundTrip(D.l)) / 2 / (1 - ROVER.reserve_fraction)) / 50) * 50;
const usable = ROVER.energy_budget_wh * (1 - ROVER.reserve_fraction);
if (!(roverRoundTrip(C.l) < usable && roverRoundTrip(D.l) > usable)) throw new Error('POI budget separation failed');

const T_ROVER_GO = T_R2 + DT;
const roverOut = C.path;
const roverBack = roverOut.slice().reverse();
const T_ROVER_AT_C = even(T_ROVER_GO + len(roverOut) / ROVER.speed);
const T_ROVER_DONE = T_ROVER_AT_C + SERVICE_C_S;
const T_ROVER_HOME = even(T_ROVER_DONE + len(roverBack) / ROVER.speed);

// ------------------------------------------------------------------ routes
function routeBudget(out, back, startT) {
  const travel = (len(out) + len(back)) / HUMAN.speed + SERVICE_B_S;
  const energy = travel * HUMAN.wh_moving;
  const oxygen = travel * HUMAN.l_per_s;
  return {
    travel_time_s: Math.round(travel),
    energy_est_wh: Math.round(energy),
    oxygen_est_l: Math.round(oxygen),
    reserve_time_s: Math.round(HUMAN.time_budget_s - startT - travel),
    reserve_wh: Math.round(HUMAN.energy_budget_wh - startT * HUMAN.wh_idle - energy),
    reserve_oxygen_l: Math.round(HUMAN.oxygen_budget_l - startT * HUMAN.l_per_s - oxygen),
  };
}
const withZ = (pts, grid) => pts.map((p) => ({ x: r2d(p.x), y: r2d(p.y), z: r2d(heightAt(grid, p.x, p.y)) }));
function minClearance(pts) {
  let best = Infinity;
  for (let d = 0; d <= len(pts); d += 10) {
    const p = pointAlong(pts, d);
    for (const f of forbidden2) best = Math.min(best, dist(p, f));
  }
  return r2d(best);
}
const r1Back = r1Out.slice().reverse();
const routes = [
  {
    timestamp_sim_s: 6, run_id: RUN_ID, request_id: 'req-001', route_id: 'r1', agent_id: HUMAN.id, mode: 'SAFE', map_version_used: 1,
    status: 'FEASIBLE', reason_code: 'PLANNED_ON_PRIOR',
    detail: 'Shortest admissible route on the orbital CTX map. The middle of the corridor has high uncertainty (sigma 3 m).',
    outbound_path: withZ(r1Out, prior), return_path: withZ(r1Back, prior), ...routeBudget(r1Out, r1Back, 0), min_clearance_m: null,
  },
  {
    timestamp_sim_s: T_R2, run_id: RUN_ID, request_id: 'req-002', route_id: 'r2', agent_id: HUMAN.id, mode: 'SAFE', map_version_used: 2,
    status: 'FEASIBLE', reason_code: 'REPLANNED_FROM_CURRENT_POSE',
    detail: 'Replanned from the astronaut position around the surveyed scarp. Return to base stays within budget.',
    outbound_path: withZ(r2Out, belief2), return_path: withZ(r2Ret, belief2), ...routeBudget(r2Out, r2Ret, T_R2), min_clearance_m: minClearance(r2Out),
  },
];

// ------------------------------------------------------------------ agent motion
function yawQuat(yaw) {
  return { x: 0, y: 0, z: Math.round(Math.sin(yaw / 2) * 1000) / 1000, w: Math.round(Math.cos(yaw / 2) * 1000) / 1000 };
}
/** segs: [{ t0, t1, mode, pts? }]. Move segments follow pts at `speed`; static segments hold the last pose. */
function evalSegs(segs, t, speed, startPose) {
  let pose = startPose;
  let mode = segs[0].mode;
  for (const s of segs) {
    if (t < s.t0) break;
    mode = s.mode;
    if (s.pts) {
      const d = Math.min((Math.min(t, s.t1) - s.t0) * speed, len(s.pts));
      pose = pointAlong(s.pts, d);
    }
  }
  return { pose, mode };
}
function timeIn(segs, t, modes) {
  let sum = 0;
  for (const s of segs) if (modes.has(s.mode)) sum += Math.max(0, Math.min(t, s.t1) - s.t0);
  return sum;
}
const MOVING = new Set(['MOVING', 'RETURNING']);

const humanSegs = [
  { t0: 0, t1: T_START, mode: 'IDLE' },
  { t0: T_START, t1: T_INVALID, mode: 'MOVING', pts: r1Out },
  { t0: T_INVALID, t1: T_R2, mode: 'HALTED', pts: [P0, P0] },
  { t0: T_R2, t1: T_AT_B, mode: 'MOVING', pts: r2Out },
  { t0: T_AT_B, t1: T_B_DONE, mode: 'WORKING' },
  { t0: T_B_DONE, t1: T_HOME, mode: 'RETURNING', pts: r2Ret },
  { t0: T_HOME, t1: Infinity, mode: 'IDLE' },
];
const droneSegs = [
  { t0: 0, t1: T_START, mode: 'IDLE' },
  { t0: T_START, t1: T_AT_S0, mode: 'MOVING', pts: droneOut },
  { t0: T_AT_S0, t1: T_OBS, mode: 'OBSERVING', pts: strip },
  { t0: T_OBS, t1: T_OBS + DT, mode: 'OBSERVING' },
  { t0: T_OBS + DT, t1: T_DRONE_HOME, mode: 'RETURNING', pts: droneBack },
  { t0: T_DRONE_HOME, t1: Infinity, mode: 'IDLE' },
];
const roverSegs = [
  { t0: 0, t1: T_ROVER_GO, mode: 'IDLE' },
  { t0: T_ROVER_GO, t1: T_ROVER_AT_C, mode: 'MOVING', pts: roverOut },
  { t0: T_ROVER_AT_C, t1: T_ROVER_DONE, mode: 'WORKING' },
  { t0: T_ROVER_DONE, t1: T_ROVER_HOME, mode: 'RETURNING', pts: roverBack },
  { t0: T_ROVER_HOME, t1: Infinity, mode: 'IDLE' },
];
const heading0 = (to) => Math.atan2(to.y - A.y, to.x - A.x);

function humanAt(t) {
  const { pose, mode } = evalSegs(humanSegs, t, HUMAN.speed, { ...A, heading: heading0(B) });
  const moving = timeIn(humanSegs, t, MOVING);
  const working = timeIn(humanSegs, t, new Set(['WORKING']));
  const idle = t - moving - working;
  return {
    id: HUMAN.id, kind: 'HUMAN', mode, pose, z: heightAt(reference, pose.x, pose.y),
    time: HUMAN.time_budget_s - t,
    energy: HUMAN.energy_budget_wh - (moving + working) * HUMAN.wh_moving - idle * HUMAN.wh_idle,
    oxygen: HUMAN.oxygen_budget_l - t * HUMAN.l_per_s,
  };
}
function droneAt(t) {
  const { pose, mode } = evalSegs(droneSegs, t, DRONE.speed, { ...DRONE_HOME, heading: 0.7 });
  const flying = timeIn(droneSegs, t, new Set(['MOVING', 'OBSERVING', 'RETURNING']));
  return {
    id: DRONE.id, kind: 'DRONE', mode, pose, z: heightAt(reference, pose.x, pose.y) + (mode === 'IDLE' ? 0 : DRONE.altitude_m),
    time: DRONE.time_budget_s - flying, energy: DRONE.energy_budget_wh - flying * DRONE.wh_per_s, oxygen: null,
  };
}
function roverAt(t) {
  const { pose, mode } = evalSegs(roverSegs, t, ROVER.speed, { ...ROVER_HOME, heading: 0.7 });
  const moving = timeIn(roverSegs, t, MOVING);
  const working = timeIn(roverSegs, t, new Set(['WORKING']));
  return {
    id: ROVER.id, kind: 'ROVER', mode, pose, z: heightAt(reference, pose.x, pose.y),
    time: ROVER.time_budget_s - t,
    energy: ROVER.energy_budget_wh - (moving + working) * ROVER.wh_moving - (t - moving - working) * ROVER.wh_idle,
    oxygen: null,
  };
}
const toAgentState = (t, a) => ({
  timestamp_sim_s: t, run_id: RUN_ID, agent_id: a.id, agent_kind: a.kind,
  pose: { position: { x: r2d(a.pose.x), y: r2d(a.pose.y), z: r2d(a.z) }, orientation: yawQuat(a.pose.heading ?? 0) },
  mode: a.mode,
  time_remaining_s: Math.round(a.time),
  energy_remaining_wh: r2d(a.energy),
  oxygen_remaining_l: a.oxygen == null ? null : r2d(a.oxygen),
  confidence: 0.95,
});

// ------------------------------------------------------------------ events
let seq = 0;
const events = [];
const ev = (t, type, f) => {
  seq += 1;
  events.push({
    timestamp_sim_s: t, event_id: `ev-${String(seq).padStart(3, '0')}`, seq, run_id: RUN_ID, causality_id: '', event_type: type,
    task_id: '', agent_id: '', map_version: t >= T_MAP ? 2 : 1, route_id: '', previous_state: '', new_state: '', reason_code: '', detail: '', ...f,
  });
  return events[events.length - 1].event_id;
};
const wh = (v) => `${Math.round(v)} Wh`;
const goalOk = ev(2, 'GOAL_ACCEPTED', { causality_id: 'req-001', agent_id: HUMAN.id, task_id: 'main:reach', reason_code: 'GOAL_SET', detail: 'Primary goal B accepted for the astronaut, with return to base A.' });
ev(2, 'MISSION_STATE_CHANGED', { causality_id: goalOk, previous_state: 'IDLE', new_state: 'PLANNING', reason_code: 'GOAL_SET', detail: 'Planning route A to B and back.' });
const r1Pub = ev(6, 'ROUTE_PUBLISHED', { causality_id: goalOk, route_id: 'r1', agent_id: HUMAN.id, new_state: 'FEASIBLE', reason_code: 'PLANNED_ON_PRIOR', detail: 'Route r1 published on map v1 (orbital CTX map only). The corridor is still uncertain.' });
ev(T_START, 'MISSION_STATE_CHANGED', { causality_id: r1Pub, previous_state: 'PLANNING', new_state: 'ACTIVE', reason_code: 'ROUTE_READY', detail: 'Astronaut departs from base A on route r1.' });
const surveyId = ev(T_START, 'TASK_DISCOVERED', { causality_id: r1Pub, task_id: 'survey:corridor', agent_id: DRONE.id, new_state: 'DISCOVERED', reason_code: 'HIGH_UNCERTAINTY_ON_ROUTE', detail: 'Route r1 crosses cells with sigma 3 m. Drone reconnaissance requested.' });
ev(T_START + DT, 'TASK_STATE_CHANGED', { causality_id: surveyId, task_id: 'survey:corridor', agent_id: DRONE.id, previous_state: 'DISCOVERED', new_state: 'EXECUTING', reason_code: 'ASSIGNED_TO_DRONE', detail: 'Drone flies over the corridor.' });
ev(T_OBS, 'TASK_STATE_CHANGED', { causality_id: 'obs-001', task_id: 'survey:corridor', agent_id: DRONE.id, previous_state: 'EXECUTING', new_state: 'DONE', reason_code: 'OBSERVATION_RECEIVED', detail: `Observation obs-001 covers ${observed.length} cells across the corridor.` });
const mapUpd = ev(T_MAP, 'MAP_UPDATED', { causality_id: 'obs-001', agent_id: DRONE.id, map_version: 2, reason_code: 'OBSERVATION_APPLIED', detail: `Map v2: drone saw a scarp across the corridor with local slope up to ${Math.round(maxSlopeObserved)}° (illustrative human limit ${HUMAN.slope}°).` });
const cFound = ev(T_MAP, 'TASK_DISCOVERED', { causality_id: 'obs-001', task_id: 'inspect:C', new_state: 'DISCOVERED', reason_code: 'SITE_OBSERVED', detail: 'Drone image shows a layered outcrop at POI C (fictitious site).' });
const dFound = ev(T_MAP + DT, 'TASK_DISCOVERED', { causality_id: 'obs-001', task_id: 'inspect:D', new_state: 'DISCOVERED', reason_code: 'SITE_OBSERVED', detail: 'Drone image shows a dark-toned deposit at POI D (fictitious site).' });
const inval = ev(T_INVALID, 'ROUTE_INVALIDATED', { causality_id: mapUpd, route_id: 'r1', agent_id: HUMAN.id, previous_state: 'FEASIBLE', new_state: 'NO_PATH', reason_code: 'HAZARD_ON_ROUTE', detail: `Route r1 crosses the scarp seen in map v2 (slope above ${HUMAN.slope}°). Astronaut halted at the current position.` });
ev(T_INVALID, 'MISSION_STATE_CHANGED', { causality_id: inval, previous_state: 'ACTIVE', new_state: 'REPLAN', reason_code: 'HAZARD_ON_ROUTE', detail: 'Replanning from the astronaut position.' });
const r2Pub = ev(T_R2, 'ROUTE_PUBLISHED', { causality_id: inval, route_id: 'r2', agent_id: HUMAN.id, new_state: 'FEASIBLE', reason_code: 'REPLANNED_FROM_CURRENT_POSE', detail: `Route r2 goes around the scarp. Round trip ${routes[1].travel_time_s - routes[0].travel_time_s >= 0 ? '+' : ''}${routes[1].travel_time_s - routes[0].travel_time_s} s versus r1, still within budget.` });
ev(T_R2, 'MISSION_STATE_CHANGED', { causality_id: r2Pub, previous_state: 'REPLAN', new_state: 'ACTIVE', reason_code: 'ROUTE_READY', detail: 'Astronaut resumes on route r2.' });
ev(T_ROVER_GO, 'TASK_STATE_CHANGED', { causality_id: cFound, task_id: 'inspect:C', agent_id: ROVER.id, previous_state: 'DISCOVERED', new_state: 'ASSIGNED', reason_code: 'FEASIBLE_WITHIN_BUDGET', detail: `Rover round trip to C needs about ${wh(roverRoundTrip(C.l))}, within the usable ${wh(usable)} (20 % reserve kept).` });
ev(T_ROVER_GO + DT, 'TASK_STATE_CHANGED', { causality_id: dFound, task_id: 'inspect:D', previous_state: 'DISCOVERED', new_state: 'REJECTED', reason_code: 'INSUFFICIENT_BUDGET', detail: `Rover round trip to D needs about ${wh(roverRoundTrip(D.l))} around the scarp, above the usable ${wh(usable)} (20 % reserve kept). Not assigned.` });
ev(T_ROVER_AT_C, 'TASK_STATE_CHANGED', { causality_id: cFound, task_id: 'inspect:C', agent_id: ROVER.id, previous_state: 'ASSIGNED', new_state: 'EXECUTING', reason_code: 'ARRIVED', detail: 'Rover inspecting POI C.' });
ev(T_ROVER_DONE, 'TASK_STATE_CHANGED', { causality_id: cFound, task_id: 'inspect:C', agent_id: ROVER.id, previous_state: 'EXECUTING', new_state: 'DONE', reason_code: 'INSPECTION_COMPLETE', detail: 'Inspection of C complete. Sampling not requested in this run.' });
ev(T_AT_B, 'TASK_STATE_CHANGED', { causality_id: goalOk, task_id: 'main:reach', agent_id: HUMAN.id, previous_state: 'ASSIGNED', new_state: 'EXECUTING', reason_code: 'ARRIVED', detail: 'Astronaut reached goal B and starts the science task.' });
ev(T_B_DONE, 'TASK_STATE_CHANGED', { causality_id: goalOk, task_id: 'main:reach', agent_id: HUMAN.id, previous_state: 'EXECUTING', new_state: 'DONE', reason_code: 'PRIMARY_GOAL_COMPLETE', detail: 'Primary goal B completed.' });
ev(T_B_DONE, 'MISSION_STATE_CHANGED', { causality_id: goalOk, previous_state: 'ACTIVE', new_state: 'RETURNING', reason_code: 'PRIMARY_GOAL_COMPLETE', detail: 'Returning to base A on the return leg of r2.' });
ev(T_HOME, 'MISSION_STATE_CHANGED', { causality_id: r2Pub, previous_state: 'RETURNING', new_state: 'COMPLETE', reason_code: 'RETURNED_TO_BASE', detail: 'Astronaut back at base A. Goal completed, return verified under the model, no budget violation.' });

// ------------------------------------------------------------------ frames
function missionAt(t) {
  if (t < 2) return { s: 'IDLE', route: '', task: '', kind: '', tstate: '' };
  if (t < 6) return { s: 'PLANNING', route: '', task: 'main:reach', kind: 'primary', tstate: 'ELIGIBLE' };
  if (t < T_START) return { s: 'PLANNING', route: 'r1', task: 'main:reach', kind: 'primary', tstate: 'ASSIGNED' };
  if (t < T_INVALID) return { s: 'ACTIVE', route: 'r1', task: 'main:reach', kind: 'primary', tstate: 'ASSIGNED' };
  if (t < T_R2) return { s: 'REPLAN', route: '', task: 'main:reach', kind: 'primary', tstate: 'ASSIGNED' };
  if (t < T_AT_B) return { s: 'ACTIVE', route: 'r2', task: 'main:reach', kind: 'primary', tstate: 'ASSIGNED' };
  if (t < T_B_DONE) return { s: 'ACTIVE', route: 'r2', task: 'main:reach', kind: 'primary', tstate: 'EXECUTING' };
  if (t < T_HOME) return { s: 'RETURNING', route: 'r2', task: 'return:base', kind: 'return', tstate: 'EXECUTING' };
  return { s: 'COMPLETE', route: 'r2', task: 'return:base', kind: 'return', tstate: 'DONE' };
}
const baseP = { x: A.x, y: A.y, z: r2d(heightAt(prior, A.x, A.y)) };
const goalP = { x: B.x, y: B.y, z: r2d(heightAt(prior, B.x, B.y)) };
const frames = [];
for (let t = 0; t <= T_END; t += DT) {
  const m = missionAt(t);
  const lastSeq = events.filter((e) => e.timestamp_sim_s <= t).reduce((s, e) => Math.max(s, e.seq), 0);
  frames.push({
    timestamp_sim_s: t,
    mission_state: {
      timestamp_sim_s: t, run_id: RUN_ID, last_event_seq: lastSeq, mission_state: m.s, reason_code: '', base: baseP, primary_goal: goalP,
      primary_agent_id: HUMAN.id, active_task_id: m.task, active_task_kind: m.kind, active_task_state: m.tstate,
      map_version: t >= T_MAP ? 2 : 1, route_id: m.route,
      agents: [humanAt(t), droneAt(t), roverAt(t)].map((a) => toAgentState(t, a)),
    },
  });
}

// ------------------------------------------------------------------ write
const priorJson = JSON.stringify(prior);
const cp = crop.crop;
const cpCells = [[14, 20], [50, 50], [84, 78]];
const manifest = {
  schema_version: SCHEMA,
  icd: 'ICD-ROS2-V1 (draft)',
  run_id: RUN_ID,
  mode: 'REPLAY',
  // ICD §6.1: who produced the run. The mission is a scripted simulation (not a planner or ROS run); never LIVE.
  source_mode: 'SIMULATION',
  provenance: ['nasa', 'simulated', 'fictitious'],
  illustrative: true,
  title: 'Demo run: corridor survey and replanning',
  summary: 'The drone surveys an uncertain corridor, finds a scarp, the first route is invalidated and the astronaut is replanned around it, reaches goal B and returns to base.',
  disclaimer: 'Terrain: NASA/USGS CTX DTM crop (real, provisional). Mission, budgets and the corridor scarp are simulated or synthetic; POIs are fictitious. Not EVA-certified limits, not a planner output.',
  ai_disclosure: {
    ai_assisted: true,
    scope: 'Fixture generator script and replay fixture structure; the simulated mission, routes and events are generated data, not observations.',
    tool: 'Claude (Anthropic) through Claude Code',
    observational_data: 'Only the terrain heights come from NASA/USGS data; everything else here is simulated.',
  },
  duration_s: T_END,
  local_z_offset_m: ZOFF,
  // Orbital image draped on the terrain (scripts/extract-ctx-ortho.mjs). Same CTX soc_008
  // production as the DTM, so it is part of the orbital prior, not of the hidden reference.
  imagery: {
    file: 'ctx_ortho.png',
    title: 'MRO CTX Jezero orthomosaic, controlled (Mars 2020 TRN)',
    source: 'JPL Mars Trek WMTS layer JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0, https://trek.nasa.gov/mars/',
    credit: 'NASA/JPL-Caltech/MSSS/USGS',
    native_resolution_m: 6,
    resolution_m: 5,
    extent: { origin_x_m: OX, origin_y_m: OY, width_m: COLS * RES, height_m: ROWS * RES },
    row0: 'north',
    processing: 'Bilinear resampling onto the crop ENU grid; display contrast stretched linearly between the 1st and 99th percentile. Panchromatic; the viewer tints it for display only.',
  },
  // Geologic units of the crop (scripts/extract-geology.mjs, USGS SIM 3464). Approximate boundaries.
  geology: { file: 'geology.json' },
  // Weather and radiation context (scripts/extract-atmosphere.mjs: MEDA, REMS, RAD). Display only.
  atmosphere: { file: 'atmosphere.json' },
  // Surroundings from the same CTX DTM (20 km, 100 m box average) and orthomosaic (40 m). Context only.
  context: { file: 'context.json', image: 'context_ortho.png' },
  terrain_meta: {
    run_id: RUN_ID, dataset_id: 'mars2020-trn-ctx-dtm-20m', frame_id: 'map', map_version: 1,
    origin_x_m: OX, origin_y_m: OY, resolution_m: RES, rows: ROWS, cols: COLS,
    crs: 'Local tangent ENU grid; source Equirectangular, Mars 2000 sphere IAU (R = 3396190 m)',
    origin_lat_deg: cp.centre_lat_deg, origin_lon_deg: cp.centre_lon_deg,
    vertical_datum: `MOLA areoid; local z = elevation - (${ZOFF} m)`,
    nodata_value: -32768,
    sources: [
      `${crop.source.title}, ${crop.source.provider}. File ${crop.source.file}, ${crop.source.size_bytes} bytes, SHA-256 ${crop.source.sha256}.`,
      `Product page ${crop.source.product_page} (DOI family ${crop.source.doi_family}). Native resolution ${crop.source.native_resolution_m} m. ${crop.source.licence}.`,
      `Crop: ${ROWS} x ${COLS} cells of ${RES} m centred at ${cp.centre_lat_deg} N, ${cp.centre_lon_deg} E, ${cp.method}. PROVISIONAL, made by the frontend until the data owner delivers the processed package.`,
      'SYNTHETIC: a scarp was added to the hidden evaluator reference to create an adverse case. It does not exist in the CTX data.',
      'ILLUSTRATIVE: uncertainty (sigma), budgets, speeds and consumption rates are assumptions of a simulated mission.',
    ],
    checksum_sha256: createHash('sha256').update(priorJson).digest('hex'),
  },
  vertical_exaggeration_default: 2,
  control_points: cpCells.map(([r, c], k) => {
    const p = center(r, c);
    return { id: `cp-${k + 1}`, position: { x: p.x, y: p.y, z: prior[r * COLS + c] }, description: `Cell centre row ${r}, col ${c} of the CTX crop.` };
  }),
  pois: [
    { id: 'A', label: 'Base A', kind: 'base', position: baseP, revealed_at_s: 0 },
    { id: 'B', label: 'Goal B', kind: 'primary_goal', position: goalP, revealed_at_s: 0 },
    // POI heights from the updated map, not from the hidden reference (R05).
    { id: 'C', label: 'POI C', kind: 'poi', position: { x: r2d(C.p.x), y: r2d(C.p.y), z: r2d(heightAt(belief2, C.p.x, C.p.y)) }, revealed_at_s: T_MAP },
    { id: 'D', label: 'POI D', kind: 'poi', position: { x: r2d(D.p.x), y: r2d(D.p.y), z: r2d(heightAt(belief2, D.p.x, D.p.y)) }, revealed_at_s: T_MAP + DT },
  ],
  files: { rasters: 'rasters.json', timeline: 'timeline.json', routes: 'routes.json' },
};

mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
writeFileSync(join(OUT, 'routes.json'), JSON.stringify({ run_id: RUN_ID, routes }, null, 2));
writeFileSync(join(OUT, 'timeline.json'), JSON.stringify({ schema_version: SCHEMA, run_id: RUN_ID, frames, events }));
writeFileSync(
  join(OUT, 'rasters.json'),
  JSON.stringify({
    run_id: RUN_ID, rows: ROWS, cols: COLS, prior,
    versions: {
      1: { belief: prior, sigma: Array.from(sigma1, r2d), observed: [] },
      2: { belief: belief2, sigma: Array.from(sigma2, r2d), observed },
    },
  }),
);
// The hidden evaluator reference never goes into the public fixture (R05). It is written to the
// repository's data/reference/ boundary, which Git ignores; only the dev server serves it, and only
// to the evaluator view (?evaluator=1). It is never copied into dist/.
const REF_DIR = join(HERE, '..', '..', 'data', 'reference', RUN_ID);
mkdirSync(REF_DIR, { recursive: true });
writeFileSync(
  join(REF_DIR, 'reference.json'),
  JSON.stringify({ run_id: RUN_ID, rows: ROWS, cols: COLS, note: 'Evaluator-only reference: CTX prior plus a SYNTHETIC scarp. Do not distribute.', reference }),
);
console.log(`terrain: ${ROWS}x${COLS} @ ${RES} m, local z offset ${ZOFF} m, relief ${cp.max_m - cp.min_m} m`);
console.log(`A->B route r1 ${Math.round(L1)} m, r2 out ${Math.round(len(r2Out))} m, r2 back ${Math.round(len(r2Ret))} m, clearance ${routes[1].min_clearance_m} m`);
console.log(`scarp: ${forbidden2.length} forbidden cells, max observed slope ${maxSlopeObserved.toFixed(1)} deg, ${observed.length} observed cells`);
console.log(`rover budget ${ROVER.energy_budget_wh} Wh; C ${Math.round(C.l)} m (${wh(roverRoundTrip(C.l))}), D ${Math.round(D.l)} m (${wh(roverRoundTrip(D.l))}), usable ${wh(usable)}`);
console.log(`times: obs ${T_OBS}s, invalid ${T_INVALID}s, replanned ${T_R2}s, at B ${T_AT_B}s, home ${T_HOME}s, end ${T_END}s, ${frames.length} frames, ${events.length} events`);
