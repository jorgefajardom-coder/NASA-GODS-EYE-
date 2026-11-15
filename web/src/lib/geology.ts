/**
 * Geologic units of the run area (USGS SIM 3464 via scripts/extract-geology.mjs), in the
 * terrain's local ENU frame. Boundaries are approximate: the map was drawn on a
 * semi-controlled CTX mosaic (about 100-200 m offset against the terrain).
 */
export interface GeologyUnit {
  id: string;
  name: string;
  symbol: string;
  description: string;
  /** "Additional characteristics" of the map: mineral associations (composition) and notes. */
  characteristics: string;
  interpretation: string;
}

export interface GeologyData {
  source: {
    title: string;
    authors: string;
    year: number;
    scale: string;
    doi: string;
    data_release: string;
    service: string;
    licence: string;
    registration_note: string;
    response_sha256: string;
  };
  frame: { crs: string; origin_x_m: number; origin_y_m: number; width_m: number; height_m: number; dataset_id?: string; origin_lat_deg?: number; origin_lon_deg?: number; vertical_datum?: string };
  units: GeologyUnit[];
  polygons: Array<{ unit: string; rings: Array<Array<[number, number]>> }>;
}

/** Map-style display colours (not the USGS sheet palette), stable per unit. */
const PALETTE = ['#5F9EA0', '#C8875A', '#8C7AA8', '#D9C27A', '#6E9F6B', '#B85C5C', '#7FA7C9', '#A88C6E'];
export function unitColor(data: GeologyData, unitId: string): string {
  const i = data.units.findIndex((u) => u.id === unitId);
  return PALETTE[(i < 0 ? 0 : i) % PALETTE.length];
}

/**
 * Rasterizes the unit polygons on an n x n grid covering the frame. Row 0 is the south edge
 * (same as the terrain rasters and texture v). Each cell holds the index of its unit in
 * `data.units`, or -1 when no unit covers it. Even-odd fill, sampled at cell centres.
 */
export function rasterizeUnits(data: GeologyData, n: number): Int16Array {
  const { origin_x_m: ox, origin_y_m: oy, width_m: w, height_m: h } = data.frame;
  const grid = new Int16Array(n * n).fill(-1);
  const index = new Map(data.units.map((u, i) => [u.id, i]));
  const xs: number[] = [];
  for (const poly of data.polygons) {
    const k = index.get(poly.unit);
    if (k == null) continue;
    for (let r = 0; r < n; r++) {
      const y = oy + ((r + 0.5) / n) * h;
      xs.length = 0;
      for (const ring of poly.rings) {
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          const [x1, y1] = ring[j];
          const [x2, y2] = ring[i];
          if (y1 > y !== y2 > y) xs.push(x1 + ((y - y1) * (x2 - x1)) / (y2 - y1));
        }
      }
      xs.sort((a, b) => a - b);
      for (let s = 0; s + 1 < xs.length; s += 2) {
        const c0 = Math.max(0, Math.ceil(((xs[s] - ox) / w) * n - 0.5));
        const c1 = Math.min(n - 1, Math.floor(((xs[s + 1] - ox) / w) * n - 0.5));
        for (let c = c0; c <= c1; c++) grid[r * n + c] = k;
      }
    }
  }
  return grid;
}

/** Share of the frame covered by each unit (0..1), in `data.units` order, plus the uncovered share. */
export function unitShares(data: GeologyData, grid: Int16Array): { shares: number[]; uncovered: number } {
  const counts = new Array<number>(data.units.length).fill(0);
  let none = 0;
  for (const v of grid) {
    if (v < 0) none++;
    else counts[v]++;
  }
  return { shares: counts.map((c) => c / grid.length), uncovered: none / grid.length };
}

/** RGBA pixels for a texture (row 0 = south). The selected unit is drawn at full strength. */
export function unitPixels(data: GeologyData, grid: Int16Array, selected: string | null): Uint8Array {
  const rgb = data.units.map((u) => {
    const hex = unitColor(data, u.id);
    return [1, 3, 5].map((o) => parseInt(hex.slice(o, o + 2), 16));
  });
  const sel = selected == null ? -1 : data.units.findIndex((u) => u.id === selected);
  const out = new Uint8Array(grid.length * 4);
  for (let i = 0; i < grid.length; i++) {
    const v = grid[i];
    let c = v < 0 ? [40, 40, 40] : rgb[v];
    if (sel >= 0 && v !== sel) c = c.map((x) => Math.round(x * 0.35 + 30));
    out[i * 4] = c[0];
    out[i * 4 + 1] = c[1];
    out[i * 4 + 2] = c[2];
    out[i * 4 + 3] = 255;
  }
  return out;
}
