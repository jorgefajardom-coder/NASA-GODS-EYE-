import { describe, expect, it } from 'vitest';
import { displayState, resolveSourceMode } from '../src/lib/provenance';

// Moved from src/lib/provenance.test.ts (node:test) so the web package keeps one runner (Vitest).
describe('display provenance', () => {
  it('replay and mock provenance never become LIVE', () => {
    expect(displayState({ mode: 'REPLAY', source: 'MOCK' }).label).toBe('REPLAY · MOCK');
    expect(displayState({ mode: 'REPLAY', source: 'SIMULATION' }).label).toBe('REPLAY · SIMULATION');
    expect(displayState({ mode: 'REPLAY', source: 'UNKNOWN' }).label).toBe('REPLAY · UNKNOWN');
    expect(displayState({ mode: 'LIVE', source: 'MOCK' }).state).toBe('MOCK');
    expect(displayState({ mode: 'LIVE', source: 'SIMULATION' }).label).toBe('SIMULATION · NOT VALIDATED LIVE');
    expect(displayState({ mode: 'LIVE', source: 'REAL' }).state).toBe('NOT_READY');
    expect(displayState({ mode: 'LIVE', source: 'REAL', validatedLive: true }).state).toBe('LIVE');
    expect(displayState({ mode: null, source: 'REAL' }).state).toBe('NOT_READY');
    expect(displayState({ mode: 'REPLAY', source: 'REAL', status: 'ERROR' }).state).toBe('ERROR');
  });

  it('external malformed mode cannot claim LIVE', () => {
    for (const mode of [undefined, 'MOCK', 'invalid', 1]) {
      expect(displayState({ mode, source: 'REAL', validatedLive: true } as unknown as Parameters<typeof displayState>[0]).state).toBe('NOT_READY');
    }
  });

  it('resolves source_mode as the ICD requires (§6.1)', () => {
    const real = { dataset_id: 'mars2020-trn-ctx-dtm-20m', sources: ['USGS CTX DTM'] };
    expect(resolveSourceMode(undefined, real)).toBe('UNKNOWN'); // absent field: UNKNOWN
    expect(resolveSourceMode('SIMULATION', real)).toBe('SIMULATION');
    expect(resolveSourceMode('UNKNOWN', { dataset_id: 'MOCK-flat-grid' })).toBe('MOCK'); // terrain evidence wins
    expect(resolveSourceMode('SIMULATION', { dataset_id: 'x', sources: ['MOCK flat grid'] })).toBe('MOCK');
    for (const bad of ['LIVE', 'REAL', 'mock', 1]) expect(resolveSourceMode(bad, real)).toBeNull(); // never declarable
  });
});
