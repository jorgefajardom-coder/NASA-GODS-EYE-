import type { PNGWithMetadata } from 'pngjs';

export interface Glb {
  json: { images?: Array<{ name?: string; mimeType?: string; bufferView?: number }>; [key: string]: unknown };
  views: Buffer[];
}

export function readGlb(buf: Buffer): Glb;
export function writeGlb(glb: Glb): Buffer;
export function imageView(glb: Glb, name: string): number;
export function decodeImage(glb: Glb, name: string): PNGWithMetadata;
export function isFlat(png: { width: number; data: Buffer }, rect: [number, number, number, number]): boolean;
