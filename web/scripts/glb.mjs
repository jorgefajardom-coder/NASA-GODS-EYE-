/**
 * Minimal GLB (glTF 2.0 binary) reader/writer for embedded images. Used by the branding
 * cleanup script and its regression test; it touches only image buffer views and keeps every
 * other buffer view byte-identical.
 */
import { PNG } from 'pngjs';

const MAGIC = 0x46546c67; // "glTF"
const JSON_CHUNK = 0x4e4f534a;
const BIN_CHUNK = 0x004e4942;

/** @param {Buffer} buf */
export function readGlb(buf) {
  if (buf.readUInt32LE(0) !== MAGIC || buf.readUInt32LE(4) !== 2) throw new Error('not a glTF 2.0 GLB');
  const jsonLen = buf.readUInt32LE(12);
  if (buf.readUInt32LE(16) !== JSON_CHUNK) throw new Error('first GLB chunk is not JSON');
  const json = JSON.parse(buf.subarray(20, 20 + jsonLen).toString('utf8'));
  const binHeader = 20 + jsonLen;
  if (buf.readUInt32LE(binHeader + 4) !== BIN_CHUNK) throw new Error('second GLB chunk is not BIN');
  const binLen = buf.readUInt32LE(binHeader);
  const bin = buf.subarray(binHeader + 8, binHeader + 8 + binLen);
  if ((json.buffers ?? []).length !== 1) throw new Error('expected exactly one buffer');
  const views = json.bufferViews.map((v) => Buffer.from(bin.subarray(v.byteOffset ?? 0, (v.byteOffset ?? 0) + v.byteLength)));
  return { json, views };
}

const pad4 = (n) => (4 - (n % 4)) % 4;

/** Re-lays out the BIN chunk from the (possibly replaced) buffer views, 4-byte aligned. */
export function writeGlb({ json, views }) {
  const parts = [];
  let offset = 0;
  views.forEach((data, i) => {
    json.bufferViews[i].byteOffset = offset;
    json.bufferViews[i].byteLength = data.length;
    parts.push(data, Buffer.alloc(pad4(data.length)));
    offset += data.length + pad4(data.length);
  });
  json.buffers[0].byteLength = offset;
  const bin = Buffer.concat(parts);
  let text = Buffer.from(JSON.stringify(json), 'utf8');
  text = Buffer.concat([text, Buffer.alloc(pad4(text.length), 0x20)]);
  const header = Buffer.alloc(12);
  header.writeUInt32LE(MAGIC, 0);
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(12 + 8 + text.length + 8 + bin.length, 8);
  const chunk = (type, data) => {
    const h = Buffer.alloc(8);
    h.writeUInt32LE(data.length, 0);
    h.writeUInt32LE(type, 4);
    return [h, data];
  };
  return Buffer.concat([header, ...chunk(JSON_CHUNK, text), ...chunk(BIN_CHUNK, bin)]);
}

/** Index of the buffer view that holds the PNG image with this name. */
export function imageView(glb, name) {
  const img = (glb.json.images ?? []).find((im) => im.name === name);
  if (!img || img.bufferView === undefined) throw new Error(`no embedded image named ${name}`);
  if (img.mimeType !== 'image/png') throw new Error(`image ${name} is ${img.mimeType}, expected image/png`);
  return img.bufferView;
}

export function decodeImage(glb, name) {
  return PNG.sync.read(glb.views[imageView(glb, name)]);
}

/** True when every pixel of the rectangle [x0, x1) × [y0, y1) has the same RGB value. */
export function isFlat(png, [x0, y0, x1, y1]) {
  const at = (x, y) => (y * png.width + x) * 4;
  const r = png.data[at(x0, y0)], g = png.data[at(x0, y0) + 1], b = png.data[at(x0, y0) + 2];
  for (let y = y0; y < y1; y++)
    for (let x = x0; x < x1; x++) {
      const i = at(x, y);
      if (png.data[i] !== r || png.data[i + 1] !== g || png.data[i + 2] !== b) return false;
    }
  return true;
}
