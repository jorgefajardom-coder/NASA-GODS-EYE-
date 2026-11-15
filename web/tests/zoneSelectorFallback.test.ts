// @vitest-environment jsdom
import { act, createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ZoneSelector } from '../src/components/ZoneSelector';

const { renderer } = vi.hoisted(() => ({ renderer: vi.fn() }));
vi.mock('three', async (importOriginal) => ({
  ...(await importOriginal<typeof import('three')>()),
  WebGLRenderer: renderer,
}));

describe('zone selection without WebGL', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
    renderer.mockReset().mockImplementation(() => { throw new Error('No WebGL context'); });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('keeps zone navigation and entry available in the selected 2D tier', async () => {
    const close = vi.fn();
    await act(async () => root.render(createElement(ZoneSelector, { runId: 'demo', onClose: close, globeEnabled: false })));
    expect(renderer).not.toHaveBeenCalled();
    expect(container.querySelector('[role="dialog"]')?.classList.contains('zones--flat')).toBe(true);
    expect(container.textContent).toContain('Mars · 2D map');

    await act(async () => container.querySelector<HTMLButtonElement>('.zones__arrow--next')!.click());
    await act(async () => { vi.advanceTimersByTime(220); });
    expect(container.querySelector('.zones__name')?.textContent).toBe('Gale crater');

    await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true })); });
    await act(async () => { vi.advanceTimersByTime(220); });
    expect(container.querySelector('.zones__name')?.textContent).toBe('Jezero crater');
    await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); });
    expect(close).toHaveBeenCalledOnce();
  });

  it('keeps the page and escape action usable when context creation fails after probing', async () => {
    const close = vi.fn();
    await act(async () => root.render(createElement(ZoneSelector, { runId: 'demo', onClose: close })));
    expect(renderer).toHaveBeenCalledOnce();
    expect(container.querySelector('[role="dialog"]')?.classList.contains('zones--flat')).toBe(true);
    expect(container.querySelector('.zones__travel')).not.toBeNull();
    await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); });
    expect(close).toHaveBeenCalledOnce();
  });
});
