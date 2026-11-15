import { useEffect, useMemo, useRef } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { Point } from '../types/icd';
import { tacticalBase, tacticalContext, type TacticalBase } from '../lib/tacticalMap';
import { yawFromQuaternion } from '../lib/coords';
import { headingFromNorth } from '../lib/management';
import { drawSiteIcon, siteKind } from '../lib/siteKinds';

const DEFAULT_SIZE = 168;

function toCanvas(b: TacticalBase): HTMLCanvasElement {
  const c = document.createElement('canvas');
  c.width = b.width;
  c.height = b.height;
  c.getContext('2d')!.putImageData(new ImageData(b.pixels, b.width, b.height), 0, 0);
  return c;
}
/** Ground radius shown around the agent (m). */
const RADIUS_M = 450;
const KIND_COLOR = { HUMAN: '#E8F4FF', DRONE: '#65CBE8', ROVER: '#D8AD66' } as const;

/** How far back the trails reach (s of replay time) and how often they are sampled. */
const TRAIL_S = 240;

/** Fading trail behind every agent: the last TRAIL_S seconds of its recorded positions. Display only. */
function drawTrails(g: CanvasRenderingContext2D, frames: ReplayBundle['timeline']['frames'], t: number, toPx: (p: Point) => readonly [number, number]): void {
  // Frames are in time order: find the first one inside the window.
  let lo = 0;
  let hi = frames.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].timestamp_sim_s < t - TRAIL_S) lo = mid + 1;
    else hi = mid;
  }
  const byAgent = new Map<string, { kind: keyof typeof KIND_COLOR; pts: Point[] }>();
  for (let i = lo; i < frames.length && frames[i].timestamp_sim_s <= t; i++) {
    for (const a of frames[i].mission_state.agents) {
      const e = byAgent.get(a.agent_id) ?? { kind: a.agent_kind, pts: [] };
      e.pts.push(a.pose.position);
      byAgent.set(a.agent_id, e);
    }
  }
  g.lineCap = 'round';
  g.lineJoin = 'round';
  for (const { kind, pts } of byAgent.values()) {
    if (pts.length < 2) continue;
    const n = pts.length;
    // Older stretches are fainter: draw the trail in a few segments of rising opacity.
    const parts = 4;
    for (let k = 0; k < parts; k++) {
      const a = Math.floor((k * (n - 1)) / parts);
      const b = Math.floor(((k + 1) * (n - 1)) / parts);
      g.strokeStyle = KIND_COLOR[kind];
      g.globalAlpha = 0.18 + (0.7 * (k + 1)) / parts;
      g.lineWidth = 1.6 + k * 0.5;
      g.beginPath();
      pts.slice(a, b + 1).forEach((p, j) => {
        const [x, y] = toPx(p);
        if (j) g.lineTo(x, y);
        else g.moveTo(x, y);
      });
      g.stroke();
    }
    g.globalAlpha = 1;
  }
}

/**
 * Game-style circular minimap, heading up (turns with the agent), centred on the selected agent: elevation bands,
 * coverage, the route in force, other agents and sites. Display only.
 */
