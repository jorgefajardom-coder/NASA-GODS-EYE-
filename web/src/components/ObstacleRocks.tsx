import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { TerrainMeta } from '../types/icd';
import { enuToThree } from '../lib/coords';
import { obstacleRocks, ROCK_VARIANTS, type RockPiece } from '../lib/obstacleRocks';

/** Shading of one shape: shadowed underside to a reddish dust coat on top (multiplies the unit colour). */
const UNDERSIDE = new THREE.Color(0.55, 0.52, 0.5);
const DUST = new THREE.Color(1.35, 1.0, 0.78);

function hash3(x: number, y: number, z: number, seed: number): number {
  const s = Math.sin(x * 127.1 + y * 311.7 + z * 74.7 + seed * 19.19) * 43758.5453;
  return s - Math.floor(s);
}

/**
 * One angular boulder shape: a subdivided icosahedron whose vertices are pushed in and out by a
 * seeded function of their position (so shared vertices stay joined), with a flattened base and a
 * squat profile. Faceted shading gives the broken-face look of basalt blocks; vertex colours put
 * reddish dust on the upper faces and dark rock below.
 */
function boulderGeometry(seed: number): THREE.BufferGeometry {
  const g = new THREE.IcosahedronGeometry(0.5, 1);
  const pos = g.getAttribute('position') as THREE.BufferAttribute;
  const v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const key = [Math.round(v.x * 1e4), Math.round(v.y * 1e4), Math.round(v.z * 1e4)];
    const bump = 0.72 + 0.5 * hash3(key[0], key[1], key[2], seed);
    v.multiplyScalar(bump);
    v.y = Math.max(v.y * 0.8, -0.22); // flat underside where it rests on the ground
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  const colors = new Float32Array(pos.count * 3);
  const c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const up = THREE.MathUtils.clamp((pos.getY(i) + 0.22) / 0.62, 0, 1);
    c.copy(UNDERSIDE).lerp(DUST, up * up * (0.75 + 0.25 * hash3(i, seed, 1, 7)));
    colors.set([c.r, c.g, c.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  return g;
}

function RockVariant({ geometry, material, pieces, groundHeight, verticalExaggeration }: {
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
  pieces: RockPiece[];
  groundHeight: (x: number, y: number) => number | null;
  verticalExaggeration: number;
}) {
  const ref = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const s = new THREE.Vector3();
    const p = new THREE.Vector3();
    const tint = new THREE.Color();
    pieces.forEach((rock, i) => {
      const z = groundHeight(rock.x, rock.y) ?? 0;
      const [x, y, zz] = enuToThree({ x: rock.x, y: rock.y, z }, verticalExaggeration);
      // Partly buried: the base sits below the ground by sinkM.
      p.set(x, y + rock.heightM * 0.22 - rock.sinkM, zz);
      q.setFromEuler(new THREE.Euler(rock.tiltRad, rock.yawRad, rock.tiltRad * 0.6));
      s.set(rock.widthM, rock.heightM, rock.depthM);
      m.compose(p, q, s);
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, tint.set(rock.style.colorHex).multiplyScalar(rock.shade));
    });
    mesh.count = pieces.length;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere();
  }, [pieces, groundHeight, verticalExaggeration]);
  if (!pieces.length) return null;
  return <instancedMesh ref={ref} args={[geometry, material, pieces.length]} castShadow receiveShadow />;
}

/**
 * Boulder clusters on the cells the current recorded map version marks impassable (public rasters
 * `impassable`, from the mapping's human traversability). Sizes follow the Golombek-Rapp rock
 * size law and the style follows the cell's USGS geologic unit (lib/obstacleRocks). Every rock
 * rests on the drawn ground inside its cell, so none leaves the terrain. Display only: shapes,
 * sizes and colours are illustrative, not measurements.
 */
export function ObstacleRocks({ meta, cells, unitAt, groundHeight, verticalExaggeration }: {
  meta: Pick<TerrainMeta, 'rows' | 'cols' | 'origin_x_m' | 'origin_y_m' | 'resolution_m'>;
  cells: readonly number[] | undefined;
  /** USGS geologic unit symbol of a cell, when the run has a matching geologic map. */
  unitAt?: (cell: number) => string | null;
  groundHeight: (x: number, y: number) => number | null;
  verticalExaggeration: number;
}) {
  const pieces = useMemo(() => obstacleRocks(meta, cells, unitAt), [meta, cells, unitAt]);
  const geometries = useMemo(() => Array.from({ length: ROCK_VARIANTS }, (_, i) => boulderGeometry(i + 1)), []);
  const material = useMemo(() => new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.96, metalness: 0, flatShading: true }), []);
  useLayoutEffect(() => () => {
    geometries.forEach((g) => g.dispose());
    material.dispose();
  }, [geometries, material]);
  const byVariant = useMemo(() => {
    const groups: RockPiece[][] = Array.from({ length: ROCK_VARIANTS }, () => []);
    for (const p of pieces) groups[p.variant].push(p);
    return groups;
  }, [pieces]);
  if (!pieces.length) return null;
  return (
    <group name="obstacle-rocks">
      {byVariant.map((group, i) => (
        <RockVariant
          key={`${i}-${group.length}`}
          geometry={geometries[i]}
          material={material}
          pieces={group}
          groundHeight={groundHeight}
          verticalExaggeration={verticalExaggeration}
        />
      ))}
    </group>
  );
}
