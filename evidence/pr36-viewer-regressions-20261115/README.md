# PR36 viewer regression corrections

Owner-requested fixes on `feat/ux`, starting at
`40a59741e0a68276f92932d25faeeadfd8f80906`, over published main
`64985e7b4b69ac9683661db4842885d5a8293695`. This record identifies the tested
runtime/test files by SHA-256 in [validation.json](validation.json); the fixes
are committed separately. Original review reproductions remain local.

## Corrected behavior

- No WebGL: the application preserves the 2D replay and offers DOM zone cards.
  A failed context allocation after GPU probing also falls back rather than
  unmounting the application. Next/previous, enter and escape retain behavior.
- Raw images: shared results, loading and errors carry mission and query
  context. Atmos shows latest Perseverance imagery only; historical stops and
  Curiosity results require the matching mission window. Sol changes trigger
  a fresh tour request even when the stop identifier is unchanged. An old
  pending load cannot replace a no-feed mission result.

## Reproduction and observed checks

With Node 24.18.0, from `web`:

```sh
npm ci
npm test
npm run build
```

The web suite passed **311 tests, one existing skip, across 51 files**. The
eight new regressions cover the two browser regressions and query/context
edges. Build and `git diff --check` passed. Logs are retained alongside this
record. `py -3.14 scripts/check_repository.py` passed locally. Local full
pytest was unavailable (`No module named pytest`); local ROS/colcon was not
rerun. Final-head Python/web/ROS CI is a separate pre-merge condition; refer
to the PR's check record rather than treating old-head CI as fresh evidence.

Production-browser check: serve `web/dist` using a file-only static server,
launch Chrome with a fresh private profile and `--disable-webgl --disable-gpu`,
and open `/?nointro=1` with reduced motion. Check the 2D selector, next and
previous zone, and Back to the 2D map. Then open
`/?run=recorded-recovery-001&nointro=1` and seek to the end. The browser record
in [browser.json](browser.json) preserves the results. No screenshot or media
is produced.

The original recorded files are unchanged; their hashes are retained in
validation.json against runtime-v1. This is the existing `it-execution` MOCK
recovery, ending READY, not scientific COMPLETE. The newer illustrative worlds
are not substituted for the recorder package.

## Acceptance boundaries

These are software regressions and an automated local browser check. Formal
AC-08 owner acceptance, public/two-machine access, steps 4/5, three-role
execution, scientific costs/profiles and organizer endorsement remain separate
open gates. No new terrain, observation, mission authority or shared schema is
introduced. Existing AI media marks and third-party attributions are preserved.

AI use: code, synthetic test fixtures and this software evidence record were
prepared with OpenAI Codex assistance, declared in docs/AI_USAGE.md and
docs/ai_usage.json. No NASA data or media was generated.