export function Minimap({ bundle, view, agentId, size = DEFAULT_SIZE }: { bundle: ReplayBundle; view: ReplayView; agentId: string; size?: number }) {
  const SIZE = size;
  const canvas = useRef<HTMLCanvasElement>(null);
  const meta = bundle.manifest.terrain_meta;
  const mapVersion = view.state?.map_version ?? 1;
  const base = useMemo(() => tacticalBase(bundle.rasters, mapVersion), [bundle.rasters, mapVersion]);
  const baseCanvas = useMemo(() => toCanvas(base), [base]);
  // Surroundings of the crop (same DTM, coarser), so the map does not look cut near the crop's edge.
  const ctxCanvas = useMemo(() => {
    const cb = bundle.context ? tacticalContext(bundle.rasters, bundle.context) : null;
    return cb ? toCanvas(cb) : null;
  }, [bundle.context, bundle.rasters]);
  const agent = view.state?.agents.find((a) => a.agent_id === agentId) ?? view.state?.agents[0] ?? null;

  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    el.width = SIZE * dpr;
    el.height = SIZE * dpr;
    const g = el.getContext('2d')!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, SIZE, SIZE);
    const c = SIZE / 2;
    const centre: Point = agent?.pose.position ?? { x: meta.origin_x_m + (meta.cols * meta.resolution_m) / 2, y: meta.origin_y_m + (meta.rows * meta.resolution_m) / 2, z: 0 };
    const k = (SIZE / 2) / RADIUS_M; // px per metre
    const toPx = (p: Point) => [c + (p.x - centre.x) * k, c - (p.y - centre.y) * k] as const;

    // Heading-up: the map turns so the selected agent always points up (its heading, clockwise
    // from north, becomes straight ahead); the N mark moves round the rim to show north.
    const hdg = agent ? (headingFromNorth(yawFromQuaternion(agent.pose.orientation)) * Math.PI) / 180 : 0;
    g.save();
    g.beginPath();
    g.arc(c, c, c - 2, 0, Math.PI * 2);
    g.clip();
    g.fillStyle = '#030a14';
    g.fillRect(0, 0, SIZE, SIZE);
    g.translate(c, c);
    g.rotate(-hdg);
    g.translate(-c, -c);
    // Surroundings first (dimmer), or a hatch outside the map when the world has none.
    const W = meta.cols * meta.resolution_m;
    const H = meta.rows * meta.resolution_m;
    const [mx, my] = toPx({ x: meta.origin_x_m, y: meta.origin_y_m + H, z: 0 });
    const cf = bundle.context?.frame;
    if (ctxCanvas && cf) {
      const [cx0, cy0] = toPx({ x: cf.origin_x_m, y: cf.origin_y_m + cf.rows * cf.resolution_m, z: 0 });
      g.imageSmoothingEnabled = true;
      g.drawImage(ctxCanvas, cx0, cy0, cf.cols * cf.resolution_m * k, cf.rows * cf.resolution_m * k);
    } else {
      g.strokeStyle = 'rgba(120,170,230,0.16)';
      g.lineWidth = 1;
      for (let d = -SIZE * 2; d < SIZE * 2; d += 7) {
        g.beginPath();
        g.moveTo(d, -SIZE);
        g.lineTo(d + SIZE * 3, SIZE * 2);
        g.stroke();
      }
    }
    // Terrain: the full map image placed in metres around the agent.
    g.imageSmoothingEnabled = false;
    g.drawImage(baseCanvas, mx, my, W * k, H * k);
    // Edge of the mission map, so its limit reads as a limit and not as a missing piece.
    g.strokeStyle = 'rgba(190,225,255,0.55)';
    g.lineWidth = 1;
    g.setLineDash([3, 3]);
    g.strokeRect(mx, my, W * k, H * k);
    g.setLineDash([]);
    // Range rings every 150 m.
    g.strokeStyle = 'rgba(150,200,255,0.18)';
    for (let r = 150; r < RADIUS_M; r += 150) {
      g.beginPath();
      g.arc(c, c, r * k, 0, Math.PI * 2);
      g.stroke();
    }
    const path = (pts: Point[], color: string, dash: number[] = []) => {
      if (pts.length < 2) return;
      g.strokeStyle = color;
      g.lineWidth = 2;
      g.setLineDash(dash);
      g.beginPath();
      pts.forEach((p, i) => {
        const [x, y] = toPx(p);
        if (i) g.lineTo(x, y);
        else g.moveTo(x, y);
      });
      g.stroke();
      g.setLineDash([]);
    };
    if (view.activeRoute) {
      path(view.activeRoute.outbound_path, '#9FE3FF');
      path(view.activeRoute.return_path, 'rgba(159,227,255,0.55)', [4, 3]);
    }
    for (const p of bundle.manifest.pois.filter((q) => q.revealed_at_s <= view.t)) {
      const [x, y] = toPx(p.position);
      drawSiteIcon(g, p.kind, x, y, 16, siteKind(p.kind).color);
    }
    // Trails: where each agent has been in the last minutes (the rover's walk/drive shows behind it).
    drawTrails(g, bundle.timeline.frames, view.t, toPx);
    // Real rover stops in range: small amber dots, and the camera badge on the three nearest (display only).
    const stopsInRange = (bundle.roverStops?.stops ?? [])
      .map((st) => ({ st, p: toPx({ x: st.x_m, y: st.y_m, z: 0 }) }))
      .filter(({ p }) => Math.hypot(p[0] - c, p[1] - c) < c - 6);
    const nearest = new Set(stopsInRange.slice().sort((a, b) => Math.hypot(a.p[0] - c, a.p[1] - c) - Math.hypot(b.p[0] - c, b.p[1] - c)).slice(0, 3).map((s) => s.st.rmc));
    for (const { st, p } of stopsInRange) {
      if (nearest.has(st.rmc)) continue;
      g.fillStyle = 'rgba(240,160,80,0.9)';
      g.beginPath();
      g.arc(p[0], p[1], 2.2, 0, Math.PI * 2);
      g.fill();
    }
    for (const { st, p } of stopsInRange) if (nearest.has(st.rmc)) drawSiteIcon(g, 'photo', p[0], p[1], 13, siteKind('photo').color);
    for (const a of view.state?.agents ?? []) {
      if (a.agent_id === agent?.agent_id) continue;
      const [x, y] = toPx(a.pose.position);
      g.fillStyle = KIND_COLOR[a.agent_kind];
      g.beginPath();
      g.arc(x, y, 3, 0, Math.PI * 2);
      g.fill();
    }
    g.restore();

    // Selected agent: arrow at the centre, always pointing up (the map turns around it).
    if (agent) {
      g.save();
      g.translate(c, c);
      g.fillStyle = KIND_COLOR[agent.agent_kind];
      g.shadowColor = KIND_COLOR[agent.agent_kind];
      g.shadowBlur = 8;
      g.beginPath();
      g.moveTo(0, -8);
      g.lineTo(5.5, 6);
      g.lineTo(0, 3);
      g.lineTo(-5.5, 6);
      g.closePath();
      g.fill();
      g.restore();
    }
    // Rim and north mark.
    g.strokeStyle = 'rgba(120,190,255,0.85)';
    g.lineWidth = 1.5;
    g.beginPath();
    g.arc(c, c, c - 2, 0, Math.PI * 2);
    g.stroke();
    // North mark on the rim, at north's bearing on the turned map.
    const nx = c + Math.sin(-hdg) * (c - 10);
    const ny = c - Math.cos(-hdg) * (c - 10);
    g.fillStyle = 'rgba(3,10,20,0.75)';
    g.beginPath();
    g.arc(nx, ny, 7, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = '#cfe9ff';
    g.font = '600 11px "Barlow Condensed", sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillText('N', nx, ny + 0.5);
    g.textBaseline = 'alphabetic';
  }, [baseCanvas, ctxCanvas, bundle.context, view, agent, bundle.manifest.pois, bundle.roverStops, bundle.timeline.frames, meta, SIZE]);

  return (
    <div className="minimap" role="img" aria-label="Minimap, heading up (turns with the selected agent), centred on it; N marks north">
      <canvas ref={canvas} style={{ width: SIZE, height: SIZE }} />
    </div>
  );
}
