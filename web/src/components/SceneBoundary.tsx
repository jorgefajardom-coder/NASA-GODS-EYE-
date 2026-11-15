import { Component, type ReactNode } from 'react';

/**
 * Catches a 3D view that fails to start (WebGL context refused or lost at creation) and shows the
 * fallback instead of a blank screen. The rest of the interface keeps working.
 */
export class SceneBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    console.warn('3D view failed to start; showing the 2D map instead.', error);
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
