import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { assetUrl } from '../data/replayAdapter';

/**
 * Rover and drone models: official NASA/JPL-Caltech 3D models with all agency branding removed
 * (see web/scripts/blender/README.md and THIRD_PARTY_NOTICES.md). Drawn at real size; the
 * parent group gives position and heading from AgentState. Purely visual.
 */
export const ROVER_URL = assetUrl('assets/models/rover.glb');
export const DRONE_URL = assetUrl('assets/models/drone.glb');

interface Props {
  url: string;
  /** Real size of the vehicle's longest horizontal dimension (m). */
  lengthM: number;
  /** Extra turn so the model's front faces +x (east at yaw 0), radians. */
  yawOffset?: number;
  /** Spin rotor nodes (drone) while true. */
  spinning?: boolean;
}

/** Rotor nodes of the drone model and their spin direction (coaxial, counter-rotating). */
const ROTORS: Array<[RegExp, number]> = [
  [/^rotors_01/, 1],
  [/^rotors_02/, -1],
];
/** Real rotor speed is about 2,500 rpm; drawn slower so it reads as motion rather than flicker. */
const ROTOR_RAD_S = 28;

export function VehicleModel({ url, lengthM, yawOffset = 0, spinning = false }: Props) {
  const gltf = useGLTF(url, false, false);
  const model = useMemo(() => cloneSkinned(gltf.scene), [gltf.scene]);
  const fit = useMemo(() => {
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const scale = lengthM / (Math.max(size.x, size.z) || 1);
    const c = box.getCenter(new THREE.Vector3());
    return { scale, offset: [-c.x * scale, -box.min.y * scale, -c.z * scale] as [number, number, number] };
  }, [model, lengthM]);

  useEffect(() => {
    model.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) {
        m.castShadow = true;
        m.receiveShadow = true;
      }
    });
  }, [model]);

  const rotors = useMemo(() => {
    const out: Array<{ node: THREE.Object3D; dir: number }> = [];
    model.traverse((o) => {
      for (const [re, dir] of ROTORS) if (re.test(o.name)) out.push({ node: o, dir });
    });
    return out;
  }, [model]);
  const spin = useRef(spinning);
  spin.current = spinning;
  useFrame((_, dt) => {
    if (!spin.current) return;
    for (const r of rotors) r.node.rotation.y += r.dir * ROTOR_RAD_S * Math.min(dt, 0.05);
  });

  return (
    <group rotation={[0, yawOffset, 0]}>
      <primitive object={model} scale={fit.scale} position={fit.offset} />
    </group>
  );
}

useGLTF.preload(ROVER_URL, false, false);
useGLTF.preload(DRONE_URL, false, false);
