import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import { droneSurvey } from '../lib/droneSurvey';
import { yawFromQuaternion } from '../lib/coords';

/**
 * MAP tab of the drone window: the terrain map the drone has built so far, north up and centred on
 * the drone. Cells the replay marks as observed by the drone are drawn as a dense point cloud
 * coloured by height; the rest is the orbital prior estimate, drawn as faint dots. Canvas 2D (no
 * second 3D render). In the demo the observations are simulated, so the window says so.
 */
const RADIUS_M = 300;
const RING_M = 100;

/** Deterministic jitter (0..1) per cell and sample, so the cloud does not flicker between redraws. */
const jitter = (i: number, k: number) => {
  const s = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453;
  return s - Math.floor(s);
};

/** Low -> high: deep teal, Signal Blue, near white. */
function ramp(t: number): string {
  const a = [27, 95, 122];
  const b = [101, 203, 232];
  const c = [232, 244, 255];
  const [p, q, u] = t < 0.5 ? [a, b, t * 2] : [b, c, (t - 0.5) * 2];
  return `rgb(${Math.round(p[0] + (q[0] - p[0]) * u)},${Math.round(p[1] + (q[1] - p[1]) * u)},${Math.round(p[2] + (q[2] - p[2]) * u)})`;
}

export function DroneMap({ bundle, view, droneId }: { bundle: ReplayBundle; view: ReplayView; droneId: string }) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 320, h: 180 });
  const meta = bundle.manifest.terrain_meta;
  const mapVersion = view.state?.map_version ?? 1;
  const drone = view.state?.agents.find((a) => a.agent_id === droneId) ?? null;
  const cx = drone?.pose.position.x ?? 0;
  const cy = drone?.pose.position.y ?? 0;
  // Recompute the survey when the drone moves a few metres or the map version changes.
  const qx = Math.round(cx / 5);
  const qy = Math.round(cy / 5);
  const survey = useMemo(() => droneSurvey(bundle.rasters, meta, mapVersion, qx * 5, qy * 5, RADIUS_M * 1.1), [bundle.rasters, meta, mapVersion, qx, qy]);
  // Flight trail up to the replay time (every few frames).
  const trail = useMemo(() => {
    const pts: Array<{ x: number; y: number }> = [];
    const frames = bundle.timeline.frames;
    for (let i = 0; i < frames.length; i += 3) {
      const f = frames[i];
      if (f.timestamp_sim_s > view.t) break;
      const a = f.mission_state.agents.find((g) => g.agent_id === droneId);
      if (a) pts.push({ x: a.pose.position.x, y: a.pose.position.y });
    }
    return pts;
  }, [bundle.timeline.frames, view.t, droneId]);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setSize({ w: Math.max(1, e.contentRect.width), h: Math.max(1, e.contentRect.height) }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    el.width = Math.round(size.w * dpr);
    el.height = Math.round(size.h * dpr);
    const g = el.getContext('2d');
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = '#03080c';
    g.fillRect(0, 0, size.w, size.h);
    const ox = size.w / 2;
    const oy = size.h / 2 + 4;
    const k = (Math.min(size.w, size.h) / 2 - 6) / RADIUS_M;
    const px = (x: number) => ox + (x - cx) * k;
    const py = (y: number) => oy - (y - cy) * k;
    const cellPx = meta.resolution_m * k;
    // Prior estimate: one faint dot per cell. Observed: a jittered cloud per cell, coloured by height.
    survey.points.forEach((p, idx) => {
      const x = px(p.x);
      const y = py(p.y);
      if (x < -cellPx || y < -cellPx || x > size.w + cellPx || y > size.h + cellPx) return;
      if (!p.observed) {
        g.fillStyle = `rgba(150, 160, 170, ${0.22 + 0.25 * p.t})`;
        g.fillRect(x - 0.8, y - 0.8, 1.6, 1.6);
        return;
      }
      g.fillStyle = ramp(p.t);
      for (let s = 0; s < 6; s++) {
        const jx = (jitter(idx, s) - 0.5) * cellPx;
        const jy = (jitter(idx, s + 7) - 0.5) * cellPx;
        g.fillRect(x + jx - 0.7, y + jy - 0.7, 1.4, 1.4);
      }
    });
    // Range rings and north.
    g.strokeStyle = 'rgba(101, 203, 232, 0.16)';
    g.lineWidth = 1;
    for (let r = RING_M; r <= RADIUS_M; r += RING_M) {
      g.beginPath();
      g.arc(ox, oy, r * k, 0, Math.PI * 2);
      g.stroke();
    }
    // Flight trail.
    if (trail.length > 1) {
      g.strokeStyle = 'rgba(101, 203, 232, 0.55)';
      g.setLineDash([3, 3]);
      g.beginPath();
      trail.forEach((p, i) => (i ? g.lineTo(px(p.x), py(p.y)) : g.moveTo(px(p.x), py(p.y))));
      g.stroke();
      g.setLineDash([]);
    }
    // Drone marker, pointing along its recorded heading (ENU yaw from east).
    if (drone) {
      const yaw = yawFromQuaternion(drone.pose.orientation);
      g.save();
      g.translate(ox, oy);
      g.rotate(-yaw + Math.PI / 2);
      g.fillStyle = '#e8f4ff';
      g.beginPath();
      g.moveTo(0, -6);
      g.lineTo(4, 4);
      g.lineTo(0, 2);
      g.lineTo(-4, 4);
      g.closePath();
      g.fill();
      g.restore();
    }
    g.fillStyle = 'rgba(207, 233, 255, 0.8)';
    g.font = '600 9px "IBM Plex Mono", monospace';
    g.textAlign = 'center';
    g.fillText('N', ox, oy - RADIUS_M * k + 9);
  }, [size, survey, trail, drone, cx, cy, meta.resolution_m]);

  const pct = survey.totalCount ? (survey.observedCount / survey.totalCount) * 100 : 0;
  return (
    <div className="dronemap" ref={wrap}>
      <canvas ref={canvas} style={{ width: size.w, height: size.h }} aria-label={`Drone survey map, map version ${mapVersion}: ${survey.observedCount} cells observed`} />
      <span className="dronemap__sweep" aria-hidden />
      <span className="dronemap__info">
        Map v{mapVersion} · {survey.observedCount} cells observed ({pct.toFixed(1)}%)
      </span>
      <span className="dronemap__legend">
        <i className="dronemap__key dronemap__key--obs" /> observed <i className="dronemap__key" /> orbital estimate · {RING_M} m rings
      </span>
    </div>
  );
}
