import { useEffect, useMemo, useRef } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { Point } from '../types/icd';
import { tacticalBase } from '../lib/tacticalMap';
import { yawFromQuaternion } from '../lib/coords';
import { headingFromNorth } from '../lib/management';

const DEFAULT_SIZE = 168;
/** Ground radius shown around the agent (m). */
const RADIUS_M = 450;
const KIND_COLOR = { HUMAN: '#E8F4FF', DRONE: '#65CBE8', ROVER: '#D8AD66' } as const;

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
  const baseCanvas = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = base.width;
    c.height = base.height;
    c.getContext('2d')!.putImageData(new ImageData(base.pixels, base.width, base.height), 0, 0);
    return c;
  }, [base]);
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
    // Terrain: the full map image placed in metres around the agent.
    const W = meta.cols * meta.resolution_m;
    const H = meta.rows * meta.resolution_m;
    const [mx, my] = toPx({ x: meta.origin_x_m, y: meta.origin_y_m + H, z: 0 });
    g.imageSmoothingEnabled = false;
    g.drawImage(baseCanvas, mx, my, W * k, H * k);
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
      g.fillStyle = '#E8F4FF';
      g.fillRect(x - 2.5, y - 2.5, 5, 5);
    }
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
  }, [baseCanvas, view, agent, bundle.manifest.pois, meta, SIZE]);

  return (
    <div className="minimap" role="img" aria-label="Minimap, heading up (turns with the selected agent), centred on it; N marks north">
      <canvas ref={canvas} style={{ width: SIZE, height: SIZE }} />
    </div>
  );
}
