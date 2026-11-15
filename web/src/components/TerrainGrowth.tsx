import { useFrame } from '@react-three/fiber';
import { useEffect, useLayoutEffect, useRef, type RefObject } from 'react';
import type * as THREE from 'three';

/** Duration of the growth (s). */
export const GROWTH_S = 5;
/** Relief share at the start: a nearly flat sheet, so the whole layer is visible from the first frame. */
export const GROWTH_FLAT = 0.02;

/** Smooth start and stop (zero speed and acceleration at both ends). */
const smootherstep = (x: number) => x * x * x * (x * (x * 6 - 15) + 10);

/**
 * Share of the true relief drawn at progress p (0..1): GROWTH_FLAT at the start, then one
 * continuous rise to 1 that starts and stops gently (no steps, no overshoot).
 */
export function reliefShare(p: number): number {
  const q = Math.max(0, Math.min(1, p));
  return GROWTH_FLAT + (1 - GROWTH_FLAT) * smootherstep(q);
}

/** Live progress of the opening growth (0..1), read by the terrain mesh each frame; 1 when idle. */
export const growthClock = { p: 1, active: false };

/** Share of the growth time over which one zone rises (the rest is the stagger between zones). */
export const ZONE_RISE_SHARE = 0.38;

/**
 * Start of a zone's rise (0..1 of the stagger): low ground first, ridges last, with a little
 * position-dependent variation so neighbouring zones of equal height do not rise as one block.
 * `normH` is the zone's height within the layer (0 = lowest, 1 = highest).
 */
export function zoneDelay(normH: number, x: number, z: number): number {
  const h = Math.max(0, Math.min(1, normH));
  const n = Math.sin(x * 0.011 + z * 0.007) * Math.cos(z * 0.013 - x * 0.005); // -1..1, smooth
  return Math.max(0, Math.min(1, 0.85 * h + 0.15 * (0.5 + 0.5 * n)));
}

/**
 * Relief share of one zone at overall progress p: it waits for its delay, then rises smoothly
 * over ZONE_RISE_SHARE of the time; every zone has finished at p = 1.
 */
export function zoneShare(p: number, delay: number): number {
  const q = Math.max(0, Math.min(1, p));
  const start = delay * (1 - ZONE_RISE_SHARE);
  const local = Math.max(0, Math.min(1, (q - start) / ZONE_RISE_SHARE));
  return GROWTH_FLAT + (1 - GROWTH_FLAT) * smootherstep(local);
}

/** How strongly a zone is rising right now (0 at rest, 1 mid-rise): used to light the rising ground. */
export function zoneGlow(p: number, delay: number): number {
  const q = Math.max(0, Math.min(1, p));
  const start = delay * (1 - ZONE_RISE_SHARE);
  const local = (q - start) / ZONE_RISE_SHARE;
  if (local <= 0 || local >= 1) return 0;
  return Math.sin(Math.PI * local);
}

/**
 * Vertical transform of the terrain group for a relief share k: heights are scaled by k about the
 * pivot (the lowest ground), so the layer starts flat at the pivot and rises to its true shape.
 */
export function reliefTransform(k: number, pivotY: number): { scaleY: number; offsetY: number } {
  return { scaleY: k, offsetY: pivotY * (1 - k) };
}

interface Props {
  /** Start growing (after the intro). Until then the terrain is hidden. */
  start: boolean;
  /** Group holding the terrain mesh, the block and the surroundings. */
  target: RefObject<THREE.Group | null>;
  /** Height the relief grows from (Three.js y, already exaggerated): the lowest ground. */
  pivotY: number;
  onDone?: () => void;
}

/**
 * Opening animation of the 3D view: the whole terrain layer appears at once as a flat sheet and its
 * relief rises to the true shape zone by zone (low ground first, ridges last, rising ground lit),
 * as if the ground were being generated. The terrain mesh reads growthClock; the block and the
 * surroundings in `target` rise uniformly. No height data changes. Agents, the base and labels appear once it has finished.
 */
export function TerrainGrowth({ start, target, pivotY, onDone }: Props) {
  const t = useRef(0);
  const finished = useRef(false);
  const done = useRef(onDone);
  done.current = onDone;

  // Flat from the very first frame, before this component's own frame runs.
  useLayoutEffect(() => {
    growthClock.p = 0;
    growthClock.active = true;
  }, []);

  // Leave the group at its true shape when unmounted (finished, or the scene changes).
  useEffect(
    () => () => {
      growthClock.p = 1;
      growthClock.active = false;
      const g = target.current;
      if (!g) return;
      g.visible = true;
      g.scale.y = 1;
      g.position.y = 0;
    },
    [target],
  );

  useFrame((_, dt) => {
    const g = target.current;
    if (finished.current || !g) return;
    if (!start) {
      g.visible = false; // hidden behind the intro
      growthClock.p = 0;
      growthClock.active = true;
      return;
    }
    g.visible = true;
    growthClock.active = true;
    t.current += Math.min(dt, 0.25); // keeps its pace at low frame rates, without jumping after a stall
    const p = t.current / GROWTH_S;
    const { scaleY, offsetY } = reliefTransform(reliefShare(p), pivotY);
    g.scale.y = scaleY;
    g.position.y = offsetY;
    growthClock.p = Math.min(1, p);
    if (p >= 1) {
      finished.current = true;
      growthClock.active = false;
      g.scale.y = 1;
      g.position.y = 0;
      done.current?.();
    }
  });

  return null;
}
