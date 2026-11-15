import { describe, expect, it } from 'vitest';
import { labelPriority, pickVisibleLabels } from '../src/lib/labelDeclutter';

const box = (left: number, top: number, w = 60, h = 16) => ({ left, top, right: left + w, bottom: top + h });

describe('label declutter', () => {
  it('shows every label when none overlaps', () => {
    const shown = pickVisibleLabels([
      { id: 'a', box: box(0, 0), priority: 1 },
      { id: 'b', box: box(100, 0), priority: 1 },
      { id: 'c', box: box(0, 40), priority: 1 },
    ]);
    expect([...shown].sort()).toEqual(['a', 'b', 'c']);
  });

  it('hides the lower-priority label of an overlapping pair, whatever the order', () => {
    const items = [
      { id: 'route', box: box(10, 4), priority: 5 },
      { id: 'agent', box: box(0, 0), priority: 1 },
    ];
    expect([...pickVisibleLabels(items)]).toEqual(['agent']);
    expect([...pickVisibleLabels([...items].reverse())]).toEqual(['agent']);
  });

  it('keeps a label that only the hidden one overlapped', () => {
    const shown = pickVisibleLabels([
      { id: 'top', box: box(0, 0), priority: 0 },
      { id: 'mid', box: box(40, 0), priority: 1 }, // overlaps top: hidden
      { id: 'far', box: box(90, 0), priority: 2 }, // overlaps only mid: shown
    ]);
    expect([...shown].sort()).toEqual(['far', 'top']);
  });

  it('keeps a small gap between shown labels', () => {
    const shown = pickVisibleLabels([
      { id: 'a', box: box(0, 0, 50), priority: 0 },
      { id: 'b', box: box(52, 0, 50), priority: 1 }, // 2 px apart: closer than the padding
    ]);
    expect([...shown]).toEqual(['a']);
  });

  it('orders the kinds of label: selected agent, agents, base and goal, other sites, stops, routes', () => {
    // The tests run without a DOM: a stand-in with the one method the priority reads.
    const el = (cls: string) => ({ classList: { contains: (c: string) => cls.split(' ').includes(c) } }) as unknown as Element;
    const p = (cls: string) => labelPriority(el(cls));
    expect(p('agent-label agent-label--selected')).toBeLessThan(p('agent-label'));
    expect(p('agent-label')).toBeLessThan(p('site-label site-label--base'));
    expect(p('site-label site-label--base')).toBeLessThan(p('site-label site-label--poi'));
    expect(p('site-label site-label--poi')).toBeLessThan(p('stop-tag'));
    expect(p('stop-tag')).toBeLessThan(p('route-label'));
  });
});
