import { useSyncExternalStore } from 'react';
import { imagesAtStop, parseRawImages, pickRawImages, rawFeedUrl, rawFeedUrlForSol, type RawImage } from './perseveranceRaw';

export type RawImagesState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | {
      status: 'ready';
      images: RawImage[];
      index: number;
      /** RMC of the rover stop the images were taken at, or null for the latest ones. */
      forStop: string | null;
      /** True once every image has finished loading (or failed) in the browser: the tour waits for it. */
      preloaded: boolean;
    };

/** How a mission's raw images are matched to a stop (see RoverMission). */
export interface StopMission {
  raw_category: string;
  image_match: 'stop' | 'sol' | 'none';
}
const DEFAULT_MISSION: StopMission = { raw_category: 'mars2020', image_match: 'stop' };

const SHOWN = 9;
const PRELOAD_TIMEOUT_MS = 15000;
const FETCH = 40;
const TIMEOUT_MS = 12000;

/** Loads every URL in the browser cache; resolves when all have finished, failed or the time is up. No browser, nothing to wait for. */
export function preloadImages(urls: string[]): Promise<void> {
  if (typeof Image === 'undefined' || urls.length === 0) return Promise.resolve();
  const loads = urls.map(
    (u) =>
      new Promise<void>((res) => {
        const im = new Image();
        im.onload = () => res();
        im.onerror = () => res();
        im.referrerPolicy = 'no-referrer';
        im.src = u;
      }),
  );
  return Promise.race([Promise.all(loads).then(() => undefined), new Promise<void>((res) => setTimeout(res, PRELOAD_TIMEOUT_MS))]);
}

type FetchLike = (url: string, init?: { signal?: AbortSignal }) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;

/**
 * One shared, opt-in loader for the Perseverance raw images, used by the Atmos tab panel and by the
 * first-person "Mars now" window and compare view. Nothing is requested until `load()` is called.
 */
export function createRawImagesStore(fetchFn: FetchLike, preload: (urls: string[]) => Promise<void> = preloadImages) {
  let state: RawImagesState = { status: 'idle' };
  let ctl: AbortController | null = null;
  /** Images already read for a sol (a tour passes many stops of the same sol): never fetched twice. */
  const solCache = new Map<string, RawImage[]>();
  const listeners = new Set<() => void>();
  const set = (s: RawImagesState) => {
    state = s;
    listeners.forEach((l) => l());
  };

  async function run(url: string, pick: (all: RawImage[]) => RawImage[], forStop: string | null, emptyMessage: string, cached?: () => RawImage[] | null): Promise<void> {
    ctl?.abort();
    const mine = new AbortController();
    ctl = mine;
    const timer = setTimeout(() => mine.abort(), TIMEOUT_MS);
    set({ status: 'loading' });
    try {
      const hit = cached?.() ?? null;
      let images: RawImage[];
      if (hit) images = pick(hit);
      else {
        const res = await fetchFn(url, { signal: mine.signal });
        if (!res.ok) throw new Error(`NASA feed answered ${res.status}`);
        images = pick(parseRawImages(await res.json()));
      }
      if (images.length === 0) throw new Error(emptyMessage);
      if (ctl === mine) {
        set({ status: 'ready', images, index: 0, forStop: forStop, preloaded: false });
        void preload(images.flatMap((i) => [i.thumbUrl, i.mediumUrl])).then(() => {
          if (state.status === 'ready' && state.images === images) set({ ...state, preloaded: true });
        });
      }
    } catch (e) {
      if (ctl !== mine) return;
      set({ status: 'error', message: mine.signal.aborted ? 'The NASA feed did not answer in time' : e instanceof Error ? e.message : 'Could not read the NASA feed' });
    } finally {
      clearTimeout(timer);
    }
  }

  /** The newest images from wherever the rover is now. */
  const load = (mission: StopMission = DEFAULT_MISSION): Promise<void> => run(rawFeedUrl(FETCH, mission.raw_category), (all) => pickRawImages(all, SHOWN), null, 'The feed returned no usable images');

  /** The images NASA lists for one rover stop (same sol, site and drive); none is an honest result. */
  const loadStop = (stop: { sol: number; site: number; drive: number; rmc: string }, mission: StopMission = DEFAULT_MISSION): Promise<void> => {
    if (mission.image_match === 'none') {
      // The mission's images are not in the feed: an honest, immediate answer (the tour moves on).
      ctl?.abort();
      set({ status: 'error', message: "No image feed: NASA's raw-image feed has no images of this mission (Spirit and Opportunity images are archived in the PDS)" });
      return Promise.resolve();
    }
    const key = `${mission.raw_category}:${stop.sol}`;
    const bySol = mission.image_match === 'sol'; // the feed does not label images with site and drive (Curiosity)
    return run(
      rawFeedUrlForSol(stop.sol, 300, mission.raw_category),
      (all) => {
        const sol = solCache.get(key) ?? all;
        solCache.set(key, sol);
        return pickRawImages(bySol ? sol : imagesAtStop(sol, stop.site, stop.drive), SHOWN);
      },
      stop.rmc,
      bySol ? `NASA lists no raw image for sol ${stop.sol}` : `NASA lists no raw image for stop ${stop.rmc}`,
      () => solCache.get(key) ?? null,
    );
  };

  /** Selects an image by its position (the tour shows them one after another). */
  function select(i: number): void {
    if (state.status !== 'ready' || i < 0 || i >= state.images.length) return;
    set({ ...state, index: i });
  }

  /** Moves the selected image by `step`, wrapping around. */
  function step(by: number): void {
    if (state.status !== 'ready') return;
    const n = state.images.length;
    set({ ...state, index: (((state.index + by) % n) + n) % n });
  }

  return {
    getState: () => state,
    subscribe: (l: () => void) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    load,
    loadStop,
    select,
    step,
  };
}

export const rawImages = createRawImagesStore((url, init) => fetch(url, init));

export function useRawImages(): RawImagesState {
  return useSyncExternalStore(rawImages.subscribe, rawImages.getState);
}
