# Private-browser replay check — AC-08 evidence input

Recorded 2026-11-15 04:39 UTC on source `6e57df0db1e34a943fed579e60141893c52fc870`
(`feat/integration`; `web/` identical to `main` `7ad6050`). This is browser
evidence for AC-08. It is **not** the AC-08 acceptance: Jorge and Jesus decide
that, and the limits below apply.

## What was run

`reproduce_private_replay.mjs` serves the production build (`web/dist`) from a
file-only static server on 127.0.0.1 and opens it in Chromium 155 with
`--incognito`, an empty profile and a new off-the-record browser context per
window. It logs every browser request and compares the viewer
(`window.mge.state()` and the visible text) with values the script computes
separately from the package files.

Result: **PASS, 35 of 35 checks** ([result](run/result.json),
[per-window record and request logs](run/windows.json),
[console log](validation/private-replay.log)).

| Window | Observed |
| --- | --- |
| Exact recorder package `?run=recorded-recovery-001` (run `it-execution`, MOCK) | Opens with empty cookies and storage. 62 requests, all to the static origin; no WebSocket, no failed request. Label `REPLAY · MOCK`, `Offline`, no LIVE claim. At five points (planning, first route, invalidation, replacement route, final) run ID, mission state, map version, active route ID/status, invalidated route ID, event sequence and agent modes equal the package. At the final sample, agent poses and remaining resources also equal the package. On the Mission replay tab the latest recorded event text is on screen at each point. |
| Default entry (simulated demo) | 55 requests, all to the static origin; label `REPLAY · SIMULATION`, `Offline`; Play advances the clock. |
| `?evaluator=1` on the public build | The reference request gets 404 and no reference layer is offered. |

The four package files hash to the values in
[the recorder cut](../audit-reconciliation-20261115/runtime-v1/package-sha256.json).
No ROS, Gazebo, gateway, planner or recorder process was running. The build has
no evaluator, reference or HiRISE-named file.

Web checks on the same tree with Node 24.18.0: `npm ci`; `npm test`
**233 passed, 1 skipped**; `npm run build` passed
([logs](validation/)). Absolute local paths in the logs are replaced by `<repo>`.

## Limits

- Automated and headless, with software rendering (SwiftShader). No person
  operated a visible private window.
- One machine, local static server. The public deployed site and two-machine
  access were not checked.
- The recorded package is a MOCK software recovery: human motion only, rover
  and drone idle. It is not the integrated three-role run, so step 5 / C5
  (same-run replay of the step 4 mission) stays open.
- No screenshot, video or audio is stored. Captures show the AI-generated base
  model and need a visible `AI-generated` mark before publication; the script's
  `--screenshots` option writes local captures only.
- No scientific COMPLETE, approved cost model or LIVE mission is claimed.

## Reproduce

From the repository root, with the Node version in `web/.nvmrc` and Chromium
installed:

```sh
(cd web && npm ci && npm test && npm run build)
node evidence/web-private-replay-20261115/reproduce_private_replay.mjs \
  --dist web/dist --out /NEW/EMPTY/DIRECTORY
```

The script refuses a non-empty output directory. Request counts and the blob
URLs in the log vary between runs; the checks are the reproduction criterion.

AI use: the script and this record were written with AI assistance (Claude
Code, Anthropic); see [AI usage](../../docs/AI_USAGE.md). No mission data,
observation or result was generated.
