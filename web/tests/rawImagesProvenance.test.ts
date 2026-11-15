// @vitest-environment jsdom
// Synthetic feed fixtures exercise UI provenance; these are not NASA observations.
import { act, createElement, Fragment } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RawImagesPanel } from '../src/components/RawImagesPanel';
import { MarsNowFrame } from '../src/components/MarsNow';
import { rawImages } from '../src/lib/rawImagesStore';

const stop = { sol: 13, site: 3, drive: 110, rmc: '3_110', lat_deg: 0, lon_deg: 0, x_m: 0, y_m: 0, z_m: 0 };
const curiosity = { id: 'msl', name: 'Curiosity', raw_category: 'msl', image_match: 'sol' as const };

describe('shared raw-image acquisition provenance', () => {
  let container: HTMLDivElement;
  let root: Root;
  let requested: string[];

  beforeEach(() => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
    // Image transfer is outside these DOM checks; no remote image is requested.
    vi.stubGlobal('Image', undefined);
    requested = [];
    vi.stubGlobal('fetch', async (url: string) => {
      requested.push(url);
      const msl = url.includes('category=msl');
      const name = msl ? 'msl-fixture' : 'm20-fixture';
      const sol = Number(/condition_2=(\d+):sol:gte/.exec(url)?.[1] ?? (msl ? 751 : 13));
      return {
        ok: true, status: 200,
        json: async () => ({ images: [{
          imageid: name, sol, site: msl ? '' : 3, drive: msl ? '' : '110',
          camera: { instrument: msl ? 'MAST_LEFT' : 'NAVCAM_LEFT' },
          image_files: { small: `https://mars.nasa.gov/${name}.jpg`, medium: `https://mars.nasa.gov/${name}.jpg` },
          link: `https://mars.nasa.gov/${name}`, credit: 'Synthetic test fixture',
        }] }),
      };
    });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  it('requires an explicit latest-Perseverance load after a Curiosity stop tour', async () => {
    await rawImages.loadStop({ ...stop, sol: 751 }, curiosity);
    await act(async () => root.render(createElement(RawImagesPanel)));
    expect(container.querySelector('img')).toBeNull();
    const load = container.querySelector<HTMLButtonElement>('.rawimg__load')!;
    expect(load.textContent).toBe('Load the latest images');
    expect(load.disabled).toBe(false);
    await act(async () => { load.click(); });
    expect(requested.at(-1)).toContain('category=mars2020');
    expect(container.querySelector('img')?.getAttribute('src')).toContain('m20-fixture');
    expect(container.querySelector('img')?.getAttribute('alt')).toContain('Perseverance');
    expect(rawImages.getState()).toMatchObject({ status: 'ready', query: { category: 'mars2020', kind: 'latest' }, forStop: null });
  });

  it('does not relabel historical Perseverance stop images as the latest images', async () => {
    await rawImages.loadStop(stop);
    await act(async () => root.render(createElement(RawImagesPanel)));
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('.rawimg__load')?.textContent).toBe('Load the latest images');
  });

  it('shows latest Curiosity images only in the matching mission window', async () => {
    await rawImages.load(curiosity);
    await act(async () => root.render(createElement(Fragment, null,
      createElement(RawImagesPanel),
      createElement(MarsNowFrame, { stop: null, mission: curiosity, onClose: () => undefined }),
    )));
    expect(container.querySelector('.rawimg img')).toBeNull();
    expect(container.querySelector('.marsnow img')?.getAttribute('alt')).toContain('Curiosity');
    expect(container.querySelector('.marsnow img')?.getAttribute('src')).toContain('msl-fixture');
  });

  it('does not reuse a result with the same stop ID for a different sol or mission', async () => {
    await rawImages.loadStop(stop);
    await act(async () => root.render(createElement(MarsNowFrame, { stop: { ...stop, sol: 14 }, onClose: () => undefined })));
    expect(container.querySelector('img')).toBeNull();
    await act(async () => root.render(createElement(MarsNowFrame, { stop, mission: curiosity, onClose: () => undefined })));
    expect(container.querySelector('img')).toBeNull();
  });

  it('reloads a tour when the sol changes even if the stop identifier is unchanged', async () => {
    const tour = { index: 0, total: 2, onPrev: () => undefined, onNext: () => undefined, onStop: () => undefined };
    await act(async () => root.render(createElement(MarsNowFrame, { stop, tour, onClose: () => undefined })));
    await act(async () => root.render(createElement(MarsNowFrame, { stop: { ...stop, sol: 14 }, tour, onClose: () => undefined })));
    expect(requested.at(-1)).toContain('condition_2=14:sol:gte');
    expect(container.querySelector('img')?.getAttribute('alt')).toContain('sol 14');
  });
});
