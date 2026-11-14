/**
 * Mandatory NASA reference resources (AGENTS.md §10), reviewed on 2026-11-14 for the
 * Jezero case. `status` says honestly whether the viewer uses the resource today.
 * Details and product identifiers: docs/data_sources.md.
 */
export interface ReferenceSource {
  name: string;
  url: string;
  /** What the resource offers for this project. */
  use: string;
  status: 'used' | 'candidate' | 'design reference' | 'not applicable';
}

export const REFERENCE_SOURCES: ReadonlyArray<ReferenceSource> = [
  {
    name: 'JPL Mars Trek',
    url: 'https://trek.nasa.gov/mars/',
    use: 'Controlled CTX orthomosaic of Jezero (6 m, same production as the CTX DTM) draped on the demo terrain. The HiRISE 25 cm orthomosaic stays evaluator only.',
    status: 'used',
  },
  {
    name: 'USGS-NASA Planetary Geologic Mapping Program',
    url: 'https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars',
    use: 'SIM 3464, geologic map of Jezero crater and Nili Planum (1:75,000, GIS) for a geology layer; SIM 3292 global map for context.',
    status: 'candidate',
  },
  {
    name: "Curiosity's Proposed Path up Mount Sharp",
    url: 'https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/',
    use: 'Route-map style: annotated science regions along a planned traverse on an orbital base map.',
    status: 'design reference',
  },
  {
    name: 'NASA Worldview',
    url: 'https://worldview.earthdata.nasa.gov/',
    use: 'Earth satellite imagery only; no Mars data.',
    status: 'not applicable',
  },
  {
    name: 'Mars Perseverance Raw Images',
    url: 'https://mars.nasa.gov/mars2020/multimedia/raw-images/',
    use: 'Ground-level Jezero images by sol, camera, site and drive (public JSON feed) to illustrate what the surface looks like at a waypoint.',
    status: 'candidate',
  },
];
