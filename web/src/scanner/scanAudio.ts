import { SCAN_CONFIG } from './ScanConfig';

/**
 * Optional scan sounds, synthesised with the Web Audio API (original tones, no recorded samples):
 * a low sweeping pulse at activation, a soft confirmation when the front reaches the edge, and a
 * short tick when the scanner is ready again. The audio context is created on the first activation
 * (a user gesture), so browsers allow it.
 */
let ctx: AudioContext | null = null;

function context(): AudioContext | null {
  if (!SCAN_CONFIG.sound || typeof window === 'undefined') return null;
  try {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    ctx ??= new AC();
    if (ctx.state === 'suspended') void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

function tone(freqFrom: number, freqTo: number, durS: number, gain: number, type: OscillatorType = 'sine', delayS = 0) {
  const c = context();
  if (!c) return;
  const t0 = c.currentTime + delayS;
  const osc = c.createOscillator();
  const g = c.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freqFrom, t0);
  osc.frequency.exponentialRampToValueAtTime(Math.max(20, freqTo), t0 + durS);
  g.gain.setValueAtTime(0, t0);
  g.gain.linearRampToValueAtTime(gain * SCAN_CONFIG.soundVolume, t0 + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + durS);
  osc.connect(g).connect(c.destination);
  osc.start(t0);
  osc.stop(t0 + durS + 0.05);
}

export const scanAudio = {
  pulse() {
    tone(220, 70, 0.9, 1, 'sine');
    tone(880, 440, 0.25, 0.35, 'triangle');
  },
  complete() {
    tone(660, 990, 0.18, 0.4, 'sine');
  },
  ready() {
    tone(1320, 1320, 0.07, 0.25, 'sine');
  },
};
