/**
 * Zones the viewer can open: each is a place on Mars with its own real NASA terrain and, where one exists, a
 * real rover or lander mission, and each has a scene. The story
 * played on every scene (drone survey, scarp, replan, rover photo tour) is simulated; only the terrain,
 * the imagery and the rover stops are NASA data.
 *
 * Every card image is real orbital imagery of that zone, north up: the same orthomosaic that is draped on
 * its terrain, so the card and the 3D map line up for the transition.
 */
export type ZoneStatus = 'scene';

export interface WorldInfo {
  id: string;
  body: 'Mars';
  place: string;
  mission: string;
  /** Replay folder under `replay/`, or null for a zone without a scene. */
  runId: string | null;
  status: ZoneStatus;
  /** What the scene is made of, or why there is none. */
  note: string;
  /** NASA data the zone is made of, and what it does not have (e.g. no rover stops). */
  data: string;
  missing: string | null;
  /** Card image (asset path under public/), north up, or null. */
  image: string | null;
  /** What the card image is, for its caption and alt text. */
  imageCaption: string | null;
  /** Source page of the zone's data. */
  url: string;
  /** Centre of the zone's scene crop (degrees, planetocentric, east positive): where its point sits on the globe. */
  lat: number;
  lon: number;
  /** Two-sentence synopsis shown on the zone card. */
  synopsis: string;
}

export const WORLDS: ReadonlyArray<WorldInfo> = [
  {
    id: 'jezero',
    body: 'Mars',
    place: 'Jezero crater',
    mission: 'Perseverance',
    runId: 'demo',
    status: 'scene',
    note: 'MRO CTX terrain at the landing area and north of it, with the real Perseverance stops (sol 13 to 708).',
    data: 'CTX DTM 20 m and CTX orthomosaic 6 m (Mars 2020 TRN), SIM 3464 geology, MMGIS M20 waypoints.',
    missing: null,
    image: 'replay/demo/ctx_ortho.png',
    imageCaption: 'MRO CTX Jezero orthomosaic over the scene crop, the image draped on its terrain',
    url: 'https://trek.nasa.gov/mars/',
    lat: 18.4899,
    lon: 77.43461,
    synopsis: 'An ancient lake crater with a river delta. Perseverance has explored it since 2021 and sealed the first samples meant for return to Earth.',
  },
  {
    id: 'gale',
    body: 'Mars',
    place: 'Gale crater',
    mission: 'Curiosity',
    runId: 'gale-demo',
    status: 'scene',
    note: 'NASA/USGS MSL Gale DEM mosaic over the foot of Mount Sharp, with the real Curiosity stops (thinned to 80 m apart).',
    data: 'MSL Gale DEM mosaic (8 m overview), MRO CTX Gale mosaic, MMGIS MSL waypoints.',
    missing: null,
    image: 'replay/gale-demo/ctx_ortho.png',
    imageCaption: 'MRO CTX Gale mosaic over the scene crop, the image draped on its terrain',
    url: 'https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/',
    lat: -4.7253,
    lon: 137.3865,
    synopsis: 'A 154 km crater around Mount Sharp. Curiosity has climbed its layered rocks since 2012, reading the record of long-lived ancient lakes.',
  },
  {
    id: 'gusev',
    body: 'Mars',
    place: 'Gusev crater',
    mission: 'Spirit',
    runId: 'gusev-demo',
    status: 'scene',
    note: "Columbia Hills DEM over Spirit's traverse from the landing site to the Columbia Hills, with the real Spirit stops (sol 1 to 1866, thinned to 40 m apart).",
    data: 'Columbia Hills HiRISE/CTX/HRSC DEM mosaic (1 m, averaged to 8 m) and visible mosaic, PDS Geosciences Node corrected Spirit traverse.',
    missing: "NASA's raw-image feed has no Spirit images (archived in the PDS): the tour shows none.",
    image: 'replay/gusev-demo/ctx_ortho.png',
    imageCaption: 'Columbia Hills visible mosaic (HiRISE/CTX/HRSC) over the scene crop, the image draped on its terrain',
    url: 'https://trek.nasa.gov/mars/',
    lat: -14.5819,
    lon: 175.502,
    synopsis: 'A crater once thought to hold a lake. Spirit drove from its landing site to the Columbia Hills and Home Plate between 2004 and 2010.',
  },
  {
    id: 'elysium',
    body: 'Mars',
    place: 'Elysium Planitia',
    mission: 'InSight',
    runId: 'insight-demo',
    status: 'scene',
    note: 'InSight DEM mosaic centred on the lander (4.502 N, 135.623 E), a flat lava plain.',
    data: 'InSight HiRISE/CTX/HRSC DEM mosaic (20 m) and InSight CTX mosaic.',
    missing: 'InSight is a lander: no rover stops and no photo tour.',
    image: 'replay/insight-demo/ctx_ortho.png',
    imageCaption: 'MRO CTX InSight mosaic over the scene crop, the image draped on its terrain',
    url: 'https://trek.nasa.gov/mars/',
    lat: 4.502,
    lon: 135.623,
    synopsis: 'A smooth volcanic plain chosen as a safe, flat site for the InSight lander, which listened to marsquakes from 2018 to 2022.',
  },
  {
    id: 'meridiani',
    body: 'Mars',
    place: 'Meridiani Planum',
    mission: 'Opportunity',
    runId: 'meridiani-demo',
    status: 'scene',
    note: "HiRISE DEM of Endeavour crater's west rim, with the real Opportunity stops along it (sol 2630 to 4922, thinned to 80 m apart).",
    data: 'Endeavour crater HiRISE DEM (1 m, averaged to 8 m), South Meridiani CTX mosaic, PDS Geosciences Node corrected Opportunity traverse.',
    missing: "The traverse is tied to the published landing site by the frontend (tens of metres); NASA's raw-image feed has no Opportunity images.",
    image: 'replay/meridiani-demo/ctx_ortho.png',
    imageCaption: 'MRO CTX South Meridiani mosaic over the scene crop, the image draped on its terrain',
    url: 'https://trek.nasa.gov/mars/',
    lat: -2.2679,
    lon: -5.369,
    synopsis: 'Hematite-rich plains. Opportunity drove more than 45 km here from 2004 to 2018 and spent its last years on the rim of Endeavour crater.',
  },
  {
    id: 'melas',
    body: 'Mars',
    place: 'Valles Marineris',
    mission: 'No landed mission',
    runId: 'melas-demo',
    status: 'scene',
    note: 'CTX stereo DEM of a Melas Chasma floor and wall (1.5 km of relief), a place never visited by a rover.',
    data: 'MRO CTX stereo DEM 11S291E (24 m) and its paired CTX orthoimage.',
    missing: 'No rover or lander has been here: no stops and no photo tour.',
    image: 'replay/melas-demo/ctx_ortho.png',
    imageCaption: 'MRO CTX orthoimage B19_017187_1685 over the scene crop, the image draped on its terrain',
    url: 'https://trek.nasa.gov/mars/',
    lat: -12.8716,
    lon: -69.0574,
    synopsis: 'Melas Chasma, part of the largest canyon system in the Solar System. No spacecraft has ever landed here.',
  },
];

