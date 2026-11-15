import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';
import { CameraBar } from '../src/components/CameraBar';
import { TitleBlock } from '../src/components/Frame';
import { DEFAULT_RUN_ENTRY, RECORDED_RECOVERY_ENTRY, RUNS } from '../src/data/replayAdapter';
import { fromGatewayPackage, parseJsonLines, type GatewayManifest } from '../src/data/gatewayReplay';
import { aboutData } from '../src/lib/stateSnapshot';
import { ORBITAL_PREVIEW_LABEL } from '../src/lib/terrainPresentation';

const fixture = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'sample', 'replay', 'mock-vertical-001');
const manifest = JSON.parse(readFileSync(join(fixture, 'manifest.json'), 'utf8')) as GatewayManifest;
const bundle = fromGatewayPackage(manifest, parseJsonLines(readFileSync(join(fixture, 'timeline.jsonl'), 'utf8')));

describe('recorded recovery entry', () => {
  it('offers the recorder case first and preserves the illustrative demo separately', () => {
    expect(DEFAULT_RUN_ENTRY).toBe('recorded-recovery-001');
    expect(RUNS[0].id).toBe(DEFAULT_RUN_ENTRY);
    expect(RUNS.find((run) => run.id === 'demo')?.label).toMatch(/Illustrative.*generated/);
  });

  it('keeps the entry folder separate from the recorded identity and states its scope', () => {
    const m = { ...bundle.manifest, run_id: 'it-execution' };
    const html = renderToStaticMarkup(createElement(TitleBlock, { manifest: m, runId: RECORDED_RECOVERY_ENTRY }));
    expect(html).toContain('value="recorded-recovery-001" selected');
    expect(html).toContain('Recorded run: it-execution');
    expect(html).toContain('Rover and drone remain idle');
    expect(html).toContain('Not a scientific COMPLETE mission');
  });

  it('labels the visual slope operation before it has been activated', () => {
    const noop = () => {};
    const html = renderToStaticMarkup(createElement(CameraBar, { agents: [], view: 'free', hasBase: false,
      onFree: noop, onBase: noop, onAgent: noop, firstPerson: false, onFirstPerson: noop, canScan: true, onScan: noop }));
    expect(html).toContain(ORBITAL_PREVIEW_LABEL);
    expect(html).toContain('no new observation');
    expect(html).not.toContain('with its camera');
  });

  it('does not attribute demo geology, imagery or a 2 km crop to a recorder package', () => {
    const about = aboutData(bundle);
    expect(about).toContain(bundle.manifest.terrain_meta.dataset_id);
    expect(about).toContain('No matched geologic layer');
    expect(about).not.toMatch(/2 km|SIM 3464|MEDA|orthomosaic/);
  });
});
