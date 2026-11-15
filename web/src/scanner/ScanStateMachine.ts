/**
 * Single source of truth for the terrain scan: READY -> SCANNING -> COOLDOWN -> READY, plus DISABLED
 * when the scan cannot run. Time is passed in (milliseconds, e.g. performance.now()), so the state
 * is the same for the button, the shaders and the tests, and independent of the frame rate.
 */
export type ScanState = 'READY' | 'SCANNING' | 'COOLDOWN' | 'DISABLED';

export interface ScanTiming {
  rangeM: number;
  speedMps: number;
  cooldownS: number;
  persistS: number;
  fadeS: number;
}

export interface ScanOrigin {
  /** Three.js world position of the scan origin (fixed for the whole scan). */
  x: number;
  y: number;
  z: number;
}

export interface ScanSnapshot {
  state: ScanState;
  /** Front radius (m) of the current or last scan; 0 before the first. */
  radiusM: number;
  /** Seconds since the last scan started, or Infinity. */
  ageS: number;
  /** 0..1 while SCANNING (front position / range), 1 afterwards. */
  scanProgress: number;
  /** 0..1 recharge while COOLDOWN, 1 when READY. */
  cooldownProgress: number;
  cooldownLeftS: number;
  /** 0..1 overall visibility of the scan effects (fades out after persist + fade). */
  effect: number;
  origin: ScanOrigin | null;
  /** Increments with each scan, so consumers can rebuild per-scan buffers once. */
  scanId: number;
  reason: string | null;
}

export class ScanStateMachine {
  private startMs = -Infinity;
  private origin: ScanOrigin | null = null;
  private id = 0;
  private available = false;
  private reason: string | null = 'Scanner not ready';

  constructor(private timing: ScanTiming) {}

  /** Seconds the front takes to reach the edge of the range. */
  get sweepS(): number {
    return this.timing.rangeM / this.timing.speedMps;
  }

  setTiming(timing: ScanTiming): void {
    this.timing = timing;
  }

  /** Enables the scanner, or disables it with the reason shown to the user. */
  setAvailable(ok: boolean, reason: string | null = null): void {
    this.available = ok;
    this.reason = ok ? null : reason ?? 'Scanner unavailable';
  }

  /** Starts a scan if READY. Returns false (and changes nothing) otherwise: no simultaneous scans. */
  trigger(nowMs: number, origin: ScanOrigin): boolean {
    if (this.snapshot(nowMs).state !== 'READY') return false;
    this.startMs = nowMs;
    this.origin = { ...origin };
    this.id += 1;
    return true;
  }

  snapshot(nowMs: number): ScanSnapshot {
    const t = this.timing;
    const ageS = Number.isFinite(this.startMs) ? Math.max(0, (nowMs - this.startMs) / 1000) : Infinity;
    const sweep = this.sweepS;
    const radiusM = Number.isFinite(ageS) ? Math.min(t.rangeM, ageS * t.speedMps) : 0;
    const lifeS = sweep + t.persistS + t.fadeS;
    const effect = !Number.isFinite(ageS) || ageS >= lifeS ? 0 : ageS <= sweep + t.persistS ? 1 : 1 - (ageS - sweep - t.persistS) / t.fadeS;
    let state: ScanState;
    if (ageS < sweep) state = 'SCANNING';
    else if (ageS < sweep + t.cooldownS) state = 'COOLDOWN';
    else state = this.available ? 'READY' : 'DISABLED';
    // A scan in flight finishes even if the data goes away; a new one needs the scanner available.
    if (state === 'READY' && !this.available) state = 'DISABLED';
    const scanProgress = state === 'SCANNING' ? ageS / sweep : Number.isFinite(ageS) ? 1 : 0;
    const cooldownLeftS = state === 'COOLDOWN' ? Math.max(0, sweep + t.cooldownS - ageS) : 0;
    const cooldownProgress = state === 'COOLDOWN' ? 1 - cooldownLeftS / t.cooldownS : state === 'SCANNING' ? 0 : 1;
    return {
      state,
      radiusM,
      ageS,
      scanProgress,
      cooldownProgress,
      cooldownLeftS,
      effect,
      origin: this.origin,
      scanId: this.id,
      reason: state === 'DISABLED' ? this.reason : null,
    };
  }
}
