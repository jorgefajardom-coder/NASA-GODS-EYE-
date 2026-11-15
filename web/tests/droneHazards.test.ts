import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { droneHazardReport, droneReportEvents } from '../src/lib/droneHazards';
import type { RasterSet } from '../src/types/replay';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const rasters = JSON.parse(readFileSync(join(dir, 'rasters.json'), 'utf8')) as RasterSet;
const meta = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8')).terrain_meta;
const timeline = JSON.parse(readFileSync(join(dir, 'timeline.json'), 'utf8'));

describe('drone hazard report', () => {
  it('reports nothing before the drone publishes its observations', () => {
    const r = droneHazardReport(rasters, meta, 1, 0, 0);
    expect(r.observedCount).toBe(0);
    expect(r.nearest).toBeNull();
  });

  it('classifies the observed cells of map v2 from the updated heights', () => {
    const r = droneHazardReport(rasters, meta, 2, 0, 0);
    const observed = rasters.versions[2].observed.length;
    expect(observed).toBeGreaterThan(0);
    expect(r.observedCount).toBe(observed);
    expect(r.counts.hazard + r.counts.caution + r.counts.changed + r.counts.clear).toBe(observed);
    expect(r.counts.hazard).toBeGreaterThan(0); // the steep scarp the survey found
    expect(r.cells.filter((c) => c.changed).length).toBeGreaterThan(0); // contradicts the orbital estimate
    expect(r.maxSlopeDeg ?? 0).toBeGreaterThanOrEqual(15);
    expect(r.nearest).not.toBeNull();
  });

  it('links the drone map update to the route it invalidated', () => {
    const before = droneReportEvents(timeline.events, 'drone_1', 300);
    expect(before.mapUpdate).toBeNull();
    const after = droneReportEvents(timeline.events, 'drone_1', 400);
    expect(after.mapUpdate?.event_type).toBe('MAP_UPDATED');
    expect(after.invalidated?.event_type).toBe('ROUTE_INVALIDATED');
  });
});
