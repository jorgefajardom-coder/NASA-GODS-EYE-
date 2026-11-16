# PR39 final real HTTP/WebSocket consumer check

PASS: five groups on the frozen TypeScript source c8dfee78335621ba982597828306051f3802c1680bd711f68e8b5a8f4f60abd6.

This is a replay-fed MOCK test using the actual unchanged mge_gateway.create_app/RunStore, uvicorn bound only to an ephemeral 127.0.0.1 port, Node 24 and native WebSocket. No ROS graph, mission service commands, POST requests, scientific acceptance or validated LIVE evidence. State/event/meta inputs come from the exact public recorded-recovery-002 package. Restart B explicitly clones run_id only, not another mission execution.

Verified: 503 startup; complete ROS-default IDLE and FEASIBLE READY payloads; actual WS arrival 1,3,2; contiguous cursor1 with a gap and snapshot recovery; actual meta2/mission1 kept separate; fresh application A to B; same-ID new RunStore seq9/meta2 to 503 to exact IDLE seq0/meta1/events[] with new WS after_seq0; an explicitly invoked retired socket handler cannot affect the fresh session; exact negative XYZ, route and ROS header preservation; MOCK labels; 17 client GET requests, four WebSocket connections and zero goal calls. Producer/client source hashes were equal before/after.

Reproduce from the checkout root with existing local Python/web dependencies, in two terminals (these scripts remain under .local/pr39-consumer):

```powershell
& 'C:\Users\User\Documents\ChatGPT\Hacktón NASA\.venv\Scripts\python.exe' -u '.local\pr39-consumer\producer-v2.py'
```

```powershell
node '.local\pr39-consumer\consumer-v2.mjs'
```

Each producer run creates a unique cut-2-* directory, recorded in active-output.json. Gateway-declared websockets was installed only under the harness python-deps directory; shared Python was unchanged. Controls and acknowledgements use unique files per command to avoid Windows replacement/read contention. The first second-cut attempt failed in this harness-only file replacement race, before same-ID validation, and is preserved in sibling cut-2-rx5ar7z9; it is not a product failure. An idle subsequent startup was stopped without running Node while waiting for final O2-source freeze. This directory is the final complete PASS cut.

ready.json locks source/package identities; consumer-report.json records assertions, GETs, socket URLs and state transitions; producer-report.json records actual ASGI requests and WebSocket payloads; actual-responses.json contains actual HTTP responses. validation.json independently checks readonly/source freeze and hashes these artifacts. Local server exited normally. The source tree had authorized uncommitted client fixes/merged main: HEAD alone is not the full tested source; use exact hashes.

AI disclosure: OpenAI Codex assisted with these local validation scripts and this description. Source mission records remain the unchanged public MOCK replay.
