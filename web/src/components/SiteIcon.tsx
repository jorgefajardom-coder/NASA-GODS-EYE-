import { siteKind } from '../lib/siteKinds';

/** Icon of a site kind (same drawing on every interface). Decorative: the text next to it names the site. */
export function SiteIcon({ kind, size = 16, color }: { kind: string; size?: number; color?: string }) {
  const info = siteKind(kind);
  return (
    <svg className="site-icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color ?? info.color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={info.path} />
    </svg>
  );
}
