import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { AtmosList } from '../src/components/AtmosPanel';
import { parseAtmosphere } from '../src/lib/atmos';
import { zoneCrewDose } from '../src/lib/zoneEnvironment';

const data = parseAtmosphere(JSON.parse(readFileSync(join(import.meta.dirname, '../public/replay/demo/atmosphere.json'), 'utf8')))!;

describe('Atmos panel dose and sol count', () => {
  it('uses the zone rate for run totals, the same rate the HUD shows', () => {
    const day = 86400;
    const html = renderToStaticMarkup(createElement(AtmosList, { data, t: day, duration: 2 * day, runId: 'demo' }));
    const zone = zoneCrewDose('demo', day)!;
    expect(zone.msvPerDay).not.toBeCloseTo(data.radiation.dose_equivalent_msv_per_day, 2);
    expect(html).toContain(`${zone.usv.toFixed(0)} ± ${zone.sigmaUsv.toFixed(0)} µSv`);
    expect(html).toContain(`this zone&#x27;s surface rate (${zone.msvPerDay.toFixed(2)} mSv/day`);
    expect(html).toContain('Dose rate at Gale (RAD measured)');
  });

  it('has fewer sols with values than feed entries, so the panel counts the bins', () => {
    const used = data.gale_seasonal.bins.reduce((a, b) => a + b.n, 0);
    expect(used).toBeGreaterThan(0);
    expect(used).toBeLessThan(data.gale_seasonal.sols_used);
  });
});
