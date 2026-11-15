import { describe, expect, it } from 'vitest';
import { neighbourWorlds } from '../src/components/WorldArrows';

describe('world arrows', () => {
  it('leads to the other scene world on both sides, skipping a world without a scene', () => {
    const n = neighbourWorlds('demo');
    expect(n?.next.id).toBe('gale');
    expect(n?.prev.id).toBe('gale'); // two scenes: wraps to the same one
    expect(neighbourWorlds('gale-demo')?.next.id).toBe('jezero');
  });

  it('shows no arrows for a run outside the catalogue', () => {
    expect(neighbourWorlds('mock-vertical-001')).toBeNull();
  });
});
