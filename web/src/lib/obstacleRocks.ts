import type { TerrainMeta } from '../types/icd';

type GridMeta = Pick<TerrainMeta, 'rows' | 'cols' | 'origin_x_m' | 'origin_y_m' | 'resolution_m'>;

/** Number of distinct boulder shapes the scene builds (see components/ObstacleRocks). */
export const ROCK_VARIANTS = 5;

/**
 * Rock size model (display only). Golombek & Rapp (1997, JGR 102(E2):4117-4129), the model used
 * to assess rock hazards at Mars landing sites, gives the cumulative fractional area covered by
 * rocks of diameter >= D as F(D) = k exp(-q D), with q = 1.79 + 0.152 / k. Sizes here follow that
 * exponential law: small rocks are common, large ones rare. ROCK_ABUNDANCE_K is an illustrative
 * value, not a measurement for these cells (owner review pending).
 */
export const ROCK_ABUNDANCE_K = 0.05;
export const ROCK_DECAY_PER_M = 1.79 + 0.152 / ROCK_ABUNDANCE_K;
/**
 * Smallest obstacle rock drawn on an impassable cell. An obstacle mapped from orbit must be
 * resolvable there: HiRISE (25 cm/px) rock counts used for Mars landing-site hazard maps
 * (Golombek et al.) start at boulders of about 1.5 m diameter. Larger rocks follow the
 * Golombek-Rapp tail above it. This is a deliberate ENLARGEMENT for use: rocks of the size law
 * are mostly decimetre-sized and could not be read at mission scale (see web/README.md, Obstacle
 * rocks). Display only, pending review; not a rover or EVA specification.
 */
export const HAZARD_ROCK_M = 1.5;
/** Impassable cells with at least this many impassable 4-neighbours form an outcrop section. */
export const SECTION_NEIGHBOURS = 2;

/**
 * Obstacle style per geologic unit of USGS SIM 3464 (Sun & Stack 2020), the units of the public
 * Jezero crop. Njf, "Jezero floor unit": rugged, mafic, light- to dark-toned crater floor, so dark
 * angular blocks. Nle, "Lower etched unit": rugged, light- to intermediate-toned, etched, so
 * lighter flat slabs of eroded layered rock. Colours and shapes are an artistic reading of the map
 * descriptions, not measured rock properties.
 */
export interface RockStyle {
  unit: string | null;
  /** Base colour of the rock (dust is added by the shape's vertex colours). */
  colorHex: string;
  /** Height relative to width: blocks are tall, slabs are flat. */
  heightRatio: [number, number];
  /** Larger obstacle factor for slab outcrops (ledges are wider than loose boulders). */
  widthFactor: number;
}

export const ROCK_STYLES: Record<string, RockStyle> = {
  Njf: { unit: 'Njf', colorHex: '#4a3a33', heightRatio: [0.55, 0.85], widthFactor: 1 },
  Nle: { unit: 'Nle', colorHex: '#8a6d55', heightRatio: [0.22, 0.38], widthFactor: 1.8 },
};
export const DEFAULT_ROCK_STYLE: RockStyle = { unit: null, colorHex: '#5a463a', heightRatio: [0.45, 0.75], widthFactor: 1 };

/**
 * One rock of the cluster drawn on an impassable cell (display only). Position is ENU (m);
 * size is the rock's width/height/depth in metres; `sinkM` is how far its base sits below the
 * ground (rocks are partly buried); `shade` varies its brightness.
 */
export interface RockPiece {
  cell: number;
  x: number;
  y: number;
  widthM: number;
  heightM: number;
  depthM: number;
  sinkM: number;
  yawRad: number;
  tiltRad: number;
  variant: number;
  shade: number;
  /** True for the cell's hazard-size rocks; the others are the smaller rocks around them. */
  hazard: boolean;
  /** True when the cell belongs to a continuous blocked section (ridge or outcrop band). */
  section: boolean;
  style: RockStyle;
}

