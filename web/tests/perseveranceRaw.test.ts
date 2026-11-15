import { describe, expect, it } from 'vitest';
import { parseRawImages, pickRawImages, rawFeedUrl } from '../src/lib/perseveranceRaw';

const entry = (over: Record<string, unknown> = {}) => ({
  imageid: 'NLF_0001',
  sol: 2031,
  site: 93,
  credit: 'NASA/JPL-Caltech',
  date_taken_utc: '2026-11-06T12:16:25.848',
  link: 'https://mars.nasa.gov/mars2020/multimedia/raw-images/NLF_0001',
  camera: { instrument: 'NAVCAM_LEFT' },
  image_files: { small: 'https://mars.nasa.gov/a_320.jpg', medium: 'https://mars.nasa.gov/a_800.jpg' },
  ...over,
});

describe('Perseverance raw images feed', () => {
  it('asks the public feed for the newest sols', () => {
    expect(rawFeedUrl(30)).toContain('category=mars2020');
    expect(rawFeedUrl(30)).toContain('num=30');
    expect(rawFeedUrl(30)).toContain('order=sol+desc');
  });

  it('parses a well-formed entry', () => {
    const [i] = parseRawImages({ images: [entry()] });
    expect(i).toMatchObject({ id: 'NLF_0001', sol: 2031, site: 93, instrument: 'NAVCAM_LEFT' });
  });

  it('drops entries that are malformed or leave mars.nasa.gov over https', () => {
    const bad = [
      entry({ image_files: { small: 'http://mars.nasa.gov/a.jpg' } }),
      entry({ image_files: { small: 'https://evil.example/a.jpg' } }),
      entry({ link: 'https://evil.example/page' }),
      entry({ sol: 'x' }),
      entry({ imageid: '' }),
      null,
    ];
    expect(parseRawImages({ images: bad })).toEqual([]);
    expect(parseRawImages(null)).toEqual([]);
    expect(parseRawImages({ images: 'nope' })).toEqual([]);
  });

  it('puts ground-view cameras before SuperCam close-ups', () => {
    const imgs = parseRawImages({
      images: [
        entry({ imageid: 'RMI', camera: { instrument: 'SUPERCAM_RMI' } }),
        entry({ imageid: 'NAV', camera: { instrument: 'NAVCAM_LEFT' } }),
        entry({ imageid: 'MCZ', camera: { instrument: 'MCZ_LEFT' } }),
      ],
    });
    expect(pickRawImages(imgs, 2).map((i) => i.id)).toEqual(['NAV', 'MCZ']);
    expect(pickRawImages(imgs, 3).map((i) => i.id)).toEqual(['NAV', 'MCZ', 'RMI']);
  });
});

import { imagesAtStop, rawFeedUrlForSol } from '../src/lib/perseveranceRaw';

describe('images of one rover stop', () => {
  it('asks the feed for a single sol', () => {
    const u = rawFeedUrlForSol(13);
    expect(u).toContain('condition_2=13:sol:gte');
    expect(u).toContain('condition_3=13:sol:lte');
  });

  it('keeps only the images taken at the same site and drive', () => {
    const e = (id: string, site: number, drive: string) => ({
      imageid: id, sol: 13, site, drive, link: 'https://mars.nasa.gov/p', camera: { instrument: 'NAVCAM_LEFT' },
      image_files: { small: 'https://mars.nasa.gov/s.jpg', medium: 'https://mars.nasa.gov/m.jpg' },
    });
    const imgs = parseRawImages({ images: [e('a', 3, '0'), e('b', 3, '110'), e('c', 4, '0')] });
    expect(imagesAtStop(imgs, 3, 0).map((i) => i.id)).toEqual(['a']);
    expect(imagesAtStop(imgs, 9, 9)).toEqual([]);
  });
});
