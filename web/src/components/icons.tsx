import type { ReactNode } from 'react';
import type { Glyph } from '../lib/management';

/** Monochrome line icons drawn for this project (no third-party artwork). */
const PATHS: Record<Glyph, ReactNode> = {
  human: (
    <>
      <circle cx="32" cy="22" r="10" />
      <rect x="25" y="19" width="14" height="7" />
      <path d="M10 58c0-12 10-20 22-20s22 8 22 20" />
    </>
  ),
  drone: (
    <>
      <rect x="26" y="26" width="12" height="12" />
      <path d="M26 26 14 14M38 26l12-12M26 38 14 50M38 38l12 12" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="52" cy="12" r="6" />
      <circle cx="12" cy="52" r="6" />
      <circle cx="52" cy="52" r="6" />
    </>
  ),
  rover: (
    <>
      <rect x="12" y="26" width="40" height="14" />
      <circle cx="20" cy="47" r="5" />
      <circle cx="32" cy="47" r="5" />
      <circle cx="44" cy="47" r="5" />
      <path d="M38 26v-9h9" />
    </>
  ),
  task: (
    <>
      <path d="M32 8 56 32 32 56 8 32Z" />
      <path d="M32 24v10M32 40v2" />
    </>
  ),
  route: (
    <>
      <path d="M12 52 26 30l14 10 14-26" />
      <circle cx="12" cy="52" r="4" />
      <circle cx="54" cy="14" r="4" />
    </>
  ),
};

export function GlyphIcon({ glyph, size = 18 }: { glyph: Glyph; size?: number }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={size <= 24 ? 5 : 2.5}
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden
      focusable="false"
    >
      {PATHS[glyph]}
    </svg>
  );
}

export function PlayIcon({ playing }: { playing: boolean }) {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden focusable="false">
      {playing ? (
        <>
          <rect x="3" y="2" width="3.5" height="12" />
          <rect x="9.5" y="2" width="3.5" height="12" />
        </>
      ) : (
        <path d="M3 2 14 8 3 14Z" />
      )}
    </svg>
  );
}

export function RestartIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden focusable="false">
      <path d="M3 8a5 5 0 1 0 2-4" />
      <path d="M2 2v4h4" />
    </svg>
  );
}
