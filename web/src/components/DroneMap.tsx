import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import { droneHazardReport, droneReportEvents, type HazardLevel } from '../lib/droneHazards';
import { yawFromQuaternion } from '../lib/coords';
import { fmtDuration } from '../lib/format';

/**
 * MAP tab of the drone window: the drone's hazard report. It draws only what the drone has
 * observed (the interface map stays in the agent dial): steep cells in red, moderate in amber,
 * cells that contradict the orbital estimate outlined in red, clear cells as faint cyan dots, with
 * the drone, its flight trail and the nearest hazard. A status line says what the report caused in
 * the replay (map update, route invalidated). The demo's observations are simulated; not LiDAR.
 */
const RADIUS_M = 300;
const RING_M = 100;
const LEVEL_COLOR: Record<HazardLevel, string> = { hazard: '#e0583f', caution: '#e3c25a', changed: '#e0583f', clear: 'rgba(101, 203, 232, 0.55)' };

export function DroneMap({ bundle, view, droneId }: { bundle: ReplayBundle; view: ReplayView; droneId: string }) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 320, h: 180 });
  const meta = bundle.manifest.terrain_meta;
  const mapVersion = view.state?.map_version ?? 1;
  const drone = view.state?.agents.find((a) => a.agent_id === droneId) ?? null;
  const cx = drone?.pose.position.x ?? 0;
  const cy = drone?.pose.position.y ?? 0;
  const qx = Math.round(cx / 5);
  const qy = Math.round(cy / 5);
  const report = useMemo(() => droneHazardReport(bundle.rasters, meta, mapVersion, qx * 5, qy * 5), [bundle.rasters, meta, mapVersion, qx, qy]);
  const caused = useMemo(() => droneReportEvents(bundle.timeline.events, droneId, view.t), [bundle.timeline.events, droneId, view.t]);
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
    const oy = size.h / 2 + 6;
    const k = (Math.min(size.w, size.h) / 2 - 8) / RADIUS_M;
    const px = (x: number) => ox + (x - cx) * k;
    const py = (y: number) => oy - (y - cy) * k;
    const cell = Math.max(2, meta.resolution_m * k);
    g.strokeStyle = 'rgba(101, 203, 232, 0.14)';
    g.lineWidth = 1;
    for (let r = RING_M; r <= RADIUS_M; r += RING_M) {
      g.beginPath();
      g.arc(ox, oy, r * k, 0, Math.PI * 2);
      g.stroke();
    }
    // Observed cells only: hazards filled, contradictions outlined, clear ground as faint dots.
    for (const c of report.cells) {
      const x = px(c.x);
      const y = py(c.y);
      if (x < -cell || y < -cell || x > size.w + cell || y > size.h + cell) continue;
      if (c.level === 'clear') {
        g.fillStyle = LEVEL_COLOR.clear;
        g.fillRect(x - 0.8, y - 0.8, 1.6, 1.6);
        continue;
      }
      if (c.level !== 'changed') {
        g.fillStyle = LEVEL_COLOR[c.level];
        g.globalAlpha = 0.85;
        g.fillRect(x - cell / 2, y - cell / 2, cell, cell);
        g.globalAlpha = 1;
      }
      if (c.changed) {
        g.strokeStyle = '#ff8a70';
        g.lineWidth = 1;
        g.strokeRect(x - cell / 2 + 0.5, y - cell / 2 + 0.5, cell - 1, cell - 1);
      }
    }
    if (trail.length > 1) {
      g.strokeStyle = 'rgba(101, 203, 232, 0.55)';
      g.setLineDash([3, 3]);
      g.beginPath();
      trail.forEach((p, i) => (i ? g.lineTo(px(p.x), py(p.y)) : g.moveTo(px(p.x), py(p.y))));
      g.stroke();
      g.setLineDash([]);
    }
    // Line to the nearest hazard.
    if (report.nearest && report.nearest.distanceM <= RADIUS_M * 1.5) {
      const a = (report.nearest.bearingDeg * Math.PI) / 180;
      const d = Math.min(report.nearest.distanceM, RADIUS_M) * k;
      g.strokeStyle = 'rgba(224, 88, 63, 0.8)';
      g.beginPath();
      g.moveTo(ox, oy);
      g.lineTo(ox + Math.sin(a) * d, oy - Math.cos(a) * d);
      g.stroke();
    }
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
  }, [size, report, trail, drone, cx, cy, meta.resolution_m]);

  const n = report.nearest;
  const status = caused.mapUpdate
    ? `Reported ${fmtDuration(caused.mapUpdate.timestamp_sim_s)} · map v${caused.mapUpdate.map_version}${caused.invalidated ? ` · route ${caused.invalidated.route_id} invalidated` : ''}`
    : 'No hazard report yet · orbital estimate only';
  return (
    <div className="dronemap" ref={wrap}>
      <canvas ref={canvas} style={{ width: size.w, height: size.h }} aria-label={`Drone hazard report: ${report.counts.hazard} steep, ${report.counts.caution} moderate, ${report.cells.filter((c) => c.changed).length} contradicting the orbital estimate`} />
      <span className="dronemap__info">
        {report.observedCount ? (
          <>
            <b className="dronemap__hz">{report.counts.hazard} steep</b> · {report.counts.caution} moderate · {report.cells.filter((c) => c.changed).length} changed
            {n ? ` · nearest ${n.distanceM.toFixed(0)} m ${String(Math.round(n.bearingDeg)).padStart(3, '0')}°` : ''}
          </>
        ) : (
          'Hazard report · no drone observations yet'
        )}
      </span>
      <span className="dronemap__status">{status}</span>
      <span className="dronemap__legend">
        <i className="dronemap__key dronemap__key--hz" /> ≥15° <i className="dronemap__key dronemap__key--ca" /> 8–15° <i className="dronemap__key dronemap__key--ch" /> changed
      </span>
    </div>
  );
}
