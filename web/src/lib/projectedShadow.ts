import * as THREE from 'three';
import { SUN_DIR } from './sun';

/**
 * Planar projected shadow shared by the astronaut, the rover and the drone (display only): each
 * mesh is drawn a second time with this material, flattened onto the ground plane along the display
 * sun direction. The shadow of a part follows its animation (it is a twin of the same node) and,
 * for a drone in flight, falls where the sun direction puts it, away from the aircraft.
 *
 * It is drawn after the route line and the terrain overlays (render order), so the line passes under
 * it and is darkened like the ground; a stencil keeps overlapping parts from darkening twice.
 */
export const SHADOW_OPACITY = 0.42;
export const SHADOW_RENDER_ORDER = 6;
/** How far towards the camera the shadow's depth is tested (m), to ride over terrain bumps. */
export const SHADOW_DEPTH_PULL_M = 0.6;

export interface ProjectedShadow {
  /** Live uniforms: `uGround` is the ground height (Three.js y) under the object, `uLight` the sun direction. */
  uniforms: { uGround: { value: number }; uLight: { value: THREE.Vector3 } };
  material: THREE.MeshBasicMaterial;
}

export function createProjectedShadow(opacity = SHADOW_OPACITY): ProjectedShadow {
  const uniforms = { uGround: { value: 0 }, uLight: { value: SUN_DIR } }; // live: SkyDome moves the sun
  const material = new THREE.MeshBasicMaterial({
    color: 0x000000,
    transparent: true,
    opacity,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -4,
    polygonOffsetUnits: -4,
    stencilWrite: true,
    stencilRef: 1,
    stencilFunc: THREE.NotEqualStencilFunc,
    stencilZPass: THREE.ReplaceStencilOp,
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uGround = uniforms.uGround;
    shader.uniforms.uLight = uniforms.uLight;
    shader.vertexShader = `uniform float uGround;\nuniform vec3 uLight;\n${shader.vertexShader}`.replace(
      '#include <project_vertex>',
      `vec4 wp = modelMatrix * vec4( transformed, 1.0 );
        wp.xyz += uLight * ( ( wp.y - uGround ) / max( -uLight.y, 0.05 ) );
        wp.y = uGround;
        vec4 mvPosition = viewMatrix * wp;
        gl_Position = projectionMatrix * mvPosition;
        // The shadow is flat but the drawn ground has bumps: test its depth as if it were a little
        // closer to the camera, so terrain humps do not cut it (its place on screen is unchanged).
        vec4 pulled = mvPosition;
        pulled.xyz *= max( 0.0, 1.0 - ${SHADOW_DEPTH_PULL_M.toFixed(2)} / max( length( mvPosition.xyz ), 1e-3 ) );
        vec4 pc = projectionMatrix * pulled;
        gl_Position.z = pc.z / pc.w * gl_Position.w;`,
    );
  };
  return { uniforms, material };
}
