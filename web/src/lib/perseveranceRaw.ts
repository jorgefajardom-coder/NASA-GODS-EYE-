/**
 * Mars Perseverance Raw Images (AGENTS.md section 10): the public NASA JSON feed behind
 * https://mars.nasa.gov/mars2020/multimedia/raw-images/ . The viewer reads it only when the person
 * asks, never at start-up, so the saved replay still works offline. The images are real and
 * unprocessed but come from wherever the rover is now: they are not the replay's site, not terrain
 * data and never reach the agents' map or the planner. Display only.
 */
export const RAW_FEED_URL = 'https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&ver=1.2';
export const RAW_GALLERY_URL = 'https://mars.nasa.gov/mars2020/multimedia/raw-images/';

export interface RawImage {
  id: string;
  sol: number;
  site: number | null;
  /** Drive counter within the site; with `site` it is the rover stop (RMC `<site>_<drive>`). */
  drive: number | null;
  instrument: string;
  /** Pointing in the rover frame (x forward, y right, z down), when the feed gives it. */
  vector: [number, number, number] | null;
  /** Mast azimuth (deg clockwise from the rover's front) and elevation (deg), when the feed gives them. */
  mastAzDeg: number | null;
  mastElDeg: number | null;
  takenUtc: string;
  credit: string;
  /** 320 px browse image. */
  thumbUrl: string;
  /** 800 px browse image. */
  mediumUrl: string;
  /** NASA gallery page of the image. */
  pageUrl: string;
}

export function rawFeedUrl(num: number, category = 'mars2020'): string {
  return `${RAW_FEED_URL.replace('category=mars2020', `category=${category}`)}&num=${num}&page=0&order=sol+desc`;
}

/** Raw images of one sol (the feed filters by sol range), oldest first so a stop's images keep their order. */
export function rawFeedUrlForSol(sol: number, num = 300, category = 'mars2020'): string {
  const mission = category === 'msl' ? 'msl' : 'M20';
  return `${RAW_FEED_URL.replace('category=mars2020', `category=${category}`)}&num=${num}&page=0&order=sol+asc&condition_1=${mission}:mission&condition_2=${sol}:sol:gte&condition_3=${sol}:sol:lte`;
}

/** Images taken at one rover stop: same site and drive. */
export function imagesAtStop(images: RawImage[], site: number, drive: number): RawImage[] {
  return images.filter((i) => i.site === site && i.drive === drive);
}

import { parseNumber, parseVector } from './photoAim';

const NASA_HOST = /^https:\/\/mars\.nasa\.gov\//;
const str = (v: unknown): string | null => (typeof v === 'string' && v ? v : null);
/** Curiosity's feed still lists some links over http; NASA serves the same files over https. */
const https = (v: unknown): string | null => str(v)?.replace(/^http:\/\/mars\.nasa\.gov\//, 'https://mars.nasa.gov/') ?? null;

/** Keeps only well-formed entries whose links stay on mars.nasa.gov over https. */
export function parseRawImages(json: unknown): RawImage[] {
  const list = (json as { images?: unknown } | null)?.images;
  if (!Array.isArray(list)) return [];
  const out: RawImage[] = [];
  for (const raw of list as Array<Record<string, unknown> | null>) {
    if (!raw) continue;
    const files = (raw.image_files ?? {}) as Record<string, unknown>;
    const thumb = https(files.small);
    const medium = https(files.medium) ?? thumb;
    const page = https(raw.link);
    const id = str(raw.imageid);
    const sol = typeof raw.sol === 'number' ? raw.sol : null;
    if (!thumb || !medium || !page || !id || sol == null) continue;
    if (![thumb, medium, page].every((u) => NASA_HOST.test(u))) continue;
    const cam = (raw.camera ?? {}) as Record<string, unknown>;
    out.push({
      id,
      sol,
      site: typeof raw.site === 'number' ? raw.site : null,
      drive: raw.drive != null && raw.drive !== '' && Number.isFinite(Number(raw.drive)) ? Number(raw.drive) : null,
      instrument: str(cam.instrument) ?? 'UNKNOWN',
      vector: parseVector(cam.camera_vector),
      mastAzDeg: parseNumber((raw.extended as Record<string, unknown> | undefined)?.mastAz),
      mastElDeg: parseNumber((raw.extended as Record<string, unknown> | undefined)?.mastEl),
      takenUtc: str(raw.date_taken_utc) ?? '',
      credit: str(raw.credit) ?? 'NASA/JPL-Caltech',
      thumbUrl: thumb,
      mediumUrl: medium,
      pageUrl: page,
    });
  }
  return out;
}

/** Ground-view cameras first; SuperCam micro-images are close-ups of a single rock. */
const isGroundView = (i: RawImage) => /NAV|HAZ|MCZ|MAST/i.test(i.instrument);

/** The newest `n` images, ground-view cameras first, feed order kept inside each group. */
export function pickRawImages(images: RawImage[], n: number): RawImage[] {
  return [...images.filter(isGroundView), ...images.filter((i) => !isGroundView(i))].slice(0, n);
}
