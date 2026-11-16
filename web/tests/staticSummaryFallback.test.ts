// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// The inline head script of index.html that hides the no-JavaScript summary while the app starts.
const html = readFileSync(resolve(__dirname, '../index.html'), 'utf8');
const startupScript = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1])
  .find((code) => code.includes("classList.add('js')"));

const summaryHidden = () => document.documentElement.classList.contains('js');

describe('static text summary when the viewer fails to start', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    document.documentElement.className = '';
    document.body.innerHTML = '<div id="root"><main class="static-summary"><h1>Summary</h1></main></div>';
    expect(startupScript).toBeDefined();
    new Function(startupScript!)();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    document.body.innerHTML = '';
    document.documentElement.className = '';
  });

  it('hides the summary while the app starts', () => {
    expect(summaryHidden()).toBe(true);
    vi.advanceTimersByTime(5000);
    expect(summaryHidden()).toBe(true);
  });

  it('shows the summary again when the module script fails to load', () => {
    const script = document.createElement('script');
    script.type = 'module';
    document.body.appendChild(script);
    script.dispatchEvent(new Event('error'));
    expect(summaryHidden()).toBe(false);
  });

  it('shows the summary again when the app has not started after the timeout', () => {
    vi.advanceTimersByTime(6000);
    expect(summaryHidden()).toBe(false);
  });

  it('keeps it hidden once the app has replaced the summary', () => {
    document.getElementById('root')!.innerHTML = '<canvas></canvas>';
    vi.advanceTimersByTime(6000);
    document.body.appendChild(document.createElement('script')).dispatchEvent(new Event('error'));
    expect(summaryHidden()).toBe(true);
  });

  it('ignores errors from other elements such as images', () => {
    document.body.appendChild(document.createElement('img')).dispatchEvent(new Event('error'));
    expect(summaryHidden()).toBe(true);
  });
});
