# PR39 gateway contract: bounded public consumer evidence

**PASS: five consumer groups. Replay-fed MOCK; no ROS graph or mission commands.**
This records the actual unchanged Python `mge_gateway.app.create_app`
and `RunStore` serving real loopback HTTP/WebSocket, consumed by the corrected
TypeScript client. It is a software check, not a new mission execution,
three-role acceptance, scientific approval or validated LIVE evidence. Source
payloads come from the already public
[recorded-recovery-002](../../web/public/replay/recorded-recovery-002/manifest.json).

The frozen client SHA-256 is
`c8dfee78335621ba982597828306051f3802c1680bd711f68e8b5a8f4f60abd6`.
The tested checkout had HEAD `8ed14b796bcf5de261b719f8dc8c68a8b1ed7ffe`
**plus uncommitted authorized changes**. That HEAD alone does not reproduce
this cut. Identify the tested code by the exact source hashes in
[manifest.json](manifest.json) and [validation.json](validation.json).
The backend was unchanged. This export introduces no shared runtime/schema version.

## What passed

- Actual HTTP 503 startup, canonical ROS-default initial IDLE route, then the
  complete recorded FEASIBLE READY state.
- Actual WebSocket arrival 1 -> 3 -> 2, preserving complete logical history.
- Gap [1,3] uses contiguous after_seq=1; full-snapshot fallback recovers event 2.
- Recorded terrain metadata v2 and lagging mission v1 remain distinct:
  terrainVersion=2, mission.map_version=1.
- Application A -> B clears A and rediscovers B. B explicitly clones only
  run_id of the public payloads; it is a synthetic test identity, not another mission.
- Same-ID new RunStore resets sequence9/metadata2 to exact IDLE/sequence0/
  metadata1/events[], with next WebSocket cursor0. An invoked retired socket
  callback cannot mutate the fresh session.
- Negative absolute XYZ, full routes and original ROS frame/sec/nanosec headers
  compare exactly to source records. MOCK labels remain.
- 17 client GETs, four WebSocket connections, zero goal calls, unchanged
  producer/client hashes before/after, and normal local-server shutdown.

## Export integrity

Validation and its seven artifacts are copied **byte for byte**. Original names
map explicitly in the manifest: README.md -> [original-README.md](original-README.md),
and producer-v2.py/consumer-v2.mjs -> [scripts/](scripts/). Historical validation
hashes refer to those original bytes, not this new public README. Preserve
sealed files without normalizing formatting, paths or historical text.

- [ready.json](ready.json): producer/client and public-package hashes.
- [consumer-report.json](consumer-report.json): assertions, GETs, socket URLs, state history.
- [producer-report.json](producer-report.json): actual ASGI requests and WS payloads.
- [actual-responses.json](actual-responses.json): actual HTTP responses.
- [scripts/producer-v2.py](scripts/producer-v2.py) and
  [scripts/consumer-v2.mjs](scripts/consumer-v2.mjs): exact harness source.

No installed dependencies, venv, node_modules, bundles, caches, private inputs,
raw frames, evaluator reference or earlier failed outputs are exported.
The sealed original README mentions a Windows ACK-file contention and canceled
idle startup; neither is claimed as a product failure or a successful run.

Verify every exported payload from the repository root:

```powershell
@'
import hashlib, json
from pathlib import Path
p = Path('evidence/pr39-gateway-contract-20261115')
m = json.loads((p / 'manifest.json').read_text(encoding='utf-8'))
actual = {f.relative_to(p).as_posix() for f in p.rglob('*') if f.is_file()}
assert actual == set(m['files']) | {'manifest.json'}
for name, expected in m['files'].items():
    data = (p / name).read_bytes()
    assert len(data) == expected['bytes'], name
    assert hashlib.sha256(data).hexdigest() == expected['sha256'], name
print('PASS: all exported payload hashes')
'@ | python -
```

## Reproduce on Windows from matching source

The scripts depend deliberately on the repository-relative
`.local/pr39-consumer` location and the existing web source/package layout.
**Do not run the archived scripts inside this evidence directory.** Install
copies at the required local path. Run these PowerShell commands from the
repository root with Python3.12 and the Node24 version pinned by web/.nvmrc.
The validated versions were Python3.12.14 and Node24.18.0 on Windows11;
portability to other platforms/layouts is not established here.

Create a local venv and install declared dependencies with repository constraints.
Websockets17.4 was used for this cut and satisfies gateway's declared >=10.4:

```powershell
python --version
node --version
New-Item -ItemType Directory -Force '.local/pr39-consumer' | Out-Null
Copy-Item -LiteralPath 'evidence/pr39-gateway-contract-20261115/scripts/producer-v2.py' -Destination '.local/pr39-consumer/producer-v2.py'
Copy-Item -LiteralPath 'evidence/pr39-gateway-contract-20261115/scripts/consumer-v2.mjs' -Destination '.local/pr39-consumer/consumer-v2.mjs'
python -m venv '.local/pr39-consumer/venv'
& '.local/pr39-consumer/venv/Scripts/python.exe' -m pip install -r requirements-dev.txt -r src/mge_gateway/requirements.txt 'websockets==17.4'
npm.cmd --prefix web ci
```

Confirm the checkout matches every source_sha256 and public_package_sha256 in
the receipt before calling a rerun a same-source comparison. Newer source
constitutes a new validation cut.

Terminal1 starts only the local replay-fed gateway:

```powershell
& '.local/pr39-consumer/venv/Scripts/python.exe' -u '.local/pr39-consumer/producer-v2.py'
```

After it prints an ephemeral 127.0.0.1 address, run in terminal2:

```powershell
node '.local/pr39-consumer/consumer-v2.mjs'
```

Each producer run creates a unique .local/pr39-consumer/cut-2-* directory,
recorded in active-output.json. Node bundles current TypeScript with the web
project's existing esbuild, uses native WebSocket and stops the local server.
It retains new consumer/producer reports and HTTP responses without modifying
this export. The sealed validation.json is an independent post-check of this
cut, not an automatically regenerated claim for a rerun. Test control/ACK
commands use unique local files outside the gateway API. No goal endpoint is called.

## AI disclosure

OpenAI Codex assisted with the local harness and descriptions; validation.json,
ready.json and manifest.json retain corresponding metadata. This export copies
existing public MOCK records and adds prose/manifest, not NASA observations
or an AI authorship credit.
