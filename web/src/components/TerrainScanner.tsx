import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { TerrainMeta } from '../types/icd';
import { INDICATOR_STYLE, SCAN_CONFIG, type IndicatorClass } from '../scanner/ScanConfig';
import { scanController } from '../scanner/ScanController';
import { layoutIndicators, spacingAt } from '../scanner/ScanIndicators';
import { INDICATOR_FRAG, INDICATOR_VERT, scanUniforms } from '../scanner/shaders';
import { scanAudio } from '../scanner/scanAudio';
import type { ScanState } from '../scanner/ScanStateMachine';

/**
 * Scene side of the first-person terrain scan (Odradek-style, adapted to Three.js): registers the
 * astronaut as the scan origin, writes the shared scan uniforms once per frame from the state
 * machine (the terrain, footprint and route shaders read them), and draws the surface indicators
 * with one InstancedMesh per symbol, rebuilt once per scan from the run's slope classes.
 * Display only: it reads existing data and changes no map, observation or route.
 */
const CLASSES: IndicatorClass[] = ['traversable', 'caution', 'hazard', 'unknown'];

/** Flat symbol geometries (in the ground plane, ~1 m across, scaled per instance). */
function glyph(kind: (typeof INDICATOR_STYLE)[IndicatorClass]['glyph']): THREE.BufferGeometry {
  let g: THREE.BufferGeometry;
  if (kind === 'dot') g = mergeGeometries([new THREE.RingGeometry(0.32, 0.4, 24), new THREE.CircleGeometry(0.1, 12)]);
  else if (kind === 'triangle') g = new THREE.RingGeometry(0.34, 0.44, 3, 1, Math.PI / 2);
  else if (kind === 'diamond') g = new THREE.RingGeometry(0.31, 0.4, 4, 1, 0);
  else {
    const a = new THREE.PlaneGeometry(0.8, 0.09);
    const b = new THREE.PlaneGeometry(0.8, 0.09);
    a.rotateZ(Math.PI / 4);
    b.rotateZ(-Math.PI / 4);
    g = mergeGeometries([a, b]);
  }
  g.rotateX(-Math.PI / 2); // lie in the ground plane, facing up (+y)
  return g;
}

interface Props {
  /** Scene name of the astronaut group, or null when there is none. */
  agentName: string | null;
  /** The scan can run (first person on the astronaut, terrain grown). */
  enabled: boolean;
  disabledReason: string;
  meta: TerrainMeta;
  slope: ReadonlyArray<number | null>;
  /** True ground height at a local ENU point (m), or null outside the grid / next to NoData. */
  groundHeight: (x: number, y: number) => number | null;
  verticalExaggeration: number;
}

