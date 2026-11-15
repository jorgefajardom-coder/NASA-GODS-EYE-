/**
 * Kinds of site shown on every interface (3D markers, first-person compass, dial minimap, flat map,
 * sites list), with one icon and colour each so a site reads the same everywhere. Display only.
 * Icons are single SVG paths on a 24 x 24 grid, drawn as strokes; the canvas views reuse them
 * through Path2D.
 */
export type SiteKind = 'base' | 'primary_goal' | 'poi' | 'science' | 'landmark' | 'landing' | 'photo' | 'depot' | 'habitat';

export interface SiteKindInfo {
  /** Short label in the compass and lists. */
  short: string;
  /** What the kind means, for tooltips. */
  title: string;
  color: string;
  /** SVG path data, 24 x 24 grid, stroke only. */
  path: string;
}

export const SITE_KINDS: Record<SiteKind, SiteKindInfo> = {
  base: { short: 'BASE', title: 'Base', color: '#65CBE8', path: 'M4 11 12 4l8 7v9H4z M10 20v-5h4v5' },
  primary_goal: { short: 'GOAL', title: 'Primary goal', color: '#F0A050', path: 'M6 21V4 M6 4h11l-2.5 4 2.5 4H6' },
  poi: { short: 'POI', title: 'Point of interest', color: '#C9D7DD', path: 'M12 21s-6-5.5-6-10a6 6 0 0 1 12 0c0 4.5-6 10-6 10z M12 9a2 2 0 1 0 0 4 2 2 0 1 0 0-4' },
  science: { short: 'SCI', title: 'Science target', color: '#9FE3A8', path: 'M9 3h6 M10 3v6l-5 10a1.5 1.5 0 0 0 1.4 2h11.2A1.5 1.5 0 0 0 19 19l-5-10V3 M7.5 15h9' },
  landmark: { short: 'LAND', title: 'Named landform', color: '#D8AD66', path: 'M3 20 9 9l4 6 3-4 5 9z' },
  photo: { short: 'IMG', title: 'Real Perseverance stop with mission images', color: '#F0A050', path: 'M3 8h4l2-3h6l2 3h4v11H3z M12 10a3.5 3.5 0 1 0 0 7 3.5 3.5 0 1 0 0-7' },
  depot: { short: 'DEPOT', title: 'Sample depot (sealed tubes left for retrieval)', color: '#E6D27A', path: 'M8 3h8 M9 3v14a3 3 0 0 0 6 0V3 M9 9h6 M4 21h16' },
  habitat: { short: 'HAB', title: 'Habitat or landing-pad area (flat ground)', color: '#8FC7E8', path: 'M3 19h18 M5 19v-6a7 7 0 0 1 14 0v6 M10 19v-4h4v4' },
  landing: { short: 'SITE', title: 'Mission site', color: '#E8F4FF', path: 'M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16 M12 9a3 3 0 1 0 0 6 3 3 0 1 0 0-6 M12 1v4 M12 19v4 M1 12h4 M19 12h4' },
};

const KINDS = Object.keys(SITE_KINDS) as SiteKind[];

/** Unknown kinds from older packages fall back to a plain point of interest. */
export function siteKind(kind: string): SiteKindInfo {
  return (KINDS as string[]).includes(kind) ? SITE_KINDS[kind as SiteKind] : SITE_KINDS.poi;
}

/** Colour with a task outcome applied: rejected red, done cyan, otherwise the kind's own colour. */
export function siteColor(kind: string, taskState?: string): string {
  if (taskState === 'REJECTED') return '#D95045';
  if (taskState === 'DONE') return '#65CBE8';
  return siteKind(kind).color;
}

/**
 * Draws a site badge centred on (x, y), `size` px across, on a 2D canvas: the same dark disc, coloured
 * ring and line icon as the SVG `SiteIcon`, so a site reads the same on every view.
 */
export function drawSiteIcon(g: CanvasRenderingContext2D, kind: string, x: number, y: number, size: number, color: string): void {
  g.save();
  g.translate(x - size / 2, y - size / 2);
  g.scale(size / 32, size / 32); // the badge is drawn on a 32 x 32 grid
  g.beginPath();
  g.arc(16, 16, 14.2, 0, Math.PI * 2);
  g.fillStyle = 'rgba(9,13,17,0.9)';
  g.fill();
  g.strokeStyle = color;
  g.lineWidth = 2;
  g.stroke();
  g.translate(7.6, 7.6);
  g.scale(0.7, 0.7);
  g.lineWidth = 2.4;
  g.lineJoin = 'round';
  g.lineCap = 'round';
  g.stroke(new Path2D(siteKind(kind).path));
  g.restore();
}
