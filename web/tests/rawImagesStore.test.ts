import { describe, expect, it } from 'vitest';
import { createRawImagesStore } from '../src/lib/rawImagesStore';

const img = (n: number) => ({
  imageid: `NLF_${n}`,
  sol: 2000 + n,
  link: `https://mars.nasa.gov/p/${n}`,
  camera: { instrument: 'NAVCAM_LEFT' },
  image_files: { small: `https://mars.nasa.gov/s${n}.jpg`, medium: `https://mars.nasa.gov/m${n}.jpg` },
});
const ok = (images: unknown[]) => async () => ({ ok: true, status: 200, json: async () => ({ images }) });

describe('raw images store', () => {
  it('requests nothing until load() is called', () => {
    let calls = 0;
    const s = createRawImagesStore(async () => {
      calls++;
      return { ok: true, status: 200, json: async () => ({ images: [] }) };
    });
    expect(s.getState().status).toBe('idle');
    expect(calls).toBe(0);
  });

  it('loads, notifies subscribers and starts on the first image', async () => {
    const s = createRawImagesStore(ok([img(1), img(2), img(3)]));
    let notified = 0;
    s.subscribe(() => notified++);
    await s.load();
    const st = s.getState();
    expect(st.status).toBe('ready');
    if (st.status === 'ready') expect(st.index).toBe(0);
    expect(notified).toBeGreaterThanOrEqual(2); // loading, then ready
  });

  it('steps through the images and wraps around', async () => {
    const s = createRawImagesStore(ok([img(1), img(2), img(3)]));
    await s.load();
    s.step(-1);
    expect((s.getState() as { index: number }).index).toBe(2);
    s.step(1);
    expect((s.getState() as { index: number }).index).toBe(0);
  });

  it('reports an error for a bad answer, an empty feed or a network failure', async () => {
    const bad = createRawImagesStore(async () => ({ ok: false, status: 503, json: async () => ({}) }));
    await bad.load();
    expect(bad.getState()).toMatchObject({ status: 'error' });
    const empty = createRawImagesStore(ok([]));
    await empty.load();
    expect(empty.getState()).toMatchObject({ status: 'error' });
    const down = createRawImagesStore(async () => {
      throw new Error('offline');
    });
    await down.load();
    expect(down.getState()).toMatchObject({ status: 'error', message: 'offline' });
  });
});

describe('raw images of a rover stop', () => {
  const at = (id: string, site: number, drive: string) => ({ ...img(1), imageid: id, site, drive });
  const stop = { sol: 13, site: 3, drive: 110, rmc: '3_110' };

  it('keeps only that stop and remembers which one it was', async () => {
    const s = createRawImagesStore(ok([at('a', 3, '0'), at('b', 3, '110'), at('c', 3, '110')]));
    await s.loadStop(stop);
    const st = s.getState();
    expect(st.status).toBe('ready');
    if (st.status === 'ready') {
      expect(st.images.map((i) => i.id)).toEqual(['b', 'c']);
      expect(st.forStop).toBe('3_110');
    }
  });

  it('says so when NASA lists no image for the stop', async () => {
    const s = createRawImagesStore(ok([at('a', 3, '0')]));
    await s.loadStop(stop);
    expect(s.getState()).toMatchObject({ status: 'error', message: 'NASA lists no raw image for stop 3_110' });
  });
});
