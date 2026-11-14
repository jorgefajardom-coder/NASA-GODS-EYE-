import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

/** Duration of the growth (s) and the number of layers it builds in. */
export const GROWTH_S = 3.2;
export const GROWTH_LAYERS = 14;
/** Share of each layer's time spent rising; the rest it holds, so the steps read as strata. */
const RISE_SHARE = 0.6;

const easeOutCubic = (x: number) => 1 - Math.pow(1 - x, 3);

/** Height of the growth front at progress p (0..1), in layers that rise and then hold. */
export function growthHeight(p: number, bottom: number, top: number, layers = GROWTH_LAYERS): number {
  const q = Math.max(0, Math.min(1, p)) * layers;
  const i = Math.min(layers - 1, Math.floor(q));
  const f = q >= layers ? 1 : q - i;
  const step = easeOutCubic(Math.min(1, f / RISE_SHARE));
  return bottom + ((top - bottom) * (i + step)) / layers;
}

interface Props {
  /** Start growing (after the intro). Until then nothing below `top` is drawn. */
  start: boolean;
  /** Lowest drawn point (base of the block) and a height above everything (Three.js y). */
  bottom: number;
  top: number;
  onDone?: () => void;
}

/**
 * Opening animation of the 3D view: a horizontal clipping plane rises from the base of the terrain
 * block to above the highest relief in GROWTH_LAYERS steps, so the ground seems to build up layer by
 * layer (walls first, then valleys, then ridges). Display only; removed once finished.
 */
export function TerrainGrowth({ start, bottom, top, onDone }: Props) {
  const gl = useThree((s) => s.gl);
  const plane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, -1, 0), bottom), [bottom]);
  const t = useRef(0);
  const finished = useRef(false);
  const done = useRef(onDone);
  done.current = onDone;

  useEffect(() => {
    gl.clippingPlanes = [plane];
    return () => {
      gl.clippingPlanes = [];
    };
  }, [gl, plane]);

  useFrame((_, dt) => {
    if (finished.current) return;
    if (!start) {
      plane.constant = bottom; // keep everything hidden until the growth starts
      return;
    }
    t.current += Math.min(dt, 0.05);
    const p = t.current / GROWTH_S;
    plane.constant = growthHeight(p, bottom, top);
    if (p >= 1) {
      finished.current = true;
      gl.clippingPlanes = [];
      done.current?.();
    }
  });

  return null;
}
