import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { sliderSeekTime } from '../src/components/Timeline';
import { fromGatewayPackage, parseJsonLines, type GatewayManifest, type GatewaySnapshot, type PublicRasters } from '../src/data/gatewayReplay';
import { viewAt } from '../src/lib/replay';
import { blockDepthM, CUT_DEPTH_M } from '../src/lib/strata';

describe('slider maximum decimal serialization', () => {
  it('normalizes the actual Chrome End value to the exact maximum', () => {
    expect(sliderSeekTime('116.892579555511', 116.89257955551147)).toBe(116.89257955551147);
  });

  it.each([116.89257955551147, 1234.1234567890123, .12345678901234567])('accepts the maximum at 15, 16 or 17 significant digits (%s)', (duration) => {
    for (const digits of [15, 16, 17]) expect(sliderSeekTime(duration.toPrecision(digits), duration)).toBe(duration);
  });

  it('does not advance an ordinary earlier seek to the final recorded state', () => {
    const duration = 116.89257955551147;
    const earlier = duration - 1e-8;
    expect(sliderSeekTime(String(earlier), duration)).toBe(earlier);
    expect(sliderSeekTime('100', duration)).toBe(100);
  });
});

it('shows exact closing modes and resources when the featured recording slider reaches End', () => {
  const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'recorded-recovery-001');
  const read = <T>(name: string) => JSON.parse(readFileSync(join(dir, name), 'utf8')) as T;
  const manifest = read<GatewayManifest>('manifest.json');
  const records = parseJsonLines(readFileSync(join(dir, 'timeline.jsonl'), 'utf8'));
  const bundle = fromGatewayPackage(manifest, records, read<PublicRasters>('public_rasters.json'), read<GatewaySnapshot>('snapshot.json'));
  const duration = bundle.manifest.duration_s;
  const domEnd = duration.toPrecision(15);
  const exact = viewAt(bundle, sliderSeekTime(domEnd, duration));
  const closing = bundle.timeline.frames.at(-1)!.mission_state;
  expect(exact.state?.agents).toEqual(closing.agents);
  expect(exact.state?.agents.find((agent) => agent.agent_id === 'human_1')?.mode).toBe('IDLE');
  // Raw timestamps still obey strict history selection. The UI conversion is
  // not permission to expose an IDLE frame before its actual arrival time.
  if (Number(domEnd) < duration) {
    expect(viewAt(bundle, Number(domEnd)).state?.agents.find((agent) => agent.agent_id === 'human_1')?.mode).toBe('MOVING');
  }
});

it('scales only the plain visual block depth on the 128 m crop', () => {
  expect(blockDepthM(128, false)).toBeCloseTo(23.04);
  expect(blockDepthM(2000, false)).toBe(CUT_DEPTH_M);
  expect(blockDepthM(128, true)).toBe(CUT_DEPTH_M);
  const minimumRecordedHeight = -2574;
  expect(minimumRecordedHeight - blockDepthM(128, false)).toBeCloseTo(-2597.04);
});
