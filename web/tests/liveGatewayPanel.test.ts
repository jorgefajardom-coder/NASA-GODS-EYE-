// @vitest-environment jsdom
import { act, createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// A synthetic connected MOCK gateway state; no network, no ROS.
const { state } = vi.hoisted(() => ({
  state: {
    status: 'connected',
    base: 'http://127.0.0.1:8010',
    message: null,
    runId: 'run-1',
    sourceMode: 'MOCK',
    label: 'MOCK',
    datasetId: 'jezero_mvp',
    mission: {
      last_event_seq: 2,
      mission_state: 'READY',
      reason_code: '',
      map_version: 2,
      agents: [{ agent_id: 'human_1', mode: 'MOVING', pose: { position: { x: -14, y: -6.3, z: 0 } }, oxygen_remaining_l: 999 }],
    },
    events: [
      { seq: 1, event_type: 'MAP_UPDATED', detail: 'Map updated to version 2.' },
      { seq: 2, event_type: 'ROUTE_PUBLISHED', detail: 'Route published.' },
    ],
    transport: 'websocket',
    updatedAt: Date.now(),
  },
}));
vi.mock('../src/lib/gatewayLive', () => ({
  gatewayLive: { connect: vi.fn(), disconnect: vi.fn() },
  useGatewayLive: () => state,
}));

import { LiveGatewayPanel } from '../src/components/LiveGatewayPanel';

describe('live gateway panel', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root.render(createElement(LiveGatewayPanel, { base: 'http://127.0.0.1:8010' })));
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  it('starts as one line with the mission, map and newest event, labelled MOCK', () => {
    const text = container.textContent ?? '';
    expect(text).toContain('MOCK');
    expect(text).toContain('READY · map v2');
    expect(text).toContain('#2 ROUTE_PUBLISHED');
    expect(text).not.toMatch(/LIVE/);
    expect(container.querySelector('.live-gw__agents')).toBeNull();
    expect(container.querySelector('[aria-expanded]')?.getAttribute('aria-expanded')).toBe('false');
  });

  it('shows the agents and events only when expanded', () => {
    const toggle = container.querySelector<HTMLButtonElement>('[aria-expanded]')!;
    act(() => toggle.click());
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(container.querySelector('.live-gw__agents')?.textContent).toContain('human_1');
    expect(container.querySelectorAll('.live-gw__events li')).toHaveLength(2);
    act(() => toggle.click());
    expect(container.querySelector('.live-gw__agents')).toBeNull();
  });
});
