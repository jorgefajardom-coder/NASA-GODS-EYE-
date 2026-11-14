import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Recorded gateway runs live once, in the repository's data/sample/replay/<run_id>/
 * (written by replay_recorder, docs/ICD.md §7). They are served at replay/<run_id>/
 * in development and copied into dist/ on build, so they are never duplicated in web/.
 */
const SAMPLE_REPLAYS = resolve(__dirname, '../data/sample/replay');
const REPLAY_FILE = /^[\w.-]+\.(json|jsonl)$/;

function replayFiles(): Array<{ run: string; file: string; path: string }> {
  if (!existsSync(SAMPLE_REPLAYS)) return [];
  return readdirSync(SAMPLE_REPLAYS)
    .filter((run) => statSync(join(SAMPLE_REPLAYS, run)).isDirectory())
    .flatMap((run) =>
      readdirSync(join(SAMPLE_REPLAYS, run))
        .filter((f) => REPLAY_FILE.test(f))
        .map((file) => ({ run, file, path: join(SAMPLE_REPLAYS, run, file) })),
    );
}

function sampleReplays(): Plugin {
  return {
    name: 'mge-sample-replays',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const m = /^\/replay\/([\w.-]+)\/([\w.-]+)$/.exec((req.url ?? '').split('?')[0]);
        const hit = m && replayFiles().find((f) => f.run === m[1] && f.file === m[2]);
        if (!hit) return next();
        res.setHeader('Content-Type', hit.file.endsWith('.jsonl') ? 'application/x-ndjson' : 'application/json');
        res.end(readFileSync(hit.path));
      });
    },
    generateBundle() {
      for (const f of replayFiles()) {
        this.emitFile({ type: 'asset', fileName: `replay/${f.run}/${f.file}`, source: readFileSync(f.path) });
      }
    },
  };
}

// Relative base so the build works from any GitHub Pages subfolder
// and when opened from a plain static server (replay mode, J-04).
export default defineConfig({
  base: './',
  plugins: [react(), sampleReplays()],
  build: { chunkSizeWarningLimit: 1500 },
  test: { environment: 'node', include: ['tests/**/*.test.ts'] },
});
