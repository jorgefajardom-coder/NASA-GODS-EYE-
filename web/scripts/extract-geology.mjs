#!/usr/bin/env node
/**
 * Geologic units of the demo crop from USGS SIM 3464 (Sun and Stack, 2020, Geologic map of
 * Jezero crater and the Nili Planum region, Mars, 1:75,000, https://doi.org/10.3133/sim3464),
 * read from the USGS ArcGIS feature service behind the map's interactive viewer
 * (data release https://doi.org/10.5066/P9CZYIO7). Only the polygons that intersect the crop
 * are requested; the 349 MB database is not downloaded.
 *
 * The service is in Mars Transverse Mercator (central meridian 77.5 E, Mars 2000 sphere,
 * R = 3396190 m, scale 1). Vertices are converted to latitude/longitude with the spherical
 * transverse Mercator inverse, then to the crop's local ENU frame with the same tangent
 * approximation as extract-ctx-crop.mjs.
 *
 * Registration caveat from the map's readme: SIM 3464 was drawn on a semi-controlled CTX
 * mosaic and has offsets of about 100-200 m against the controlled Mars 2020 CTX products
 * used for the terrain. No re-registration is applied; the viewer labels unit boundaries as
 * approximate.
 *
 * Usage: node scripts/extract-geology.mjs [out.json]
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SERVICE = 'https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/Jezero_FeatureServiceFromPro/FeatureServer/8';
const R = 3396190;
const LON0 = (77.5 * Math.PI) / 180;
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = process.argv[2] ?? join(HERE, '..', 'public', 'replay', 'demo', 'geology.json');

const crop = JSON.parse(readFileSync(join(HERE, 'data', 'ctx_crop.json'), 'utf8')).crop;
const lat0 = (crop.centre_lat_deg * Math.PI) / 180;
const lon0 = (crop.centre_lon_deg * Math.PI) / 180;
const W = crop.cols * crop.resolution_m;
const H = crop.rows * crop.resolution_m;

/** Spherical transverse Mercator, k0 = 1, latitude of origin 0. */
function tmForward(lat, lon) {
  const b = Math.cos(lat) * Math.sin(lon - LON0);
  return { x: (R / 2) * Math.log((1 + b) / (1 - b)), y: R * Math.atan2(Math.tan(lat), Math.cos(lon - LON0)) };
}
function tmInverse(x, y) {
  const d = y / R;
  return { lat: Math.asin(Math.sin(d) / Math.cosh(x / R)), lon: LON0 + Math.atan2(Math.sinh(x / R), Math.cos(d)) };
}
const toEnu = ({ lat, lon }) => ({ x: R * Math.cos(lat) * (lon - lon0), y: R * (lat - lat0) });
const fromEnu = (e, n) => { const lat = lat0 + n / R; return { lat, lon: lon0 + e / (R * Math.cos(lat)) }; };

// Self-check of the projection pair (round trip below a millimetre).
{
  const p = tmForward(lat0, lon0);
  const q = tmInverse(p.x, p.y);
  if (Math.abs(q.lat - lat0) * R > 1e-3 || Math.abs(q.lon - lon0) * R > 1e-3) throw new Error('TM round trip failed');
}

// Query envelope: the crop corners in MTM plus a 300 m margin for the registration offset.
const corners = [[0, 0], [W, 0], [0, H], [W, H]].map(([dx, dy]) => {
  const g = fromEnu(crop.origin_x_m + dx, crop.origin_y_m + dy);
  return tmForward(g.lat, g.lon);
});
const env = {
  xmin: Math.min(...corners.map((c) => c.x)) - 300,
  ymin: Math.min(...corners.map((c) => c.y)) - 300,
  xmax: Math.max(...corners.map((c) => c.x)) + 300,
  ymax: Math.max(...corners.map((c) => c.y)) + 300,
};
const params = new URLSearchParams({
  where: '1=1',
  geometry: JSON.stringify(env),
  geometryType: 'esriGeometryEnvelope',
  spatialRel: 'esriSpatialRelIntersects',
  outFields: 'unit,name,symbol,Unit_Description,Additional_Characteristics,Unit_Interpretation',
  returnGeometry: 'true',
  f: 'json',
});
const res = await fetch(`${SERVICE}/query?${params}`);
if (!res.ok) throw new Error(`HTTP ${res.status}`);
const raw = await res.text();
const data = JSON.parse(raw);
if (data.error) throw new Error(JSON.stringify(data.error));
console.log(`${data.features.length} unit polygons intersect the crop envelope`);

