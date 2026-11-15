import { siteKind } from '../lib/siteKinds';

/**
 * Badge of a site kind: a dark disc with a coloured ring and the kind's line icon inside, the same
 * drawing on every interface (the canvas views draw it with `drawSiteIcon`). Decorative: the text
 * next to it names the site.
 */
export function SiteIcon({ kind, size = 16, color }: { kind: string; size?: number; color?: string }) {
  const info = siteKind(kind);
  const c = color ?? info.color;
  return (
    <svg className="site-icon" width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <circle cx="16" cy="16" r="14.2" fill="rgba(9,13,17,0.9)" stroke={c} strokeWidth="2" />
      <circle cx="16" cy="16" r="11.4" stroke={c} strokeOpacity="0.28" strokeWidth="1" />
      <g transform="translate(7.6 7.6) scale(0.7)" stroke={c} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <path d={info.path} />
      </g>
    </svg>
  );
}
