import { describe, expect, it } from 'vitest';
import { SITE_KINDS, siteColor, siteKind } from '../src/lib/siteKinds';

describe('site kinds', () => {
  it('gives every kind a distinct icon, colour and short label', () => {
    const kinds = Object.values(SITE_KINDS);
    expect(new Set(kinds.map((k) => k.path)).size).toBe(kinds.length);
    expect(new Set(kinds.map((k) => k.short)).size).toBe(kinds.length);
    for (const k of kinds) expect(k.color).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });

  it('falls back to a plain point of interest for an unknown kind', () => {
    expect(siteKind('something_new')).toBe(SITE_KINDS.poi);
  });

  it('colours a rejected or done task over the kind colour', () => {
    expect(siteColor('poi', 'REJECTED')).toBe('#D95045');
    expect(siteColor('poi', 'DONE')).toBe('#65CBE8');
    expect(siteColor('base')).toBe(SITE_KINDS.base.color);
  });
});
