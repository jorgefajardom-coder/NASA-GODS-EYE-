/**
 * Rendering tier of the viewer, chosen once at start-up from what the browser can do.
 *
 * - `full`: hardware WebGL; every display effect on.
 * - `lite`: WebGL works but through a software rasteriser or a GPU the browser flags as slow;
 *   the 3D view stays, with pixel ratio 1, no antialiasing, no surface detail and no surroundings.
 * - `map2d`: no WebGL at all (or the 3D view failed to start); a 2D top-down map of the same replay
 *   replaces the 3D view. Every panel, the timeline and the data are unchanged.
 *
 * `?render=full|lite|2d` in the URL forces a tier (for testing and for slow machines).
 */
export type RenderTier = 'full' | 'lite' | 'map2d';

/** Renderer strings of software rasterisers (no GPU acceleration). */
const SOFTWARE_RENDERERS = /swiftshader|llvmpipe|softpipe|software|basic render|microsoft basic|mesa offscreen|warp/i;

export interface GpuProbe {
  /** A WebGL (1 or 2) context could be created at all. */
  webgl: boolean;
  /** The browser refused a context with failIfMajorPerformanceCaveat (it would be slow). */
  majorCaveat: boolean;
  /** Unmasked renderer string when the browser exposes it, else ''. */
  renderer: string;
}

/** Tier for a probe result and an optional URL override (pure; tested). */
export function chooseTier(probe: GpuProbe, override: string | null): RenderTier {
  if (override === '2d' || override === 'map2d') return 'map2d';
  if (!probe.webgl) return 'map2d';
  if (override === 'lite') return 'lite';
  if (override === 'full') return 'full';
  if (probe.majorCaveat || SOFTWARE_RENDERERS.test(probe.renderer)) return 'lite';
  return 'full';
}

function release(gl: WebGLRenderingContext | WebGL2RenderingContext | null) {
  gl?.getExtension('WEBGL_lose_context')?.loseContext();
}

/** Probes WebGL with throwaway canvases (released at once so they do not count against the context limit). */
export function probeGpu(): GpuProbe {
  const probe: GpuProbe = { webgl: false, majorCaveat: false, renderer: '' };
  if (typeof document === 'undefined') return probe;
  try {
    const c = document.createElement('canvas');
    const gl = (c.getContext('webgl2') ?? c.getContext('webgl')) as WebGL2RenderingContext | WebGLRenderingContext | null;
    if (!gl) return probe;
    probe.webgl = true;
    const info = gl.getExtension('WEBGL_debug_renderer_info');
    probe.renderer = String(gl.getParameter(info ? info.UNMASKED_RENDERER_WEBGL : gl.RENDERER) ?? '');
    release(gl);
    const strict = document.createElement('canvas').getContext('webgl2', { failIfMajorPerformanceCaveat: true }) as WebGL2RenderingContext | null;
    probe.majorCaveat = !strict;
    release(strict);
  } catch {
    // A browser that throws while probing is treated as having no usable WebGL.
    probe.webgl = false;
  }
  return probe;
}

/** Tier for this browser and page URL. */
export function detectRenderTier(): RenderTier {
  const override = typeof window === 'undefined' ? null : new URLSearchParams(window.location.search).get('render');
  return chooseTier(probeGpu(), override);
}
