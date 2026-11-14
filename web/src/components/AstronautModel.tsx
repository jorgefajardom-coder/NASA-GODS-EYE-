import { useAnimations, useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { Component, useEffect, useMemo, useRef, type ReactNode } from 'react';
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { AgentMode } from '../types/icd';
import { assetUrl } from '../data/replayAdapter';

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
export const ASTRONAUT_VISUAL_HEIGHT_M = 4;

const WALKING: ReadonlySet<AgentMode> = new Set(['MOVING', 'RETURNING']);
const FADE_S = 0.35;
/** Screen speed at which moon_walk plays at its authored rate for the enlarged model (visual tuning). */
const CLIP_SPEED_MPS = 2.2;
const MAX_TIME_SCALE = 3;

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
  const model = useMemo(() => cloneSkinned(gltf.scene), [gltf.scene]);
  const { actions, mixer } = useAnimations(gltf.animations, root);

  // Normalise size and put the feet on the agent position, measured from the file itself.
  const fit = useMemo(() => {
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);
    const height = box.max.y - box.min.y || 1;
    const scale = ASTRONAUT_VISUAL_HEIGHT_M / height;
    const centre = box.getCenter(new THREE.Vector3());
    return { scale, offset: [-centre.x * scale, -box.min.y * scale, -centre.z * scale] as [number, number, number] };
  }, [model]);

  useEffect(() => {
    model.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) {
        o.castShadow = true;
        o.frustumCulled = false; // skinned bounds are bind-pose only
      }
    });
  }, [model]);

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
    const walk = actions['moon_walk'];
    if (walk) walk.timeScale = playing ? Math.min(MAX_TIME_SCALE, Math.max(0.5, screenSpeedMps / CLIP_SPEED_MPS)) : 0;
  });

  useEffect(() => () => void mixer.stopAllAction(), [mixer]);

  return (
    // The parent group faces +x (east) at yaw 0; the model faces +z, so turn it 90°.
    <group ref={root} rotation={[0, Math.PI / 2, 0]}>
      <primitive object={model} scale={fit.scale} position={fit.offset} />
    </group>
  );
}

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
