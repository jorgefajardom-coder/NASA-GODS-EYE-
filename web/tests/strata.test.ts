import { describe, expect, it } from 'vitest';
import { CUT_DEPTH_M, STRATA_ORDER, columnBelow } from '../src/lib/strata';

describe('schematic strata of the cut-away block', () => {
  it('follows the SIM 3464 order, youngest first, ending in the undifferentiated base', () => {
    expect(STRATA_ORDER.map((s) => s.symbol)).toEqual(['Aeb', 'NHjf2', 'Njf', 'Nue', 'base']);
    expect(CUT_DEPTH_M).toBe(STRATA_ORDER.reduce((a, s) => a + s.thicknessM, 0));
  });

  it('starts each column with the unit exposed at the surface and keeps every older layer', () => {
    expect(columnBelow('Njf').map((s) => s.symbol)).toEqual(['Njf', 'Nue', 'base']);
    expect(columnBelow('Aeb')).toHaveLength(STRATA_ORDER.length);
    expect(columnBelow(null).map((s) => s.symbol)).toEqual(['base']);
  });
});
