import * as THREE from 'three';

/**
 * Display sun of the 3D view (Three.js axes): where the key light sits, as a unit vector from the
 * scene centre. One place, so the light and the astronaut's projected shadow agree. It is a
 * lighting choice for readability, not a computed solar position for the run.
 */
export const SUN_FROM = new THREE.Vector3(-1.2, 0.55, 0.35).normalize();

/** Direction the sunlight travels (towards the ground). */
export const SUN_DIR = SUN_FROM.clone().negate();
