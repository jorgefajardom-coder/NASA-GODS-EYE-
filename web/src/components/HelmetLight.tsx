import { useFrame, useThree } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';

/**
 * Helmet lights of the astronaut: EVA suits carry LED lamps on the helmet (for example the lights on
 * the sides of the EMU / xEMU helmet) for working in shadow and at night. Drawn as one cool-white
 * spot light at helmet height, aimed ahead along the heading and down to the ground in front, plus
 * a small glowing lamp. Brightness, beam and colour are display choices, not suit specifications.
 * The light is always in the scene (intensity 0 when off) so switching does not recompile shaders.
 */
export const HELMET_LIGHT = { upM: 1.68, forwardM: 0.22, aimAheadM: 9, aimDownM: 1.9, candela: 420, angleRad: 0.5, penumbra: 0.55, rangeM: 70 };

export function HelmetLight({ agentName, on }: { agentName: string | null; on: boolean }) {
  const scene = useThree((s) => s.scene);
  const light = useRef<THREE.SpotLight>(null);
  const lamp = useRef<THREE.Mesh>(null);
  const target = useMemo(() => new THREE.Object3D(), []);
  const world = useMemo(() => new THREE.Vector3(), []);
  const level = useRef(0);

  useFrame((_, dt) => {
    const L = light.current;
    if (!L) return;
    const agent = agentName ? scene.getObjectByName(agentName) : null;
    // Ease on and off (a quarter second), like a lamp warming up.
    level.current += ((on && agent ? 1 : 0) - level.current) * Math.min(1, dt * 10);
    L.intensity = HELMET_LIGHT.candela * level.current;
    if (lamp.current) lamp.current.visible = level.current > 0.05;
    if (!agent) return;
    agent.getWorldPosition(world);
    const h = agent.rotation.y; // model faces +x, yaw about +y
    const fx = Math.cos(h);
    const fz = -Math.sin(h);
    L.position.set(world.x + fx * HELMET_LIGHT.forwardM, world.y + HELMET_LIGHT.upM, world.z + fz * HELMET_LIGHT.forwardM);
    target.position.set(world.x + fx * HELMET_LIGHT.aimAheadM, world.y + HELMET_LIGHT.upM - HELMET_LIGHT.aimDownM, world.z + fz * HELMET_LIGHT.aimAheadM);
    target.updateMatrixWorld();
    lamp.current?.position.copy(L.position);
  });

  return (
    <>
      <primitive object={target} />
      <spotLight
        ref={light}
        target={target}
        intensity={0}
        color="#eef3ff"
        angle={HELMET_LIGHT.angleRad}
        penumbra={HELMET_LIGHT.penumbra}
        distance={HELMET_LIGHT.rangeM}
        decay={2}
      />
      <mesh ref={lamp} visible={false}>
        <sphereGeometry args={[0.035, 10, 8]} />
        <meshBasicMaterial color="#f4f8ff" toneMapped={false} />
      </mesh>
    </>
  );
}