/** Sutherland-Hodgman clip of one ring against an axis-aligned rectangle (rings stay closed loops). */
function clipRing(ring, x0, y0, x1, y1) {
  const edges = [
    [(p) => p[0] >= x0, (a, b) => [x0, a[1] + ((b[1] - a[1]) * (x0 - a[0])) / (b[0] - a[0])]],
    [(p) => p[0] <= x1, (a, b) => [x1, a[1] + ((b[1] - a[1]) * (x1 - a[0])) / (b[0] - a[0])]],
    [(p) => p[1] >= y0, (a, b) => [a[0] + ((b[0] - a[0]) * (y0 - a[1])) / (b[1] - a[1]), y0]],
    [(p) => p[1] <= y1, (a, b) => [a[0] + ((b[0] - a[0]) * (y1 - a[1])) / (b[1] - a[1]), y1]],
  ];
  let pts = ring;
  for (const [inside, cut] of edges) {
    const next = [];
    for (let i = 0; i < pts.length; i++) {
      const a = pts[(i + pts.length - 1) % pts.length];
      const b = pts[i];
      if (inside(b)) {
        if (!inside(a)) next.push(cut(a, b));
        next.push(b);
      } else if (inside(a)) next.push(cut(a, b));
    }
    pts = next;
    if (pts.length === 0) break;
  }
  return pts;
}
const MARGIN = 50;
const [cx0, cy0, cx1, cy1] = [crop.origin_x_m - MARGIN, crop.origin_y_m - MARGIN, crop.origin_x_m + W + MARGIN, crop.origin_y_m + H + MARGIN];

const units = new Map();
const polygons = [];
for (const f of data.features) {
  const a = f.attributes;
  const id = a.unit;
  if (!units.has(id)) {
    units.set(id, {
      id,
      name: a.name,
      symbol: a.symbol,
      description: a.Unit_Description ?? '',
      characteristics: a.Additional_Characteristics ?? '',
      interpretation: a.Unit_Interpretation ?? '',
    });
  }
  const rings = f.geometry.rings
    .map((ring) => ring.map(([x, y]) => { const p = toEnu(tmInverse(x, y)); return [p.x, p.y]; }))
    .map((ring) => clipRing(ring, cx0, cy0, cx1, cy1).map(([x, y]) => [Math.round(x * 10) / 10, Math.round(y * 10) / 10]))
    .filter((ring) => ring.length >= 3);
  if (rings.length) polygons.push({ unit: id, rings });
}

const out = {
  source: {
    title: 'Geologic map of Jezero crater and the Nili Planum region, Mars (USGS SIM 3464)',
    authors: 'Sun, V., and Stack, K.',
    year: 2020,
    scale: '1:75,000',
    doi: 'https://doi.org/10.3133/sim3464',
    data_release: 'https://doi.org/10.5066/P9CZYIO7',
    service: SERVICE,
    licence: 'USGS publication, public domain',
    registration_note: 'Drawn on a semi-controlled CTX mosaic: about 100-200 m offset against the controlled Mars 2020 CTX terrain. Not re-registered; boundaries are approximate.',
    response_sha256: createHash('sha256').update(raw).digest('hex'),
  },
  frame: { crs: 'Crop local ENU (same as terrain_meta)', origin_x_m: crop.origin_x_m, origin_y_m: crop.origin_y_m, width_m: W, height_m: H },
  // Only units with area inside the crop.
  units: [...units.values()].filter((u) => polygons.some((p) => p.unit === u.id)).sort((p, q) => p.id.localeCompare(q.id)),
  polygons,
};
writeFileSync(outPath, JSON.stringify(out));
console.log(`units: ${out.units.map((u) => `${u.id} (${u.name})`).join(', ')}`);
console.log(`written ${outPath}`);
