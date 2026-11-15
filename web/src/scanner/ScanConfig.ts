/**
 * Terrain scan (first person): every tunable in one place. These are initial values of a visual
 * experience, not the specification of a physical sensor: the scan only redraws what the viewer
 * already has (the orbital slope classes and NoData of the current run) around the astronaut.
 */
export const SCAN_CONFIG = {
  /** Visual reach of the wave (m). */
  rangeM: 50,
  /** Propagation speed of the front (m/s); the wave reaches the edge in rangeM / speedMps seconds. */
  speedMps: 25,
  /** Width of the bright front (m). */
  widthM: 1.5,
  /** Indicators stay this long after the front passes them (s), then fade over fadeS. */
  persistS: 5,
  fadeS: 2,
  /** Indicator spacing near the origin and at the edge of the range (m); it grows linearly between. */
  spacingNearM: 0.5,
  spacingFarM: 2,
  /** Upper bound of indicator instances (pool size). */
  maxIndicators: 6000,
  /** Lift above the surface to avoid z-fighting (m). */
  liftM: 0.04,
  /** Main colour (Signal Blue). */
  color: '#65CBE8',
  /** Recharge after the front reaches the edge (s). */
  cooldownS: 3,
  /** Keyboard trigger in first person (KeyboardEvent.code). */
  key: 'KeyQ',
  keyLabel: 'Q',
  /** Button diameter (px). */
  buttonPx: 56,
  /** Optional synthesised sounds (Web Audio; original, no recorded samples). */
  sound: true,
  soundVolume: 0.12,
  /** Interval of the temporary contour lines drawn in the swept area (m of real height). */
  contourStepM: 1,
} as const;

export type ScanConfig = typeof SCAN_CONFIG;

/** Indicator classes, from the viewer's existing orbital slope bands and NoData (lib/scan). */
export type IndicatorClass = 'traversable' | 'caution' | 'hazard' | 'unknown';

export const INDICATOR_STYLE: Record<IndicatorClass, { color: string; label: string; glyph: 'dot' | 'triangle' | 'cross' | 'diamond' }> = {
  traversable: { color: '#65CBE8', label: 'Gentle slope (model)', glyph: 'dot' },
  caution: { color: '#E3C25A', label: 'Moderate slope: caution', glyph: 'triangle' },
  hazard: { color: '#E0583F', label: 'Steep slope: hazard', glyph: 'cross' },
  unknown: { color: '#8A9096', label: 'No data', glyph: 'diamond' },
};
