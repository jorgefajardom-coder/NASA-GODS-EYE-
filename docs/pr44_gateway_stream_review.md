# PR44 event-stream reconciliation — 15 November 2026

## Source and finding

Owner PR44 starts at `ef8f3ac2b49505d1ddebe3fdc05d6b7f2e8605bf` (`feat/integration`), including ef864ae/ef8f3ac. Reconcile current main `798016eda88d33f4fdd8595e3328d091b4ba7308` while preserving ancestry. These existing changes push TerrainMeta on WebSocket and document health/metadata fields; no ROS message/service, enum, unit or JSON schema1.0.0 is redefined. Integration review remains with Jesús; scientific approval and ICD freeze remain open.

P1 reproduced on the exact original producer: insert events1→3→2→4 while the socket stays open. The store accepts and snapshots [1,2,3,4], but the WebSocket emits [1,3,4]. The `seq <= sent` high-water filter incorrectly treats a unique late event as already sent. A healthy socket carrying other messages can hide the loss from a client indefinitely. Original CI was green because it lacked this case.

## Correction and verification

Keep `after_seq` as the fixed requested resume floor. A per-connection set records sequences actually emitted from the backlog or live queue; skip those exact duplicates, while preserving new late sequences above the original floor. Snapshot, raw XYZ, ROS headers, source labels, metadata versions and goal behavior remain unchanged.

Four real TestClient WebSocket regressions fail on the original producer and pass with the correction: open-stream1→3→2; backlog/queue overlap with a gap at cursor0/1; and a fixed cursor2 accepting late4 after5 while omitting1/2. Canary events make lost events fail assertions instead of blocking a test indefinitely.

- Focused producer/bridge/launch tests: **114 passed, 2 ROS skips**.
- Independent late-event/metadata/XYZ/source checks on corrected source: **2 passed**.
- Full native Python3.12.14: **1281 passed, 26 skipped**, one existing warning, with a unique local basetemp. ROS/platform/symlink skips are explicit.
- Actual frozen PR39 client SHA256`c8dfee78335621ba982597828306051f3802c1680bd711f68e8b5a8f4f60abd6` against corrected producer SHA256`3f2ceb9a674b496e79d057c822a0dabd43815bd70ee010ef8d8795277f150f61`: **five groups PASS**, 17 GET requests, 4 WebSockets, zero goal calls. Dynamic terrain metadata v2 is received on the same open socket while mission authority remains v1; 1→3→2, gap recovery, run replacement, same-ID reset and exact XYZ/headers/source are covered. Inputs are public replay-fed MOCK, with no new ROS graph. Bounded scripts/receipts retain the true dirty source HEAD plus exact hashes.
- Final exact-head CI, including Ubuntu24.04/Jazzy build/interfaces and integrations, must pass before merge. No new ROS mission is claimed from the native checks.

The corrected gateway client can consume terrain metadata independently of mission map authority; a transport connection never establishes a validated LIVE mission. Evidence and source hashes are preserved under `evidence/pr44-gateway-stream-20261115/` when published.

## Remaining gates and delivery

Explicit owner authorization precedes this PR's merge. Approval of PR39/42 does not automatically merge PR44. Preserve stable main and independent pilot evidence. Jesús hands the exact reviewed package to the organizer at20:00 America/Bogota on15 November; explicit endorsement of that revision and submission receipt remain pending delivery gates. No external organizer message or final submission is performed by this reconciliation.

Required AI-use text and metadata cover the changed code/tests/harness/docs, without optional authorship credits or scientific-result claims.
