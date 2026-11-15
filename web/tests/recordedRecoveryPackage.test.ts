import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PerspectiveCamera, Vector3 } from 'three';
import { expect, it } from 'vitest';
import { RECORDED_RECOVERY_ENTRY } from '../src/data/replayAdapter';
import {
  fromGatewayPackage, parseJsonLines, type GatewayManifest, type GatewaySnapshot, type PublicRasters,
} from '../src/data/gatewayReplay';
import { terrainFraming } from '../src/lib/terrainPresentation';

/** Mandatory consumer of the actual featured recorder output. No generated
 * substitute and no environment-dependent skip: a broken default must fail CI.
 */
it('opens the featured recorder package with its recorded decision change and absolute datum', () => {
  // The recorder package is consumed by name; the viewer's default entry is a separate choice.
  const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', RECORDED_RECOVERY_ENTRY);
  for (const name of ['manifest.json', 'timeline.jsonl', 'snapshot.json', 'public_rasters.json']) {
    expect(existsSync(join(dir, name)), `Missing featured recording: ${name}`).toBe(true);
  }
  const read = <T>(name: string) => JSON.parse(readFileSync(join(dir, name), 'utf8')) as T;
  const manifest = read<GatewayManifest>('manifest.json');
  const records = parseJsonLines(readFileSync(join(dir, 'timeline.jsonl'), 'utf8'));
  const snapshot = read<GatewaySnapshot>('snapshot.json');
  const rasters = read<PublicRasters>('public_rasters.json');
  const bundle = fromGatewayPackage(manifest, records, rasters, snapshot);

  expect(bundle.manifest.run_id).toBe(manifest.run_id);
  expect(bundle.manifest.source_mode).toBe('MOCK');
  expect(snapshot.mission_state?.mission_state).toBe('READY');
  expect(snapshot.mission_state?.mission_state).not.toBe('COMPLETE');
  expect(bundle.timeline.frames).toHaveLength(records.filter((record) => record.type === 'state').length);
  expect(bundle.timeline.events).toHaveLength(manifest.event_count);
  expect(Object.keys(rasters.versions).map(Number).sort()).toEqual([1, 2]);
  expect(rasters.versions['1'].observed).toEqual([]);
  expect(rasters.versions['2'].observed).toHaveLength(1);
  expect([...new Set([...bundle.routes.values()].map((route) => route.map_version_used))].sort()).toEqual([1, 2]);
  expect(bundle.rasters.prior).toEqual(rasters.prior);
  for (const version of ['1', '2']) expect(bundle.rasters.versions[version]).toEqual(rasters.versions[version]);

  const agents = bundle.timeline.frames.flatMap((frame) => frame.mission_state.agents);
  const positions = (id: string) => new Set(agents.filter((agent) => agent.agent_id === id)
    .map((agent) => JSON.stringify(agent.pose.position)));
  expect(positions('human_1').size).toBeGreaterThan(2);
  for (const id of ['rover_1', 'drone_1']) {
    expect(positions(id).size).toBe(1);
    expect(agents.filter((agent) => agent.agent_id === id).every((agent) => agent.mode === 'IDLE')).toBe(true);
  }

  // The recording is drawn in its absolute datum, not translated to the demo's
  // -2495 m offset. Every prior bounding corner must be in the initial frustum.
  expect(bundle.manifest.local_z_offset_m).toBeUndefined();
  const heights = rasters.prior.filter((h): h is number => h !== null);
  expect(heights.length).toBeGreaterThan(0);
  const lo = Math.min(...heights), hi = Math.max(...heights);
  const meta = bundle.manifest.terrain_meta;
  const framing = terrainFraming(meta, rasters.prior);
  expect(framing.target[1]).toBe((lo + hi) / 2);
  const camera = new PerspectiveCamera(38, 16 / 9, 1, framing.far);
  camera.position.set(...framing.position);
  camera.lookAt(new Vector3(...framing.target));
  camera.updateMatrixWorld();
  for (const x of [meta.origin_x_m, meta.origin_x_m + meta.cols * meta.resolution_m]) {
    for (const north of [meta.origin_y_m, meta.origin_y_m + meta.rows * meta.resolution_m]) {
      for (const z of [lo, hi]) {
        const ndc = new Vector3(x, z, -north).project(camera);
        expect(Math.abs(ndc.x)).toBeLessThan(1);
        expect(Math.abs(ndc.y)).toBeLessThan(1);
        expect(Math.abs(ndc.z)).toBeLessThan(1);
      }
    }
  }
});
