import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';
import { CameraBar } from '../src/components/CameraBar';
import { TitleBlock } from '../src/components/Frame';
import { TerrainScanButton } from '../src/components/TerrainScanButton';
import { DEFAULT_RUN_ENTRY, RECORDED_RECOVERY_ENTRY, RUNS } from '../src/data/replayAdapter';
import { fromGatewayPackage, parseJsonLines, type GatewayManifest } from '../src/data/gatewayReplay';
import { aboutData } from '../src/lib/stateSnapshot';
import { ORBITAL_PREVIEW_LABEL } from '../src/lib/terrainPresentation';

const fixture = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'sample', 'replay', 'mock-vertical-001');
const manifest = JSON.parse(readFileSync(join(fixture, 'manifest.json'), 'utf8')) as GatewayManifest;
const bundle = fromGatewayPackage(manifest, parseJsonLines(readFileSync(join(fixture, 'timeline.jsonl'), 'utf8')));

describe('recorded recovery entry', () => {
  it('opens the illustrative demo by default and keeps the recorder case as its own entry', () => {
    expect(DEFAULT_RUN_ENTRY).toBe('demo');
    expect(RUNS[0].id).toBe(DEFAULT_RUN_ENTRY);
    expect(RUNS.find((run) => run.id === 'demo')?.label).toMatch(/Illustrative.*generated/);
    expect(RUNS.find((run) => run.id === RECORDED_RECOVERY_ENTRY)?.label).toMatch(/MOCK/);
  });

  it('keeps the entry folder separate from the recorded identity and states its scope', () => {
    const m = { ...bundle.manifest, run_id: 'it-execution' };
    const html = renderToStaticMarkup(createElement(TitleBlock, { manifest: m, runId: RECORDED_RECOVERY_ENTRY }));
    expect(html).toContain('value="recorded-recovery-001" selected');
    expect(html).toContain('Recorded run: it-execution');
    expect(html).toContain('Rover and drone remain idle');
    expect(html).toContain('Not a scientific COMPLETE mission');
  });

  it('no longer offers the drone orbital preview; the terrain scan labels itself display only', () => {
    const noop = () => {};
    const bar = renderToStaticMarkup(createElement(CameraBar, { agents: [], view: 'free', hasBase: false,
      onFree: noop, onBase: noop, onAgent: noop, firstPerson: false, onFirstPerson: noop }));
    expect(bar).not.toContain(ORBITAL_PREVIEW_LABEL);
    expect(bar).not.toContain('with its camera');
    const key = renderToStaticMarkup(createElement(TerrainScanButton));
    expect(key).toContain('Terrain scan');
    expect(key).toMatch(/Display only, not a sensor|Scanner/);
  });

  it('does not attribute demo geology, imagery or a 2 km crop to a recorder package', () => {
    const about = aboutData(bundle);
    expect(about).toContain(bundle.manifest.terrain_meta.dataset_id);
    expect(about).toContain('No matched geologic layer');
    expect(about).not.toMatch(/2 km|SIM 3464|MEDA|orthomosaic/);
  });
});

describe('run selector', () => {
  it('offers only the simulated worlds, no MOCK entry', async () => {
    const { OFFERED_RUNS } = await import('../src/data/replayAdapter');
    expect(OFFERED_RUNS.map((r) => r.id)).toEqual([DEFAULT_RUN_ENTRY, 'gale-demo']);
    expect(OFFERED_RUNS.some((r) => /MOCK/.test(r.label))).toBe(false);
  });
});
