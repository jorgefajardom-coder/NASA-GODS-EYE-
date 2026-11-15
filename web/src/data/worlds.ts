/**
 * Worlds the viewer can open: each is a place with its own real NASA terrain and a real rover mission
 * whose stops are drawn on it. A world with a `runId` has a scene; the others are listed with the
 * reason they have none. The story played on every scene (drone survey, scarp, replan, rover photo
 * tour) is simulated; only the terrain, the imagery and the rover stops are NASA data.
 */
export interface WorldInfo {
  id: string;
  body: 'Mars' | 'Earth';
  place: string;
  mission: string;
  /** Replay folder under `replay/`, or null for a world without a scene. */
  runId: string | null;
  /** What the scene is made of, or why there is none. */
  note: string;
  /** Source page of the world's data. */
  url: string;
}

export const WORLDS: ReadonlyArray<WorldInfo> = [
  {
    id: 'jezero',
    body: 'Mars',
    place: 'Jezero crater',
    mission: 'Perseverance',
    runId: 'demo',
    note: 'MRO CTX terrain at the landing area and north of it, with the real Perseverance stops (sol 13 to 708).',
    url: 'https://trek.nasa.gov/mars/',
  },
  {
    id: 'gale',
    body: 'Mars',
    place: 'Gale crater',
    mission: 'Curiosity',
    runId: 'gale-demo',
    note: 'NASA/USGS MSL Gale DEM mosaic over the foot of Mount Sharp, with the real Curiosity stops (thinned to 80 m apart).',
    url: 'https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/',
  },
  {
    id: 'earth',
    body: 'Earth',
    place: 'Earth',
    mission: 'NASA Worldview',
    runId: null,
    note: 'No scene: Worldview offers satellite imagery of Earth, not terrain or rover stops. Opens in a new tab.',
    url: 'https://worldview.earthdata.nasa.gov/',
  },
];

/** The world a run belongs to, or null for a run outside the catalogue (e.g. a test package opened with ?run=). */
export function worldOfRun(runId: string): WorldInfo | null {
  return WORLDS.find((w) => w.runId === runId) ?? null;
}
