import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/** R05: the hidden evaluator reference must never be part of the public site. */
const WEB = join(dirname(fileURLToPath(import.meta.url)), '..');

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
}

describe('evaluator reference isolation (R05)', () => {
  it('is not in any public replay fixture', () => {
    for (const f of files(join(WEB, 'public', 'replay')).filter((p) => p.endsWith('.json'))) {
      const j = JSON.parse(readFileSync(f, 'utf8'));
      expect(j, f).not.toHaveProperty('reference');
    }
  });

  it('is only served by the dev server and never emitted into the build', () => {
    const cfg = readFileSync(join(WEB, 'vite.config.ts'), 'utf8');
    const plugin = cfg.slice(cfg.indexOf('function evaluatorReference'), cfg.indexOf('function sampleReplays'));
    expect(plugin).toMatch(/apply: 'serve'/);
    expect(plugin).not.toMatch(/emitFile|generateBundle/);
  });
});
