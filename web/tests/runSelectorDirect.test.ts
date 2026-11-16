// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { consumeDirectRun } from '../src/components/Frame';

describe('run selector opens the chosen run directly', () => {
  afterEach(() => window.sessionStorage.clear());

  it('skips the start screens once for the run the selector asked for', () => {
    window.sessionStorage.setItem('mge.directRun', 'gale-demo');
    expect(consumeDirectRun('gale-demo')).toBe(true);
    expect(consumeDirectRun('gale-demo')).toBe(false); // a later reload shows the start menu again
  });

  it('does not skip them for another run or a fresh visit', () => {
    window.sessionStorage.setItem('mge.directRun', 'gale-demo');
    expect(consumeDirectRun('demo')).toBe(false);
    expect(consumeDirectRun('demo')).toBe(false);
  });
});
