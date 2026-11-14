import { describe, expect, it } from 'vitest';
import { displayState } from '../src/lib/provenance';

// Moved from src/lib/provenance.test.ts (node:test) so the web package keeps one runner (Vitest).
describe('display provenance', () => {
  it('replay and mock provenance never become LIVE', () => {
    expect(displayState({ mode: 'REPLAY', source: 'MOCK' }).label).toBe('REPLAY · MOCK');
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
});
