# PR44 corrected gateway to current TypeScript consumer

PASS five lifecycle groups plus terrain_meta pushed dynamically over the existing WebSocket before fallback. This is a replay-fed MOCK transport check, not a ROS graph, another mission, scientific approval or validated LIVE. Actual create_app/RunStore are imported from the corrected PR44 B checkout; TypeScript gatewayLive.ts is bundled directly from A. Public recorded-recovery-002 states/events/meta are unchanged. B restart identity is explicitly synthetic, cloned run_id only.

Frozen backend app SHA256: 3f2ceb9a674b496e79d057c822a0dabd43815bd70ee010ef8d8795277f150f61. Frozen TypeScript client SHA256: c8dfee78335621ba982597828306051f3802c1680bd711f68e8b5a8f4f60abd6. All five source hashes matched before/after.

Validated: 503 startup, canonical ROS-default IDLE and READY, true WS1-3-2 delivery, gap-safe cursor1, dynamic metadata2 and mission1 kept separate on the open socket, full-snapshot recovery, restart A to B, same-ID seq9/meta2 to IDLE0/meta1/events[] reset/cursor0, retired-handler isolation, exact negative XYZ/paths/ROS headers, MOCK provenance, 17 client GETs/four sockets/zero goals. Server stopped normally. The local Bridge feeds already serialized recorded payloads through the real RunStore/update hook; no claim is made of running RosBridge subscriptions or ROS conversion.

Reproduce from A, with existing web dependencies, local Python venv and the gateway-declared websockets package available in A/.local/pr39-consumer/python-deps:

1. Set MGE_PR44_BACKEND_ROOT to B repository root and MGE_PR44_CLIENT_ROOT to A repository root in terminal1. Run Python .local/pr44-review/consumer-fixed/producer.py with that venv.
2. Set MGE_PR44_CLIENT_ROOT to A in terminal2 and run node .local/pr44-review/consumer-fixed/consumer.mjs.

The harness expects this repository-relative installation and creates fresh cut-fixed-* outputs. Exact paths for the executed cut are in ready.json. These archived script copies are provenance, not portable root discovery. Producer uses a loopback ephemeral port and unique local command/ACK files. No mission goal or POST is sent.

Independent original-head review source and JUnit receipts are one level above consumer-fixed: source-lock.json pins ef8f3ac2b49505d1ddebe3fdc05d6b7f2e8605bf. Original tests110PASS+2ROSskips; independent loss regression1FAIL+XYZ/meta1PASS. All four new canary tests fail on original head; corrected B focal114PASS+2ROSskips, independent2PASS. ROS modules skipped locally; original-head CI43753188458 succeeded, which does not validate the unpublished fix.

AI disclosure: OpenAI Codex assisted with the ignored harness and descriptions. Source mission payloads remain unchanged public MOCK replay.
