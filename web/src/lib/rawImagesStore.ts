import { useSyncExternalStore } from 'react';
import { imagesAtStop, parseRawImages, pickRawImages, rawFeedUrl, rawFeedUrlForSol, type RawImage } from './perseveranceRaw';

export type RawImagesState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; images: RawImage[]; index: number; /** RMC of the rover stop the images were taken at, or null for the latest ones. */ forStop: string | null };

const SHOWN = 6;
const FETCH = 40;
const TIMEOUT_MS = 12000;

type FetchLike = (url: string, init?: { signal?: AbortSignal }) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;

/**
 * One shared, opt-in loader for the Perseverance raw images, used by the Atmos tab panel and by the
 * first-person "Mars now" window and compare view. Nothing is requested until `load()` is called.
 */
export function createRawImagesStore(fetchFn: FetchLike) {
  let state: RawImagesState = { status: 'idle' };
  let ctl: AbortController | null = null;
  /** Images already read for a sol (a tour passes many stops of the same sol): never fetched twice. */
  const solCache = new Map<number, RawImage[]>();
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
      if (ctl === mine) set({ status: 'ready', images, index: 0, forStop: forStop });
    } catch (e) {
      if (ctl !== mine) return;
      set({ status: 'error', message: mine.signal.aborted ? 'The NASA feed did not answer in time' : e instanceof Error ? e.message : 'Could not read the NASA feed' });
    } finally {
      clearTimeout(timer);
    }
  }

  /** The newest images from wherever the rover is now. */
  const load = (): Promise<void> => run(rawFeedUrl(FETCH), (all) => pickRawImages(all, SHOWN), null, 'The feed returned no usable images');

  /** The images NASA lists for one rover stop (same sol, site and drive); none is an honest result. */
  const loadStop = (stop: { sol: number; site: number; drive: number; rmc: string }): Promise<void> =>
    run(
      rawFeedUrlForSol(stop.sol),
      (all) => {
        const sol = solCache.get(stop.sol) ?? all;
        solCache.set(stop.sol, sol);
        return pickRawImages(imagesAtStop(sol, stop.site, stop.drive), SHOWN);
      },
      stop.rmc,
      `NASA lists no raw image for stop ${stop.rmc}`,
      () => solCache.get(stop.sol) ?? null,
    );

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
    step,
  };
}

export const rawImages = createRawImagesStore((url, init) => fetch(url, init));

export function useRawImages(): RawImagesState {
  return useSyncExternalStore(rawImages.subscribe, rawImages.getState);
}
