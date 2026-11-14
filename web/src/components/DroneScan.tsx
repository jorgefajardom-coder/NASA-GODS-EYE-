import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { SCAN_CLASS_INFO, SCAN_HOLD_S, SCAN_RADIUS_M, SCAN_SWEEP_S, type ScanMark } from '../lib/scan';

export interface ScanRequest {
  /** Increments on every scan, so the same place can be scanned again. */
  seq: number;
  /** ENU origin on the ground under the drone (m). */
  x: number;
  y: number;
  marks: ScanMark[];
}

interface Props {
  scan: ScanRequest | null;
  /** Scene name of the drone group (beam apex), or null when there is none. */
  droneName: string | null;
  groundHeight: (x: number, y: number) => number | null;
  verticalExaggeration: number;
}

const RING_POINTS = 160;
const BEAMS = 4;
const MARK_SIZE_M = 1.3;
const MARK_LIFT_M = 0.8;
const FADE_S = 2;

/**
 * Drone camera scan (display only): a front sweeps outwards over the drawn ground from under the
 * drone, with beams from the drone camera to the front, and leaves a marker on each 20 m cell
 * coloured by its orbital slope band (lib/scan). No observation is made and no map data changes.
 */
export function DroneScan({ scan, droneName, groundHeight, verticalExaggeration }: Props) {
  const scene = useThree((s) => s.scene);
  const start = useRef<number | null>(null);
  const clock = useRef(0);
  const marks = useRef<THREE.InstancedMesh>(null);
  const ring = useRef<THREE.LineLoop | null>(null);
  const beams = useRef<THREE.LineSegments>(null);
  const apex = useRef(new THREE.Vector3());
  const m4 = useRef(new THREE.Matrix4());
  const q = useRef(new THREE.Quaternion());
  const s3 = useRef(new THREE.Vector3());
  const p3 = useRef(new THREE.Vector3());

  const geo = useMemo(() => new THREE.OctahedronGeometry(MARK_SIZE_M / 2, 0).scale(1, 1.6, 1), []);
  const mat = useMemo(() => new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.9, depthWrite: false, toneMapped: false }), []);
  const ringGeo = useMemo(() => new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(RING_POINTS * 3), 3)), []);
  const beamGeo = useMemo(() => new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(BEAMS * 2 * 3), 3)), []);
  const lineMat = useMemo(() => new THREE.LineBasicMaterial({ color: '#c9eaf3', transparent: true, opacity: 0.9, depthWrite: false, toneMapped: false }), []);
  const beamMat = useMemo(() => new THREE.LineBasicMaterial({ color: '#65cbe8', transparent: true, opacity: 0.6, depthWrite: false, toneMapped: false }), []);
  const loop = useMemo(() => new THREE.LineLoop(ringGeo, lineMat), [ringGeo, lineMat]);
  ring.current = loop;
  useEffect(() => () => [geo, mat, ringGeo, beamGeo, lineMat, beamMat].forEach((d) => d.dispose()), [geo, mat, ringGeo, beamGeo, lineMat, beamMat]);

  // Drawn heights and colours of the marks, fixed for one scan.
  const placed = useMemo(() => {
    if (!scan) return [];
    return scan.marks.map((mk) => {
      const h = groundHeight(mk.x, mk.y);
      return { mk, y: h == null ? null : h * verticalExaggeration, color: new THREE.Color(SCAN_CLASS_INFO[mk.cls].color) };
    });
  }, [scan, groundHeight, verticalExaggeration]);

  useEffect(() => {
    start.current = scan ? clock.current : null;
  }, [scan]);

  useFrame((_, dt) => {
    clock.current += Math.min(dt, 0.1);
    const im = marks.current;
    const rl = ring.current;
    const bl = beams.current;
    if (!im || !rl || !bl) return;
    const t0 = start.current;
    const age = t0 == null || !scan ? Infinity : clock.current - t0;
    const alive = age < SCAN_SWEEP_S + SCAN_HOLD_S;
    im.visible = alive;
    rl.visible = alive && age < SCAN_SWEEP_S + 0.4;
    bl.visible = rl.visible;
    if (!alive || !scan) return;

    const front = SCAN_RADIUS_M * Math.min(1, age / SCAN_SWEEP_S);
    const fade = Math.min(1, (SCAN_SWEEP_S + SCAN_HOLD_S - age) / FADE_S);
    mat.opacity = 0.9 * fade;

    // Marks pop in as the front passes them, then bob slightly.
    let n = 0;
    for (const p of placed) {
      if (p.y == null) continue;
      const since = age - (p.mk.distanceM / SCAN_RADIUS_M) * SCAN_SWEEP_S;
      const k = since <= 0 ? 0 : Math.min(1, since / 0.25);
      const bob = Math.sin((clock.current + p.mk.distanceM * 0.05) * 2) * 0.15;
      p3.current.set(p.mk.x, p.y + MARK_LIFT_M + bob, -p.mk.y);
      s3.current.setScalar(Math.max(1e-4, k));
      q.current.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, clock.current * 0.8);
      m4.current.compose(p3.current, q.current, s3.current);
      im.setMatrixAt(n, m4.current);
      // Colours are set in placement order; keep them aligned with the matrices.
      im.setColorAt(n, p.color);
      n++;
    }
    im.count = n;
    im.instanceMatrix.needsUpdate = true;
    if (im.instanceColor) im.instanceColor.needsUpdate = true;

    // Front: a loop draped on the drawn ground.
    const pos = ringGeo.getAttribute('position') as THREE.BufferAttribute;
    for (let i = 0; i < RING_POINTS; i++) {
      const a = (i / RING_POINTS) * Math.PI * 2;
      const x = scan.x + Math.cos(a) * front;
      const y = scan.y + Math.sin(a) * front;
      const h = groundHeight(x, y);
      pos.setXYZ(i, x, (h ?? 0) * verticalExaggeration + 0.6, -y);
    }
    pos.needsUpdate = true;
    lineMat.opacity = 0.9 * Math.max(0, 1 - age / (SCAN_SWEEP_S + 0.4));

    // Beams from the drone camera to four points of the front, turning as it sweeps.
    const drone = droneName ? scene.getObjectByName(droneName) : null;
    if (drone) drone.getWorldPosition(apex.current);
    else apex.current.set(scan.x, ((groundHeight(scan.x, scan.y) ?? 0) * verticalExaggeration) + 20, -scan.y);
    const bp = beamGeo.getAttribute('position') as THREE.BufferAttribute;
    for (let i = 0; i < BEAMS; i++) {
      const j = Math.floor(((i / BEAMS + age * 0.15) % 1) * RING_POINTS);
      bp.setXYZ(i * 2, apex.current.x, apex.current.y, apex.current.z);
      bp.setXYZ(i * 2 + 1, pos.getX(j), pos.getY(j), pos.getZ(j));
    }
    bp.needsUpdate = true;
    beamMat.opacity = 0.6 * Math.max(0, 1 - age / (SCAN_SWEEP_S + 0.4));
  });

  const capacity = Math.max(1, scan?.marks.length ?? 1);
  return (
    <group name="drone-scan">
      <instancedMesh key={capacity} ref={marks} args={[geo, mat, capacity]} frustumCulled={false} renderOrder={5} />
      <primitive object={loop} frustumCulled={false} />
      <lineSegments ref={beams} args={[beamGeo, beamMat]} frustumCulled={false} />
    </group>
  );
}
