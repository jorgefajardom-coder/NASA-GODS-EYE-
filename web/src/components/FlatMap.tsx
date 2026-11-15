import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { Point } from '../types/icd';
import { tacticalBase } from '../lib/tacticalMap';
import type { RenderTier } from '../lib/gpu';
import { drawSiteIcon, siteKind } from '../lib/siteKinds';

const KIND_COLOR = { HUMAN: '#E8F4FF', DRONE: '#65CBE8', ROVER: '#D8AD66' } as const;

/**
 * 2D top-down map that replaces the 3D view when the browser has no usable WebGL (no GPU, WebGL
 * disabled, or the 3D view failed to start). North up, fitted to the screen: the same tactical
 * terrain image as the minimap, the route in force and earlier routes, sites and agents at the
 * replay time. Canvas 2D only, so it runs on any browser. Display only; no data is changed.
 */
export function FlatMap({ bundle, view, selectedAgentId, reason }: { bundle: ReplayBundle; view: ReplayView; selectedAgentId: string | null; reason: RenderTier | 'failed' }) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
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
    g.fillStyle = '#0b0705';
    g.fillRect(0, 0, size.w, size.h);
    const W = meta.cols * meta.resolution_m;
    const H = meta.rows * meta.resolution_m;
    const k = Math.min(size.w / W, size.h / H) * 0.86; // px per metre, with a margin for the panels
    const ox = (size.w - W * k) / 2;
    const oy = (size.h - H * k) / 2;
    const toPx = (p: Point) => [ox + (p.x - meta.origin_x_m) * k, oy + (meta.origin_y_m + H - p.y) * k] as const;

    g.imageSmoothingEnabled = false;
    g.drawImage(baseCanvas, ox, oy, W * k, H * k);
    g.strokeStyle = 'rgba(150,200,255,0.35)';
    g.lineWidth = 1;
    g.strokeRect(ox, oy, W * k, H * k);

    const path = (pts: Point[], color: string, width: number, dash: number[] = []) => {
      if (pts.length < 2) return;
      g.strokeStyle = color;
      g.lineWidth = width;
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
    for (const r of view.previousRoutes) path(r.outbound_path, 'rgba(200,200,200,0.35)', 1.5, [3, 4]);
    if (view.activeRoute) {
      path(view.activeRoute.outbound_path, '#9FE3FF', 2.5);
      path(view.activeRoute.return_path, 'rgba(159,227,255,0.6)', 2, [6, 4]);
    }

    for (const st of bundle.roverStops?.stops ?? []) {
      const [x, y] = toPx({ x: st.x_m, y: st.y_m, z: 0 });
      drawSiteIcon(g, 'photo', x, y, 10, siteKind('photo').color);
    }
    g.font = '600 12px "Barlow Condensed", sans-serif';
    g.textBaseline = 'middle';
    for (const p of bundle.manifest.pois.filter((q) => q.revealed_at_s <= view.t)) {
      const [x, y] = toPx(p.position);
      drawSiteIcon(g, p.kind, x, y, 16, siteKind(p.kind).color);
      g.fillStyle = 'rgba(232,244,255,0.85)';
      g.fillText(p.label, x + 11, y);
    }
    for (const a of view.state?.agents ?? []) {
      const [x, y] = toPx(a.pose.position);
      const sel = a.agent_id === selectedAgentId;
      g.fillStyle = KIND_COLOR[a.agent_kind];
      g.beginPath();
      g.arc(x, y, sel ? 7 : 5, 0, Math.PI * 2);
      g.fill();
      if (sel) {
        g.strokeStyle = '#ffffff';
        g.lineWidth = 2;
        g.stroke();
      }
      g.fillStyle = '#ffffff';
      g.fillText(a.agent_id, x + 9, y - 9);
    }
    // North arrow and scale bar.
    g.fillStyle = '#cfe9ff';
    g.textAlign = 'center';
    g.fillText('N ▲', ox + W * k - 18, oy + 16);
    g.textAlign = 'left';
    const barM = 500;
    g.fillRect(ox + 12, oy + H * k - 18, barM * k, 3);
    g.fillText(`${barM} m`, ox + 12, oy + H * k - 30);
  }, [baseCanvas, view, bundle.manifest.pois, bundle.roverStops, meta, size, selectedAgentId]);

  const why = reason === 'failed' ? 'the 3D view could not start' : 'WebGL is not available in this browser';
  return (
    <div className="scene flatmap" ref={wrap} role="img" aria-label="2D top-down map of the mission area, north up">
      <canvas ref={canvas} style={{ width: size.w, height: size.h }} />
      <p className="flatmap__note">
        2D map mode · {why}. Same replay and data; <a href="?render=full">try 3D</a>
      </p>
    </div>
  );
}
