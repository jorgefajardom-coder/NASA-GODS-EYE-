import { SCAN_CONFIG } from './ScanConfig';
import { ScanStateMachine, type ScanOrigin, type ScanSnapshot } from './ScanStateMachine';

/**
 * The one scan controller of the app: the button, the Q key and the 3D scene all read this state
 * machine, and every activation goes through triggerScan(). The 3D scene registers where the scan
 * starts (the astronaut's current position) and plays the optional sounds.
 */
const reducedMotion = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

function timing() {
  // Reduced motion: the wave covers the range almost at once instead of travelling.
  const speedMps = reducedMotion() ? SCAN_CONFIG.rangeM / 0.25 : SCAN_CONFIG.speedMps;
  return { rangeM: SCAN_CONFIG.rangeM, speedMps, cooldownS: SCAN_CONFIG.cooldownS, persistS: SCAN_CONFIG.persistS, fadeS: SCAN_CONFIG.fadeS };
}

const machine = new ScanStateMachine(timing());
let originProvider: (() => ScanOrigin | null) | null = null;
const listeners = new Set<(s: ScanSnapshot, started: boolean) => void>();

export const scanController = {
  now: () => (typeof performance !== 'undefined' ? performance.now() : Date.now()),
  snapshot(): ScanSnapshot {
    return machine.snapshot(this.now());
  },
  /** Scene side: where a scan starts right now, or null when there is no astronaut to scan from. */
  setOriginProvider(fn: (() => ScanOrigin | null) | null) {
    originProvider = fn;
  },
  setAvailable(ok: boolean, reason: string | null = null) {
    machine.setAvailable(ok, reason);
  },
  /** Called with every started scan (sounds, per-scan buffers). Returns an unsubscribe function. */
  onScan(fn: (s: ScanSnapshot, started: boolean) => void) {
    listeners.add(fn);
    return () => void listeners.delete(fn);
  },
  sweepS: () => machine.sweepS,
};

/** The single activation path for the button and the keyboard. Returns true when a scan started. */
export function triggerScan(): boolean {
  const origin = originProvider?.();
  if (!origin) return false;
  machine.setTiming(timing());
  const now = scanController.now();
  const started = machine.trigger(now, origin);
  if (started) {
    const snap = machine.snapshot(now);
    for (const fn of listeners) fn(snap, true);
  }
  return started;
}
