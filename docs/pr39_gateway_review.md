# PR39 read-only gateway reconciliation — 15 November 2026

## Cut and contract

Reviewed owner branch `feat/live-gateway` at `8ed14b796bcf5de261b719f8dc8c68a8b1ed7ffe` against integrated main `7ff5a077dfe70e181e960a2d638e3a1e955591c1` (PR41 merged). Main is merged into this candidate with preserved ancestry; retarget PR39 from the now-integrated PR37 branch to main. ICD-WEB schema remains `1.0.0`; gateway, recorder, ROS messages and services are unchanged. The proposed contract remains subject to recorded owner review.

`?gateway=<http(s) URL>` enables a separate read-only status line/details panel. The 3D scene and timeline still use saved packages. No mission goals are sent and no connection certifies a LIVE mission. Existing photo-tour exit behavior is preserved. Default six-zone selection, height-corrected recorded-recovery-002 and historical recorded-recovery-001 remain available.

## Corrections

- Validate HTTP status, canonical NOT_READY/ERROR, schema, envelope, run/mode/source and actual ROS payload shapes before showing connected state or rendering resources.
- Rediscover the manifest after unavailable/replaced runs; invalidate old HTTP/WebSocket callbacks. Every fresh handshake starts an authoritative current-store binding, including a restarted store with the same run ID. Historical continuity across reconnections is not asserted without a wire epoch.
- Deduplicate immutable event IDs/sequences, retain a contiguous resume cursor and reconcile gaps through the full snapshot. Out-of-order unique events 1,3,2 are retained; the last 60 form the display window.
- Validate and bind terrain identity/version while displaying terrain metadata version separately from mission map authority. No raster endpoint, geometry or planning authority is invented.
- Preserve exact XYZ, ROS stamps and route data; nonhuman oxygen remains null. Accept the real producer's default inactive RouteDecision. The real mission manager clears rejected routes on BLOCKED.
- Refresh public descriptions for the optional panel and current primary recording. Historical recorder bytes are unchanged.

## Validation

- Windows Python 3.12.14: `python -m pytest --basetemp=.local/pr39-final-pytest`: **1274 passed, 25 skipped**, one warning. Platform/ROS/symlink skips are not mission validation.
- `python scripts/check_repository.py`: PASS (8 package manifests).
- Pinned Node 24.18.0: web `npm test`: **400 passed, 1 existing skip** across 58 files; `npm run build`: PASS. Gateway/panel focused regressions: **65 passed**.
- Actual unchanged FastAPI/create_app/RunStore to the frozen TypeScript client: **five groups PASS**, 17 GET requests, 4 WebSocket connections, **zero goal calls**. Startup 503, ROS-default IDLE/FEASIBLE READY, actual 1,3,2 delivery, gap recovery, run A→B and same-ID store restart are covered. Inputs are the existing public MOCK package, not a new mission or ROS graph. See `evidence/pr39-gateway-contract-20261115/` for byte-locked scripts, responses, reports and reproduction commands.
- Client SHA256: `c8dfee78335621ba982597828306051f3802c1680bd711f68e8b5a8f4f60abd6`. Test receipts correctly record dirty source HEAD8ed plus file hashes; they are not retroactively rewritten to a later commit.
- Exact published-head CI, including Ubuntu ROS checks, must pass before integration. The earlier owner's ROS smoke is historical evidence and is not represented as rerun by this consumer audit.

## Remaining gates and next deliverable

Owner review and explicit merge approval precede integration; final CI is recorded in the PR. An inactive integration-branch event-stream change is outside this PR and must not be imported implicitly. No live 3D terrain feed, full coordinated three-role mission, scientific model approval or final submission is claimed.

Jesús hands the reviewed package to the organizer at **20:00 America/Bogota, 15 November 2026**. Preserve stable main while isolated pilots continue before that cut. Explicit organizer endorsement of the exact package revision, any corrections and final submission receipt remain delivery gates; contact confirmation is not endorsement. No external notification or submission is performed by this review.

AI assistance for changed code/tests/docs and this software evidence is declared in `AI_USAGE.md`, `ai_usage.json` and the evidence manifest. No new media was generated here.

## Concurrent main refresh

Before authorized integration, main advanced to `798016eda88d33f4fdd8595e3328d091b4ba7308` through PR45. Preserve that terrain/menu/crop implementation and regenerated illustrative packages. Resolve the photo-tour button by keeping both the existing `endTour` behavior and main's per-zone `photoTourTitle`; retain both mandatory disclosure histories. The gateway client source remains the exact c8 SHA above and backend/interfaces remain unchanged. Rerun web checks and exact-head CI after this refresh.

The main45 refresh also exposed future geometry in recorder-backed runs: at map1, cell528 of recorded002 was displayed with the map2 +3 m contradiction before its observation (~4.1 s). Restrict final-story geometry to `illustrative === true` with source SIMULATION; all other runs use the current map version. Illustrative belief/sigma share their stable display shape, while recorded belief/sigma retain causal geometry. Preserve prior/NoData and all input bytes. The exact-package regression proves both sides of the change. This is a consumer correction, with no shared schema change or alteration of sealed evidence.
