import { describe, expect, it } from 'vitest';
import { photoTourTitle } from '../src/lib/roverStops';

describe('photo tour button text', () => {
  it("names each zone's own rover", () => {
    expect(photoTourTitle({ id: 'mars2020', name: 'Perseverance', raw_category: 'mars2020', image_match: 'stop' })).toMatch(/every real Perseverance stop.*NASA's images/);
    expect(photoTourTitle({ id: 'msl', name: 'Curiosity', raw_category: 'msl', image_match: 'sol' })).toMatch(/every real Curiosity stop/);
  });

  it('promises no photos where the raw-image feed has none (Spirit, Opportunity)', () => {
    const t = photoTourTitle({ id: 'mer1', name: 'Opportunity', raw_category: '', image_match: 'none' });
    expect(t).toMatch(/every real Opportunity stop/);
    expect(t).toMatch(/no photos are shown/);
    expect(t).not.toMatch(/Perseverance/);
  });
});
