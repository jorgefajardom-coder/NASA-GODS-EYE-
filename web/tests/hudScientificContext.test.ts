import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { HudGauge } from '../src/components/HudGauge';
import { fromGatewayPackage, parseJsonLines } from '../src/data/gatewayReplay';
import { viewAt } from '../src/lib/replay';

const dir = join(import.meta.dirname, '../../data/sample/replay/mock-vertical-001');
const bundle = fromGatewayPackage(JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8')),
  parseJsonLines(readFileSync(join(dir, 'timeline.jsonl'), 'utf8')));
const firstFrame = bundle.timeline.frames[0];
const view = viewAt(bundle, firstFrame.timestamp_sim_s);
const agent = view.state!.agents.find((a) => a.agent_kind === 'HUMAN')!;
const props = { size: 168, bundle, view, t: firstFrame.timestamp_sim_s, agent, route: null,
  budget: { time_s: 1000, energy_wh: 100, oxygen_l: 25 }, atmosphere: undefined, runId: 'gale-demo' };

describe('scientific context in the rendered HUD', () => {
  it('reports dose equivalent without a career-limit percentage', () => {
    const html = renderToStaticMarkup(createElement(HudGauge, { ...props, option: 'dose', t: 3600 }));
    expect(html).toContain('RAD dose equivalent');
    expect(html).toContain('career-limit compliance are not calculated');
    expect(html).not.toMatch(/% of NASA|600 mSv/);
  });

  it('does not turn an unavailable breathing rate into a reassuring physiological claim', () => {
    const single = { ...bundle, timeline: { ...bundle.timeline, frames: [bundle.timeline.frames[0]] } };
    const html = renderToStaticMarkup(createElement(HudGauge, { ...props, bundle: single, option: 'co2' }));
    expect(html).toContain('rate unavailable');
    expect(html).not.toContain('not breathing hard');
    expect(html).toContain('removal capacity is not modelled');
  });
});
