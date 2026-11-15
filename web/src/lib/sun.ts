import * as THREE from 'three';

/**
 * Key light of the 3D view (Three.js axes), as a unit vector from the scene centre. One place, so the
 * light and the astronaut's projected shadow agree. SkyDome updates both vectors in place every
 * second: by day they follow the Sun at the real present time at the site (Mars24, lib/marsSky); at
 * night they blend to a dim overhead fill so the terrain stays readable (a display choice, not
 * starlight). The value below is only the start-up direction.
 */
export const SUN_FROM = new THREE.Vector3(-1.2, 0.55, 0.35).normalize();

/** Direction the sunlight travels (towards the ground). */
export const SUN_DIR = SUN_FROM.clone().negate();
