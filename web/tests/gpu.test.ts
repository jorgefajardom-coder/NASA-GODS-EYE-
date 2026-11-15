import { describe, expect, it } from 'vitest';
import { chooseTier } from '../src/lib/gpu';

const hw = { webgl: true, majorCaveat: false, renderer: 'ANGLE (NVIDIA GeForce RTX 3060 Direct3D11)' };

describe('chooseTier', () => {
  it('keeps the full 3D view on a hardware GPU', () => {
    expect(chooseTier(hw, null)).toBe('full');
  });

  it('falls back to the 2D map without WebGL, even when full is forced', () => {
    const none = { webgl: false, majorCaveat: false, renderer: '' };
    expect(chooseTier(none, null)).toBe('map2d');
    expect(chooseTier(none, 'full')).toBe('map2d');
  });

  it('uses the lite 3D view on software rasterisers or a flagged slow GPU', () => {
    expect(chooseTier({ ...hw, renderer: 'Google SwiftShader' }, null)).toBe('lite');
    expect(chooseTier({ ...hw, renderer: 'llvmpipe (LLVM 15.0.7, 256 bits)' }, null)).toBe('lite');
    expect(chooseTier({ ...hw, renderer: 'ANGLE (Microsoft Basic Render Driver)' }, null)).toBe('lite');
    expect(chooseTier({ ...hw, majorCaveat: true }, null)).toBe('lite');
  });

  it('honours the URL override', () => {
    expect(chooseTier(hw, '2d')).toBe('map2d');
    expect(chooseTier(hw, 'lite')).toBe('lite');
    expect(chooseTier({ ...hw, renderer: 'SwiftShader' }, 'full')).toBe('full');
  });
});
