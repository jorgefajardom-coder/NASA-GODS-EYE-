import { useEffect, useRef, useState } from 'react';
import { assetUrl } from '../data/replayAdapter';

/** Intro clip: AI-generated with Kling (declared in docs/AI_USAGE.md); always shown with a visible "AI-generated" mark. */
export const INTRO_URL = assetUrl('assets/intro/mars-gods-eye-intro.webm');
/** Fade-out of the intro screen (ms). */
const FADE_MS = 700;

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

/** Whether the intro should play: not with reduced motion, not with ?nointro=1. */
export function introWanted(): boolean {
  if (prefersReducedMotion()) return false;
  try {
    return new URLSearchParams(window.location.search).get('nointro') !== '1';
  } catch {
    return true;
  }
}

/**
 * Opening screen: plays the project intro clip once, muted (browsers block autoplay with sound),
 * then fades out. Skip button, click or Escape/Enter/Space skip it. If the clip cannot load or play,
 * the screen closes at once so the viewer is never blocked. The clip is AI-generated: an
 * "AI-generated" mark stays on screen the whole time it is visible.
 */
export function Intro({ onDone, onLeaving }: { onDone: () => void; onLeaving?: () => void }) {
  const [leaving, setLeaving] = useState(false);
  const done = useRef(false);
  const video = useRef<HTMLVideoElement>(null);

  const finish = () => {
    if (done.current) return;
    done.current = true;
    setLeaving(true);
    onLeaving?.(); // what follows the intro can appear under it while it fades
    window.setTimeout(onDone, FADE_MS);
  };

  useEffect(() => {
    const v = video.current;
    // Safety net: never hold the viewer longer than the clip plus a margin.
    const timer = window.setTimeout(finish, 9000);
    v?.play().catch(() => finish());
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        finish();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('keydown', onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={`intro${leaving ? ' intro--leaving' : ''}`} style={{ transitionDuration: `${FADE_MS}ms` }} onClick={finish} role="dialog" aria-label="Intro">
      <div className="intro__stage">
        <video ref={video} className="intro__video" src={INTRO_URL} muted playsInline preload="auto" onEnded={finish} onError={finish} aria-label="Mars Gods Eye intro (AI-generated video)" />
        {/* The required "AI-GENERATED · KLING" mark is burned into every frame (bottom-right), so it is the only one. */}
      </div>
      <button
        type="button"
        className="intro__skip"
        onClick={(e) => {
          e.stopPropagation();
          finish();
        }}
      >
        Skip ▸
      </button>
    </div>
  );
}