export function TerrainScanner({ agentName, enabled, disabledReason, meta, slope, groundHeight, verticalExaggeration }: Props) {
  const scene = useThree((s) => s.scene);
  const world = useMemo(() => new THREE.Vector3(), []);

  // Origin provider and availability: the scan always starts at the astronaut's current position.
  useEffect(() => {
    scanController.setOriginProvider(() => {
      const obj = agentName ? scene.getObjectByName(agentName) : null;
      if (!obj) return null;
      obj.getWorldPosition(world);
      return { x: world.x, y: world.y, z: world.z };
    });
    return () => scanController.setOriginProvider(null);
  }, [agentName, scene, world]);
  useEffect(() => {
    scanController.setAvailable(enabled, disabledReason);
    return () => scanController.setAvailable(false, 'Scanner not loaded');
  }, [enabled, disabledReason]);

  // Indicator pool: one InstancedMesh per class, fixed capacity, reused for every scan.
  const meshes = useMemo(() => {
    return CLASSES.map((cls) => {
      const geo = glyph(INDICATOR_STYLE[cls].glyph);
      const mat = new THREE.ShaderMaterial({
        vertexShader: INDICATOR_VERT,
        fragmentShader: INDICATOR_FRAG,
        uniforms: { ...scanUniforms, uColor: { value: new THREE.Color(INDICATOR_STYLE[cls].color) } },
        transparent: true,
        depthWrite: false,
        depthTest: true, // occluded by the terrain
        side: THREE.DoubleSide,
        polygonOffset: true,
        polygonOffsetFactor: -2,
        polygonOffsetUnits: -2,
        toneMapped: false,
      });
      const mesh = new THREE.InstancedMesh(geo, mat, SCAN_CONFIG.maxIndicators);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      const dist = new THREE.InstancedBufferAttribute(new Float32Array(SCAN_CONFIG.maxIndicators), 1);
      dist.setUsage(THREE.DynamicDrawUsage);
      geo.setAttribute('aDist', dist);
      mesh.count = 0;
      mesh.frustumCulled = false;
      mesh.renderOrder = 6;
      mesh.name = `scan-indicators-${cls}`;
      return mesh;
    });
  }, []);
  useEffect(
    () => () => {
      for (const m of meshes) {
        m.geometry.dispose();
        (m.material as THREE.Material).dispose();
        m.dispose();
      }
    },
    [meshes],
  );

  // Rebuild the indicators once per scan (not per frame).
  const tmp = useMemo(() => ({ m: new THREE.Matrix4(), q: new THREE.Quaternion(), n: new THREE.Vector3(), up: new THREE.Vector3(0, 1, 0), p: new THREE.Vector3(), s: new THREE.Vector3() }), []);
  useEffect(() => {
    return scanController.onScan((snap) => {
      const o = snap.origin;
      if (!o) return;
      scanAudio.pulse();
      const ox = o.x;
      const oy = -o.z; // Three.js z = -north
      const pts = layoutIndicators(meta, slope, ox, oy, { rangeM: SCAN_CONFIG.rangeM, nearM: SCAN_CONFIG.spacingNearM, farM: SCAN_CONFIG.spacingFarM, max: SCAN_CONFIG.maxIndicators });
      const counts = [0, 0, 0, 0];
      const e = verticalExaggeration;
      const d = 0.75;
      for (const p of pts) {
        const ci = CLASSES.indexOf(p.cls);
        const mesh = meshes[ci];
        const i = counts[ci]++;
        const h = groundHeight(p.x, p.y);
        const hx0 = groundHeight(p.x - d, p.y);
        const hx1 = groundHeight(p.x + d, p.y);
        const hy0 = groundHeight(p.x, p.y - d);
        const hy1 = groundHeight(p.x, p.y + d);
        // Surface normal from the drawn (exaggerated) relief: y = f(x, z) with z = -north.
        const dhdx = hx0 != null && hx1 != null ? (hx1 - hx0) / (2 * d) : 0;
        const dhdy = hy0 != null && hy1 != null ? (hy1 - hy0) / (2 * d) : 0;
        tmp.n.set(-dhdx * e, 1, dhdy * e).normalize();
        tmp.q.setFromUnitVectors(tmp.up, tmp.n);
        const y = h == null ? o.y : h * e;
        tmp.p.set(p.x, y, -p.y).addScaledVector(tmp.n, SCAN_CONFIG.liftM);
        const size = 0.2 * spacingAt(p.distanceM, SCAN_CONFIG.rangeM, SCAN_CONFIG.spacingNearM, SCAN_CONFIG.spacingFarM);
        tmp.s.setScalar(size);
        tmp.m.compose(tmp.p, tmp.q, tmp.s);
        mesh.setMatrixAt(i, tmp.m);
        (mesh.geometry.getAttribute('aDist') as THREE.InstancedBufferAttribute).setX(i, p.distanceM);
      }
      meshes.forEach((m, ci) => {
        m.count = counts[ci];
        m.instanceMatrix.needsUpdate = true;
        (m.geometry.getAttribute('aDist') as THREE.InstancedBufferAttribute).needsUpdate = true;
      });
    });
  }, [meshes, meta, slope, groundHeight, verticalExaggeration, tmp]);

  // Per frame: the state machine drives every shader through the shared uniforms.
  const last = useRef<ScanState | null>(null);
  useFrame(() => {
    const snap = scanController.snapshot();
    const u = scanUniforms;
    if (snap.origin) u.uScanOrigin.value.set(snap.origin.x, snap.origin.z);
    u.uScanRadius.value = snap.radiusM;
    u.uScanTime.value = Number.isFinite(snap.ageS) ? snap.ageS : 1e6;
    u.uScanIntensity.value = snap.effect;
    u.uScanSpeed.value = SCAN_CONFIG.rangeM / scanController.sweepS();
    const visible = snap.effect > 0;
    for (const m of meshes) m.visible = visible && m.count > 0;
    if (last.current === 'SCANNING' && snap.state === 'COOLDOWN') scanAudio.complete();
    if (last.current === 'COOLDOWN' && snap.state === 'READY') scanAudio.ready();
    last.current = snap.state;
  });

  return (
    <group name="terrain-scanner">
      {meshes.map((m) => (
        <primitive key={m.name} object={m} />
      ))}
    </group>
  );
}
