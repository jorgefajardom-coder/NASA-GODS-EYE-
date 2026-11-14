import { useEffect, useMemo, useRef } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { Point } from '../types/icd';
import { tacticalBase } from '../lib/tacticalMap';
import { finiteRange } from '../lib/layers';

const KIND_COLOR = { HUMAN: '#E8F4FF', DRONE: '#65CBE8', ROVER: '#D8AD66' } as const;

/**
 * 2D tactical map (Tactical map tab): elevation bands of the updated map, relief shading,
 * observed-cell coverage, the active and invalidated routes, sites and agents. Display only;
 * it uses the same data as the 3D view and never computes routes.
 */
export function TacticalMap({ bundle, view }: { bundle: ReplayBundle; view: ReplayView }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const meta = bundle.manifest.terrain_meta;
  const mapVersion = view.state?.map_version ?? 1;
  const base = useMemo(() => tacticalBase(bundle.rasters, mapVersion), [bundle.rasters, mapVersion]);
  const baseCanvas = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = base.width;
    c.height = base.height;
    c.getContext('2d')!.putImageData(new ImageData(base.pixels, base.width, base.height), 0, 0);
    return c;
  }, [base]);
  const [lo, hi] = finiteRange(bundle.rasters.prior);
  const offset = bundle.manifest.local_z_offset_m ?? 0;

  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const box = el.getBoundingClientRect();
    el.width = Math.round(box.width * dpr);
    el.height = Math.round(box.height * dpr);
    const g = el.getContext('2d')!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, box.width, box.height);

    // Fit the square map in the box, leaving room for the frame.
    const size = Math.min(box.width, box.height) * 0.86;
    const x0 = (box.width - size) / 2;
    const y0 = (box.height - size) / 2 + 12;
    const W = meta.cols * meta.resolution_m;
    const H = meta.rows * meta.resolution_m;
    const toPx = (p: Point) => [x0 + ((p.x - meta.origin_x_m) / W) * size, y0 + (1 - (p.y - meta.origin_y_m) / H) * size] as const;

    // Glow under the map, then the blocky base.
    g.save();
    g.shadowColor = 'rgba(80,160,255,0.55)';
    g.shadowBlur = 28;
    g.fillStyle = '#061630';
    g.fillRect(x0, y0, size, size);
    g.restore();
    g.imageSmoothingEnabled = false;
    g.drawImage(baseCanvas, x0, y0, size, size);

    // Fine grid every 100 m.
    g.strokeStyle = 'rgba(150,200,255,0.08)';
    g.lineWidth = 1;
    for (let m = 100; m < W; m += 100) {
      const x = x0 + (m / W) * size;
      g.beginPath();
      g.moveTo(x, y0);
      g.lineTo(x, y0 + size);
      g.stroke();
      const y = y0 + (m / H) * size;
      g.beginPath();
      g.moveTo(x0, y);
      g.lineTo(x0 + size, y);
      g.stroke();
    }
    g.strokeStyle = 'rgba(120,190,255,0.9)';
    g.lineWidth = 1.5;
    g.strokeRect(x0, y0, size, size);

    const path = (pts: Point[], color: string, dash: number[] = []) => {
      if (pts.length < 2) return;
      g.save();
      g.strokeStyle = color;
      g.lineWidth = 2;
      g.setLineDash(dash);
      g.shadowColor = color;
      g.shadowBlur = 8;
      g.beginPath();
      pts.forEach((p, i) => {
        const [x, y] = toPx(p);
        if (i) g.lineTo(x, y);
        else g.moveTo(x, y);
      });
      g.stroke();
      g.restore();
    };
    for (const r of view.previousRoutes) path(r.outbound_path, 'rgba(217,80,69,0.8)', [5, 5]);
    if (view.activeRoute) {
      path(view.activeRoute.outbound_path, '#9FE3FF');
      path(view.activeRoute.return_path, 'rgba(159,227,255,0.6)', [6, 4]);
    }

    g.font = '600 12px "Barlow Condensed", sans-serif';
    for (const p of bundle.manifest.pois.filter((q) => q.revealed_at_s <= view.t)) {
      const [x, y] = toPx(p.position);
      g.fillStyle = '#E8F4FF';
      g.beginPath();
      g.moveTo(x, y - 6);
      g.lineTo(x + 5, y);
      g.lineTo(x, y + 6);
      g.lineTo(x - 5, y);
      g.closePath();
      g.fill();
      g.fillText(p.label.toUpperCase(), x + 8, y + 4);
    }
    for (const a of view.state?.agents ?? []) {
      const [x, y] = toPx(a.pose.position);
      g.save();
      g.fillStyle = KIND_COLOR[a.agent_kind];
      g.shadowColor = KIND_COLOR[a.agent_kind];
      g.shadowBlur = 12;
      g.beginPath();
      g.arc(x, y, 4.5, 0, Math.PI * 2);
      g.fill();
      g.restore();
      g.fillStyle = KIND_COLOR[a.agent_kind];
      g.fillText(a.agent_kind, x + 8, y - 6);
    }

    // Scale bar: 500 m.
    const bar = (500 / W) * size;
    g.strokeStyle = '#9FE3FF';
    g.beginPath();
    g.moveTo(x0 + 12, y0 + size - 14);
    g.lineTo(x0 + 12 + bar, y0 + size - 14);
    g.stroke();
    g.fillStyle = '#9FE3FF';
    g.fillText('500 m', x0 + 12, y0 + size - 20);
  }, [baseCanvas, view, bundle.manifest.pois, meta]);

  const pct = base.total ? (100 * base.observed) / base.total : 0;
  return (
    <div className="tactical" aria-label="2D tactical map of the terrain">
      <header className="tactical__head">
        <h2>Terrain coverage</h2>
        <div className="tactical__stats mono">
          <span>map v{mapVersion}</span>
          <span>
            {base.observed}/{base.total} cells observed ({pct.toFixed(1)} %)
          </span>
        </div>
      </header>
      <canvas ref={canvas} className="tactical__canvas" />
      <footer className="tactical__legend">
        <span className="tactical__ramp" aria-hidden />
        <span className="mono">
          {(lo + offset).toFixed(0)} m … {(hi + offset).toFixed(0)} m (MOLA areoid), {meta.resolution_m} m cells
        </span>
        <span className="tactical__key tactical__key--seen">observed by agents</span>
        <span className="tactical__key tactical__key--route">route in force</span>
        <span className="tactical__key tactical__key--old">invalidated route</span>
      </footer>
    </div>
  );
}
