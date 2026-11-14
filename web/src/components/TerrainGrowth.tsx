import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

/** Duration of the growth (s). */
export const GROWTH_S = 2.4;
/** Sides of the clipping polygon: enough that the front reads as a circle. */
export const GROWTH_SIDES = 24;

/** Share of the time spent opening the main terrain block when the wider surroundings follow it. */
export const GROWTH_BLOCK_SHARE = 0.7;

const easeInOutSine = (x: number) => -(Math.cos(Math.PI * x) - 1) / 2;

/**
 * Radius of the growth front at progress p (0..1); negative before the start, so nothing is drawn.
 * The front opens the main block (radius `blockR`) with a smooth ease; when the 20 km surroundings
 * are drawn (`maxR` > `blockR`) it then keeps expanding geometrically to them, so their much larger
 * radius does not make the centre flash by.
 */
export function growthRadius(p: number, maxR: number, blockR = maxR): number {
  const q = Math.max(0, Math.min(1, p));
  if (q === 0) return -1;
  const share = maxR > blockR ? GROWTH_BLOCK_SHARE : 1;
  if (q <= share) return blockR * easeInOutSine(q / share);
  return blockR * Math.pow(maxR / blockR, (q - share) / (1 - share));
}

/**
 * Clipping planes that keep a regular polygon around (cx, cz) in the Three.js ground plane, hidden
 * until a radius is set. Each plane keeps the side facing the centre: n·p + constant >= 0.
 */
export function growthPlanes(cx: number, cz: number, sides = GROWTH_SIDES): THREE.Plane[] {
  const planes = Array.from({ length: sides }, (_, i) => {
    const a = (i / sides) * Math.PI * 2;
    return new THREE.Plane(new THREE.Vector3(-Math.cos(a), 0, -Math.sin(a)), 0);
  });
  setGrowthRadius(planes, cx, cz, -1);
  return planes;
}

/** Sets every plane so the kept polygon has apothem `r` around its centre. */
export function setGrowthRadius(planes: THREE.Plane[], cx: number, cz: number, r: number): void {
  for (const p of planes) {
    // Kept side: r - dir·(x - c) >= 0, with n = -dir  =>  constant = r + dir·c.
    p.constant = r - (p.normal.x * cx + p.normal.z * cz);
  }
}

interface Props {
  /** Start growing (after the intro). Until then nothing is drawn. */
  start: boolean;
  /** Centre of the terrain in Three.js ground coordinates (x east, z = -north). */
  centerX: number;
  centerZ: number;
  /** Distance from the centre to the farthest drawn ground (m), and to the main block's corners. */
  maxRadius: number;
  blockRadius: number;
  onDone?: () => void;
}

/**
 * Opening animation of the 3D view: the terrain appears from the centre of the map outwards, as a
 * circular front (a polygon of clipping planes) that expands to the farthest corner. Agents and the
 * base appear as the front reaches them. Display only; removed once finished.
 */
export function TerrainGrowth({ start, centerX, centerZ, maxRadius, blockRadius, onDone }: Props) {
  const gl = useThree((s) => s.gl);
  const planes = useMemo(() => growthPlanes(centerX, centerZ), [centerX, centerZ]);
  const t = useRef(0);
  const finished = useRef(false);
  const done = useRef(onDone);
  done.current = onDone;

  useEffect(() => {
    setGrowthRadius(planes, centerX, centerZ, -1);
    gl.clippingPlanes = planes;
    return () => {
      gl.clippingPlanes = [];
    };
  }, [gl, planes, centerX, centerZ]);

  useFrame((_, dt) => {
    if (finished.current) return;
    if (!start) {
      setGrowthRadius(planes, centerX, centerZ, -1); // keep everything hidden until the growth starts
      return;
    }
    t.current += Math.min(dt, 0.25); // keeps its pace at low frame rates, without jumping after a stall
    const p = t.current / GROWTH_S;
    setGrowthRadius(planes, centerX, centerZ, growthRadius(p, maxRadius, blockRadius));
    if (p >= 1) {
      finished.current = true;
      gl.clippingPlanes = [];
      done.current?.();
    }
  });

  return null;
}
