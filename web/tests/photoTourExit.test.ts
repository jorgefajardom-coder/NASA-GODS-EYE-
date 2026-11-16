// @vitest-environment jsdom
import { act, createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FirstPersonHud } from '../src/components/FirstPersonHud';
import type { AgentState } from '../src/types/icd';

// A synthetic rover pose; the HUD only reads it for display.
const rover = {
  agent_id: 'rover_1',
  agent_kind: 'ROVER',
  mode: 'MOVING',
  pose: { position: { x: 0, y: 0, z: 0 }, orientation: { x: 0, y: 0, z: 0, w: 1 } },
} as unknown as AgentState;

const props = {
  agent: rover,
  sourceLabel: 'REPLAY · SIMULATION',
  pois: [],
  onExit: () => {},
  dial: null,
  alert: null,
  droneCam: null,
  droneCamOn: false,
  stops: [],
  marsNow: null,
  marsNowOn: false,
  onMarsNow: () => {},
  canDroneCam: false,
  onDroneCam: () => {},
  helmetLight: false,
  canHelmetLight: false,
  onHelmetLight: () => {},
  artificialLight: true,
  onArtificialLight: () => {},
  sway: false,
  onSway: () => {},
};

describe('photo tour exit in the rover HUD', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  const exitButton = () => [...container.querySelectorAll('button')].find((b) => b.textContent?.includes('Exit photo tour'));

  it('shows an exit button during the tour that leaves it', () => {
    const onEndTour = vi.fn();
    act(() => root.render(createElement(FirstPersonHud, { ...props, onEndTour })));
    const button = exitButton();
    expect(button).toBeDefined();
    act(() => button!.click());
    expect(onEndTour).toHaveBeenCalledTimes(1);
  });

  it('has no exit button outside the tour', () => {
    act(() => root.render(createElement(FirstPersonHud, { ...props, onEndTour: null })));
    expect(exitButton()).toBeUndefined();
  });
});
