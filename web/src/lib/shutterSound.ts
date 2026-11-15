/** A short mechanical click for the photo tour's shutter (synthesised, no asset). Silent when audio is unavailable. */
let ctx: AudioContext | null = null;

export function playShutter(): void {
  try {
    const AC = (window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext) as typeof AudioContext | undefined;
    if (!AC) return;
    ctx ??= new AC();
    if (ctx.state === 'suspended') void ctx.resume();
    const t0 = ctx.currentTime;
    const len = Math.floor(ctx.sampleRate * 0.07);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.exp(-i / (len * 0.12));
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const band = ctx.createBiquadFilter();
    band.type = 'bandpass';
    band.frequency.value = 2400;
    const gain = ctx.createGain();
    gain.gain.value = 0.22;
    src.connect(band).connect(gain).connect(ctx.destination);
    src.start(t0);
  } catch {
    /* sound is optional */
  }
}