/** Deterministic pseudo-random stream for a cell, so a cell always gets the same cluster. */
function stream(seed: number): () => number {
  let s = ((seed + 1) * 2654435761) >>> 0;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5;
    s >>>= 0;
    return s / 4294967296;
  };
}

/** A diameter from the exponential size law, at least `min` m: min + Exp(q). */
function diameter(rnd: () => number, min: number): number {
  return min - Math.log(1 - rnd() * 0.999) / ROCK_DECAY_PER_M;
}

/**
 * Rock clusters for the cells a recorded map version marks impassable (public rasters
 * `impassable`): a hazard-size rock (or, on the etched unit, a slab ledge) plus smaller rocks,
 * sized by the Golombek-Rapp law and styled by the cell's USGS geologic unit when known
 * (`unitAt`). Every rock is placed inside its cell, so none leaves the terrain; indices off the
 * grid are ignored. Cosmetic: not measurements of real rocks at these places.
 */
export function obstacleRocks(
  meta: GridMeta,
  cells: readonly number[] | undefined,
  unitAt: (cell: number) => string | null = () => null,
): RockPiece[] {
  if (!cells?.length) return [];
  const { rows, cols, origin_x_m, origin_y_m, resolution_m: res } = meta;
  const out: RockPiece[] = [];
  const blocked = new Set(cells.filter((c) => Number.isInteger(c) && c >= 0 && c < rows * cols));
  for (const cell of blocked) {
    const style = ROCK_STYLES[unitAt(cell) ?? ''] ?? DEFAULT_ROCK_STYLE;
    const r = Math.floor(cell / cols);
    const c = cell % cols;
    const cx = origin_x_m + (c + 0.5) * res;
    const cy = origin_y_m + (r + 0.5) * res;
    const rnd = stream(cell);
    const neighbours = [r > 0 ? cell - cols : -1, r < rows - 1 ? cell + cols : -1, c > 0 ? cell - 1 : -1, c < cols - 1 ? cell + 1 : -1]
      .filter((n) => blocked.has(n)).length;
    const section = neighbours >= SECTION_NEIGHBOURS;
    // A section cell is filled by two or three large blocks that join its neighbours into a band;
    // an isolated cell has one large boulder. Both are surrounded by smaller rocks.
    const big = section ? 2 + Math.floor(rnd() * 2) : 1;
    const smaller = 5 + Math.floor(rnd() * 6);
    for (let k = 0; k < big + smaller; k++) {
      const hazard = k < big;
      const d = Math.min(res * (section ? 0.8 : 0.7), hazard
        ? diameter(rnd, HAZARD_ROCK_M) * (section ? 1.25 : 1)
        : Math.min(diameter(rnd, 0.1), HAZARD_ROCK_M * 0.5) * style.widthFactor);
      // Large blocks stand up (0.4-0.85 of their width); small rocks follow the unit's shape.
      const [h0, h1] = !hazard ? style.heightRatio
        : section ? [0.55, 0.85] : [Math.max(style.heightRatio[0], 0.4), Math.max(style.heightRatio[1], 0.65)];
      // Keep every rock's footprint inside its cell.
      const room = Math.max(0, res / 2 - d * 0.6);
      out.push({
        cell,
        x: cx + (rnd() * 2 - 1) * room * (hazard && !section ? 0.35 : 1),
        y: cy + (rnd() * 2 - 1) * room * (hazard && !section ? 0.35 : 1),
        widthM: d * (0.85 + 0.3 * rnd()),
        heightM: d * (h0 + (h1 - h0) * rnd()),
        depthM: d * (0.7 + 0.3 * rnd()),
        sinkM: d * (0.08 + 0.1 * rnd()),
        yawRad: rnd() * Math.PI * 2,
        tiltRad: (rnd() * 2 - 1) * (style.heightRatio[1] < 0.5 ? 0.08 : 0.25),
        variant: Math.floor(rnd() * ROCK_VARIANTS),
        shade: 0.82 + 0.3 * rnd(),
        hazard,
        section,
        style,
      });
    }
  }
  return out;
}
