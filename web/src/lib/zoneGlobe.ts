/**
 * Geometry of the zone selector's globe, kept free of three.js and the DOM so it can be tested:
 * where a zone sits on the sphere, how to turn the globe so it faces the camera, the title arcs on the
 * planet's left side and the card's radial left edge. Display only.
 */

/** Unit vector of a point on a three.js SphereGeometry textured with an equirectangular map whose column 0 is 180 W. */
export function globeDir(latDeg: number, lonDeg: number): [number, number, number] {
  const phi = ((lonDeg + 180) / 360) * Math.PI * 2;
  const theta = ((90 - latDeg) / 180) * Math.PI;
  return [-Math.cos(phi) * Math.sin(theta), Math.cos(theta), Math.sin(phi) * Math.sin(theta)];
}

/** Globe rotation (Euler XYZ: yaw about Y first, then pitch about X) that brings a point to face the camera (+Z). */
export function aimAt(latDeg: number, lonDeg: number): { x: number; y: number } {
  const [x, y, z] = globeDir(latDeg, lonDeg);
  return { y: -Math.atan2(x, z), x: Math.atan2(y, Math.hypot(x, z)) };
}

/** Applies Euler XYZ (x, y) to a vector, as three.js does: v' = Rx(Ry(v)). */
export function rotateXY(v: [number, number, number], rx: number, ry: number): [number, number, number] {
  const [x0, y0, z0] = v;
  const x1 = x0 * Math.cos(ry) + z0 * Math.sin(ry);
  const z1 = -x0 * Math.sin(ry) + z0 * Math.cos(ry);
  return [x1, y0 * Math.cos(rx) - z1 * Math.sin(rx), y0 * Math.sin(rx) + z1 * Math.cos(rx)];
}

/** Shortest signed angle from a to b (radians), so the globe never spins the long way round. */
export function angleDelta(a: number, b: number): number {
  const d = b - a;
  return Math.atan2(Math.sin(d), Math.cos(d));
}

/**
 * SVG arc on the planet's left side, centred on its left point and spanning +-halfAngle, drawn from bottom to top
 * so text on it reads upwards (screen coordinates, y down).
 */
export function leftArc(cx: number, cy: number, r: number, halfAngle: number): string {
  const a0 = Math.PI - halfAngle;
  const a1 = Math.PI + halfAngle;
  const p = (a: number) => `${(cx + r * Math.cos(a)).toFixed(1)} ${(cy + r * Math.sin(a)).toFixed(1)}`;
  return `M${p(a0)} A${r.toFixed(1)} ${r.toFixed(1)} 0 0 1 ${p(a1)}`;
}

/**
 * Card placed radially against the planet: its left side is an arc of radius `gapR` centred on the globe. Returns
 * the card's left and width, how far the arc reaches into it at mid-height (the content's left padding), and the
 * arc's x at the card's top and bottom edges. The card stays inside the screen (right margin), overlapping the
 * arc further when the globe is large.
 */
export function radialCard(
  cx: number,
  gapR: number,
  halfHeight: number,
  baseWidth: number,
  screenWidth: number,
  margin: number,
): { left: number; width: number; intrusion: number; edgeX: number } {
  const depth = halfHeight < gapR ? gapR - Math.sqrt(gapR * gapR - halfHeight * halfHeight) : gapR;
  const left = Math.min(cx + gapR - depth, screenWidth - margin - baseWidth - depth);
  const intrusion = cx + gapR - left;
  const width = Math.min(baseWidth + intrusion, screenWidth - margin - left);
  const edgeX = cx + Math.sqrt(Math.max(0, gapR * gapR - halfHeight * halfHeight));
  return { left, width, intrusion, edgeX };
}