/** The zone a run belongs to, or null for a run outside the catalogue (e.g. a test package opened with ?run=). */
export function worldOfRun(runId: string): WorldInfo | null {
  return WORLDS.find((w) => w.runId === runId) ?? null;
}

/** Zone whose card the selector menu shows first (owner's choice), whatever run is open. The scene is not entered. */
export const DEFAULT_ZONE_ID = 'jezero';
export function defaultZoneIndex(): number {
  const i = WORLDS.findIndex((w) => w.id === DEFAULT_ZONE_ID);
  return i >= 0 ? i : Math.max(0, WORLDS.findIndex((w) => w.status === 'scene'));
}

/** Index of the zone shown first in the selector: the current run's, else the first scene. */
export function initialZoneIndex(runId: string): number {
  const i = WORLDS.findIndex((w) => w.runId === runId);
  return i >= 0 ? i : Math.max(0, WORLDS.findIndex((w) => w.status === 'scene'));
}

/** Index after a step left (-1) or right (+1), wrapping around. */
export function stepZone(i: number, dir: 1 | -1, n = WORLDS.length): number {
  return (i + dir + n) % n;
}

/** URL that opens a zone's scene (keeps other parameters such as ?lite). */
export function zoneUrl(href: string, runId: string): string {
  const url = new URL(href);
  url.searchParams.set('run', runId);
  return url.toString();
}
