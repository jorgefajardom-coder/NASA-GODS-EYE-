import type { GeologyData } from './geology';

/**
 * Schematic stratigraphy for the cut-away block of the Ground layers tab.
 *
 * ORDER (youngest first) follows the unit interpretations of USGS SIM 3464 (Sun and Stack,
 * 2020): Aeb is Amazonian unconsolidated bedforms; NHjf2 (Late Noachian-Early Hesperian fan)
 * overlies NHjf1; Njf was emplaced in the Late Noachian before NHjf1; Nue is an ash deposit
 * draping older units (its position relative to Njf is not stated by the map and is assumed
 * here). THICKNESSES ARE SCHEMATIC: the map gives no unit thickness at this site. Colours are
 * display rock tones chosen from the reported character (light-toned, mafic, clay/carbonate),
 * not measured colours.
 */
export interface Stratum {
  /** SIM 3464 map symbol, or 'base' for the undifferentiated older crust below the mapped units. */
  symbol: string;
  label: string;
  thicknessM: number;
  rgb: [number, number, number];
  /** Short composition note drawn from the map's unit characteristics. */
  composition: string;
}

export const STRATA_ORDER: Stratum[] = [
  { symbol: 'Aeb', label: 'Eolian bedforms', thicknessM: 3, rgb: [0.78, 0.6, 0.42], composition: 'Unconsolidated wind-blown sediment (transverse aeolian ridges).' },
  { symbol: 'NHjf2', label: 'Jezero fan 2 (delta)', thicknessM: 35, rgb: [0.55, 0.6, 0.52], composition: 'Stratified deltaic deposits associated with Fe/Mg clay and carbonate.' },
  { symbol: 'Njf', label: 'Jezero floor', thicknessM: 25, rgb: [0.36, 0.3, 0.26], composition: 'Volcanic ash or airfall drape of mafic composition.' },
  { symbol: 'Nue', label: 'Upper etched', thicknessM: 30, rgb: [0.7, 0.66, 0.5], composition: 'Light-toned ash or clastic deposit associated with olivine and variable carbonate.' },
  { symbol: 'base', label: 'Older crust (undifferentiated)', thicknessM: 40, rgb: [0.28, 0.2, 0.17], composition: 'Below the mapped units; not described at this site.' },
];

/** Total schematic depth of the block below the lowest terrain point (m). */
export const CUT_DEPTH_M = STRATA_ORDER.reduce((s, x) => s + x.thicknessM, 0);

/**
 * Layers under a surface point: the column starts with the unit exposed at the surface and
 * continues with every older stratum. Unknown surface units start at the base.
 */
export function columnBelow(surfaceSymbol: string | null): Stratum[] {
  const k = STRATA_ORDER.findIndex((s) => s.symbol === surfaceSymbol);
  return STRATA_ORDER.slice(k < 0 ? STRATA_ORDER.length - 1 : k);
}

/** Unit symbol exposed at grid cell (row, col) of a rasterized geology grid, or null. */
export function surfaceSymbolAt(data: GeologyData, grid: Int16Array, n: number, row: number, col: number): string | null {
  const v = grid[Math.min(n - 1, Math.max(0, row)) * n + Math.min(n - 1, Math.max(0, col))];
  return v < 0 ? null : data.units[v].symbol;
}
