/**
 * Geometry of the zone-arrival transition: the zone's orbital image starts full screen and lays itself
 * down on the terrain footprint it is draped on. Display only.
 */

/** Four screen points (CSS px, client coordinates): top-left, top-right, bottom-right, bottom-left of the image. */
export type Quad = [[number, number], [number, number], [number, number], [number, number]];

/**
 * Shared between the 3D scene (writer) and the arrival overlay (reader), outside React so the scene does
 * not re-render: while `want` is set the scene projects the imagery footprint to `quad` every frame.
 */
export const arrivalView: { want: boolean; quad: Quad | null } = { want: false, quad: null };

/** The rectangle that covers a vw x vh screen with a w x h image, centred (CSS object-fit: cover). */
export function coverQuad(w: number, h: number, vw: number, vh: number): Quad {
  const s = Math.max(vw / w, vh / h);
  const x0 = (vw - w * s) / 2;
  const y0 = (vh - h * s) / 2;
  const x1 = x0 + w * s;
  const y1 = y0 + h * s;
  return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
}

export function lerpQuad(a: Quad, b: Quad, k: number): Quad {
  return a.map(([x, y], n) => [x + (b[n][0] - x) * k, y + (b[n][1] - y) * k]) as Quad;
}

/**
 * CSS `matrix3d` that maps a w x h element (transform-origin 0 0) onto the quad: the projective map of
 * the unit square to a quadrilateral (Heckbert 1989), scaled to the element size.
 */
export function quadMatrix3d(w: number, h: number, q: Quad): string {
  const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = q;
  const sx = x0 - x1 + x2 - x3;
  const sy = y0 - y1 + y2 - y3;
  let a: number, b: number, d: number, e: number, g = 0, k = 0;
  if (Math.abs(sx) < 1e-9 && Math.abs(sy) < 1e-9) {
    a = x1 - x0; b = x3 - x0; d = y1 - y0; e = y3 - y0;
  } else {
    const dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2;
    const det = dx1 * dy2 - dx2 * dy1;
    g = (sx * dy2 - dx2 * sy) / det;
    k = (dx1 * sy - sx * dy1) / det;
    a = x1 - x0 + g * x1; b = x3 - x0 + k * x3;
    d = y1 - y0 + g * y1; e = y3 - y0 + k * y3;
  }
  const m = [a / w, d / w, 0, g / w, b / h, e / h, 0, k / h, 0, 0, 1, 0, x0, y0, 0, 1];
  return `matrix3d(${m.map((v) => +v.toPrecision(12)).join(',')})`;
}

/** Applies a matrix3d string to a point (px, py) of the element, as the browser does. */
export function applyMatrix3d(css: string, px: number, py: number): [number, number] {
  const m = css.slice(9, -1).split(',').map(Number);
  const x = m[0] * px + m[4] * py + m[12];
  const y = m[1] * px + m[5] * py + m[13];
  const w = m[3] * px + m[7] * py + m[15];
  return [x / w, y / w];
}

/** Smooth start and end. */
export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
