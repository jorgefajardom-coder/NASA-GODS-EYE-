/**
 * Estimated surface pressure over the mission area, for the atmospheric conditions map.
 *
 * Only one pressure is measured nearby: the latest Perseverance MEDA daily summary. Air pressure
 * falls with height (isothermal scale height of about 11.1 km on Mars), so each cell is given
 *   p = p_ref * exp(-(h - h_ref) / H)
 * from its drawn height h, with p_ref the MEDA value taken at the area's mean height h_ref. That
 * reference is an assumption (MEDA sits elsewhere in Jezero), so the map shows the relative
 * variation with terrain, a few pascals across the area, not a measured field. Display only.
 */
export const SCALE_HEIGHT_M = 11100;

export interface PressureField {
  /** Row-major estimate per cell (Pa), null where the height is NoData. */
  values: (number | null)[];
  min: number;
  max: number;
  /** Mean height used as the MEDA reference (m). */
  refHeightM: number;
}

export function pressureField(heights: ReadonlyArray<number | null>, pRefPa: number, scaleHeightM = SCALE_HEIGHT_M): PressureField | null {
  let sum = 0;
  let n = 0;
  for (const h of heights) {
    if (h != null && Number.isFinite(h)) {
      sum += h;
      n++;
    }
  }
  if (!n || !(pRefPa > 0) || !(scaleHeightM > 0)) return null;
  const ref = sum / n;
  let min = Infinity;
  let max = -Infinity;
  const values = heights.map((h) => {
    if (h == null || !Number.isFinite(h)) return null;
    const p = pRefPa * Math.exp(-(h - ref) / scaleHeightM);
    if (p < min) min = p;
    if (p > max) max = p;
    return p;
  });
  return { values, min, max, refHeightM: ref };
}
