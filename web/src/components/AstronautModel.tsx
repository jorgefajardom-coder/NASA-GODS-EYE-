import { useAnimations, useGLTF } from '@react-three/drei';
import { useFrame, useThree } from '@react-three/fiber';
import { Component, useEffect, useMemo, useRef, type ReactNode } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { AgentMode } from '../types/icd';
import { assetUrl } from '../data/replayAdapter';
import { calmClip } from '../lib/astronautPose';
import { FootDust } from './FootDust';

/**
 * Astronaut GLB ("Animated Astronaut Character in Space Suit Loop" by LasquetiSpice,
 * CC BY 4.0, see THIRD_PARTY_NOTICES.md). Clips found in the file: wave, floating,
 * idle, moon_walk. Only idle and moon_walk are used; floating is not Mars locomotion.
 *
 * The model is purely visual: position and heading come from AgentState through the
 * parent group. moon_walk is an in-place clip (no root motion), so it cannot move
 * the agent. The animation is not a biomechanical validation.
 */
export const ASTRONAUT_URL = assetUrl('assets/models/astronaut.glb');

/** Drawn taller than a real person so it stays readable on a regional map (visual only). */
export const ASTRONAUT_VISUAL_HEIGHT_M = 1.9; // real EVA-suit height, next to real-size rover and base

const WALKING: ReadonlySet<AgentMode> = new Set(['MOVING', 'RETURNING']);
const FADE_S = 0.35;
/** Screen speed at which moon_walk plays at its authored rate for the enlarged model (visual tuning). */
const CLIP_SPEED_MPS = 1.05; // authored walk rate for a real-size (1.9 m) astronaut
/**
 * The walk cycle stays near its natural pace. Replay speed makes the astronaut cross the map
 * faster, but playing the cycle faster too looks like shaking, so foot sliding is accepted.
 */
const MIN_TIME_SCALE = 0.8;
const MAX_TIME_SCALE = 1.3;
const TEXTURE_SLOTS = ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap', 'specularColorMap', 'specularIntensityMap'] as const;

interface Props {
  mode: AgentMode;
  /** False while the replay is paused: the walk cycle freezes with the agent. */
  playing: boolean;
  /** Ground speed on screen, m/s of wall time (simulated speed × replay speed). */
  screenSpeedMps: number;
}

export function AstronautModel({ mode, playing, screenSpeedMps }: Props) {
  // Draco/Meshopt decoders disabled: the file uses neither and nothing may load from a CDN.
  const gltf = useGLTF(ASTRONAUT_URL, false, false);
  const root = useRef<THREE.Group>(null);
  const gl = useThree((s) => s.gl);
  const model = useMemo(() => cloneSkinned(gltf.scene), [gltf.scene]);

  // Normalise size and put the feet on the agent position, measured from the file itself.
  const fit = useMemo(() => {
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);
    const height = box.max.y - box.min.y || 1;
    const scale = ASTRONAUT_VISUAL_HEIGHT_M / height;
    const centre = box.getCenter(new THREE.Vector3());
    return { scale, offset: [-centre.x * scale, -box.min.y * scale, -centre.z * scale] as [number, number, number] };
  }, [model]);

  // Calmer copies of idle and moon_walk (see lib/astronautPose.ts); the other clips are not used.
  const clips = useMemo(
    () => gltf.animations.map((c) => (c.name === 'idle' || c.name === 'moon_walk' ? calmClip(model, c) : c)),
    [model, gltf.animations],
  );
  const { actions, mixer } = useAnimations(clips, root);

  // Local image-based light (no network) so the metallic parts are not rendered dark and muddy.
  const envMap = useMemo(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const tex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    return tex;
  }, [gl]);

  useEffect(() => {
    const aniso = gl.capabilities.getMaxAnisotropy();
    model.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      mesh.frustumCulled = false; // skinned bounds are bind-pose only
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of mats as THREE.MeshStandardMaterial[]) {
        m.envMap = envMap;
        m.envMapIntensity = 1.05; // brighter suit reflections, still physically based
        // Sharper textures at grazing angles (default anisotropy of 1 blurs them).
        for (const slot of TEXTURE_SLOTS) {
          const tex = (m as unknown as Record<string, THREE.Texture | null | undefined>)[slot];
          if (tex && tex.anisotropy !== aniso) {
            tex.anisotropy = aniso;
            tex.needsUpdate = true;
          }
        }
        m.needsUpdate = true;
      }
    });
    return () => envMap.dispose();
  }, [model, gl, envMap]);

  const walking = WALKING.has(mode);
  useEffect(() => {
    const next = actions[walking ? 'moon_walk' : 'idle'];
    const prev = actions[walking ? 'idle' : 'moon_walk'];
    if (!next) return;
    next.reset().setLoop(THREE.LoopRepeat, Infinity).fadeIn(FADE_S).play();
    prev?.fadeOut(FADE_S);
    return () => {
      next.fadeOut(FADE_S);
    };
  }, [actions, walking]);

  useFrame(() => {
    // Pause each clip, not the mixer: a frozen mixer also freezes the cross-fade, and a clip
    // still fading in at weight 0 leaves the model in its rest (T) pose while paused.
    mixer.timeScale = 1;
    const idle = actions['idle'];
    const walk = actions['moon_walk'];
    if (idle) idle.timeScale = playing ? 1 : 0;
    if (walk) walk.timeScale = playing ? Math.min(MAX_TIME_SCALE, Math.max(MIN_TIME_SCALE, screenSpeedMps / CLIP_SPEED_MPS)) : 0;
  });

  useEffect(() => () => void mixer.stopAllAction(), [mixer]);

  return (
    // The parent group faces +x (east) at yaw 0; the model faces +z, so turn it 90°.
    <group ref={root} rotation={[0, Math.PI / 2, 0]}>
      <primitive object={model} scale={fit.scale} position={fit.offset} />
      <FootDust model={model} active={walking && playing} screenSpeedMps={screenSpeedMps} />
      {/* Display lighting for the model only (distance-limited): warm key from the front-left,
          cool rim from behind to separate the suit from the ground, soft contact shadow. */}
      <pointLight position={[-2.2, 3.4, 2.6]} intensity={9} distance={9} decay={1.6} color="#ffe6cc" />
      <pointLight position={[1.6, 3.8, -2.8]} intensity={7} distance={9} decay={1.6} color="#a9d4ff" />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]} renderOrder={-1}>
        <circleGeometry args={[1.25, 32]} />
        <meshBasicMaterial map={contactShadow} transparent depthWrite={false} toneMapped={false} />
      </mesh>
    </group>
  );
}

/** Radial dark falloff used as a cheap contact shadow under the feet. */
const contactShadow = (() => {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(32, 32, 2, 32, 32, 32);
  grad.addColorStop(0, 'rgba(0,0,0,0.55)');
  grad.addColorStop(0.55, 'rgba(0,0,0,0.25)');
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
})();

/** Falls back to the simple avatar if the model cannot be loaded (plan B of the guide). */
export class ModelBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: unknown) {
    console.warn('Astronaut model unavailable, using simple avatar.', error);
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
