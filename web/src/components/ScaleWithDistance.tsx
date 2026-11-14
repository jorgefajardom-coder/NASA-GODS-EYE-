import { useFrame } from '@react-three/fiber';
import { useRef, type ReactNode } from 'react';
import * as THREE from 'three';

interface Props {
  /** Scale added per metre of camera distance. */
  perMetre: number;
  min?: number;
  max?: number;
  children: ReactNode;
}

/**
 * Keeps map markers and agents readable at any zoom by enlarging them with camera
 * distance (never below 1:1). Purely visual: positions and orientations are untouched.
 */
export function ScaleWithDistance({ perMetre, min = 1, max = 12, children }: Props) {
  const group = useRef<THREE.Group>(null);
  const world = useRef(new THREE.Vector3());
  useFrame(({ camera }) => {
    const g = group.current;
    if (!g) return;
    g.getWorldPosition(world.current);
    g.scale.setScalar(THREE.MathUtils.clamp(camera.position.distanceTo(world.current) * perMetre, min, max));
  });
  return <group ref={group}>{children}</group>;
}
