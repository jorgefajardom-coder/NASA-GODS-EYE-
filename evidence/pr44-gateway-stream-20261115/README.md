# PR44 gateway stream: bounded red/green consumer evidence

**Corrected source PASS. Replay-fed MOCK software validation; no ROS mission.**
The original PR44 head ef8f3ac2b49505d1ddebe3fdc05d6b7f2e8605bf discarded a
late event2 after event3. The store retained [1,2,3,4], while its WebSocket
sent [1,3,4]. The correction keeps the requested after_seq floor fixed and
deduplicates sequences actually emitted through backlog or queue.

Frozen corrected app SHA-256:
3f2ceb9a674b496e79d057c822a0dabd43815bd70ee010ef8d8795277f150f61.
Current TypeScript client SHA-256:
c8dfee78335621ba982597828306051f3802c1680bd711f68e8b5a8f4f60abd6.
The tested backend had authorized uncommitted changes and a merge in progress;
its historical HEAD alone is not the corrected source. Exact hashes, source
roots and original Git blobs are recorded in [manifest.json](manifest.json),
[review/source-lock.json](review/source-lock.json) and
[consumer/ready.json](consumer/ready.json).

## Results and limits

- Original existing tests: 110 passed, two ROS-dependent modules skipped.
- Independent original regression: expected one failure (event2 lost), one
  coordinate/metadata/provenance check passed.
- Four new bounded TestClient cases fail on the original source, using later
  marker events to detect loss without hanging: live1/3/2, backlog/queue
  overlap at cursors0/1, and a fixed cursor2 with late4 after5.
- Corrected focal command: 114 passed, two ROS-dependent modules skipped.
  A separate focused JUnit was not retained; the command/output were inspected.
- Independent corrected regression: both tests passed.
- Actual corrected Python create_app/RunStore -> current TypeScript client:
  five lifecycle groups passed, plus terrain_meta2 delivered dynamically over
  the existing WebSocket while the authoritative mission remained v1.
- Actual WebSocket1/3/2 delivery, gap-safe cursor and snapshot fallback,
  restartA->B, same-ID seq9/meta2 -> IDLE0/meta1/events[] reset, retired-callback
  isolation, exact negative XYZ/routes/ROS headers and MOCK labels all passed.
- 17 client GETs, four WebSockets, zero goal calls; source hashes matched
  before/after. The ephemeral loopback server exited normally.

The original-head CI run43753188458 succeeded despite the uncovered regression:
[CI original head](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/actions/runs/43753188458).
It does not validate the unpublished corrected source. Root separately ran the
full corrected Python suite (1281 passed,26 skipped); its larger local log/JUnit
are not included in this bounded export.

ROS subscriptions, generated interfaces and launch were not executed by this
local consumer harness. A small test Bridge feeds already serialized public
recorded payloads through the real gateway store/update hook. Inputs come only
from public recorded-recovery-002. RestartB explicitly clones run_id; it is not
another mission execution. This establishes no scientific, three-role or
validated LIVE acceptance. No mission goal endpoint or POST is called.

## Preserved files

[consumer/validation.json](consumer/validation.json) and its seven artifacts
are copied byte for byte. Original README.md is preserved as
[consumer/original-README.md](consumer/original-README.md); scripts are under
[consumer/scripts/](consumer/scripts/). Manifest maps original names explicitly
and retains all original byte counts/hashes. Do not normalize sealed text.

The review folder contains original/fixed reproduction JSON, exact original
Git source lock, source-verified original-suite JUnit, the four-red-case JUnit,
final independent test source and both red/green JUnit files. Review summary
states which source and outcome each receipt represents. Original-red results
are intentionally failing tests, not claimed successes.

No venv, installed dependency, node_modules, bundle, browser profile/cache,
private input, evaluator reference or raw media frame is included. HTTP/WS
payloads are only the small recorded public state/event/metadata test subset.

## Reproduce the cross-language consumer on Windows

Validated versions: Python3.12.14 and Node24.18.0. Use the Node version pinned
by web/.nvmrc. These are PowerShell instructions. Preserve an existing evidence
cut; run new work in an ignored local harness.

A is a checkout containing the exact c8 client. B contains the exact corrected
3f backend. They may be the same checkout only when both hashes match.
Set these explicit roots to your local paths:

~~~powershell
$reviewA = 'C:\path\to\client-checkout'
$reviewB = 'C:\path\to\corrected-backend-checkout'
$packet = Join-Path $reviewB 'evidence\pr44-gateway-stream-20261115'
$harness = Join-Path $reviewA '.local\pr44-review\consumer-fixed'
New-Item -ItemType Directory -Force $harness | Out-Null
Copy-Item -LiteralPath (Join-Path $packet 'consumer\scripts\producer.py') -Destination (Join-Path $harness 'producer.py')
Copy-Item -LiteralPath (Join-Path $packet 'consumer\scripts\consumer.mjs') -Destination (Join-Path $harness 'consumer.mjs')
python -m venv (Join-Path $reviewA '.local\pr44-review\venv')
$reviewPython = Join-Path $reviewA '.local\pr44-review\venv\Scripts\python.exe'
& $reviewPython -m pip install -r (Join-Path $reviewB 'requirements-dev.txt') -r (Join-Path $reviewB 'src\mge_gateway\requirements.txt') 'websockets==17.4'
npm.cmd --prefix (Join-Path $reviewA 'web') ci
~~~

The script explicitly receives both roots through environment variables. Its
HARNESS directory holds active-output.json and unique cut-fixed-* outputs;
do not execute archived copies inside this sealed evidence directory. The
original local run also used websockets17.4 from A/.local/pr39-consumer/python-deps;
that optional lookup is harmless when absent because the new venv supplies it.

In terminal1:

~~~powershell
$env:MGE_PR44_BACKEND_ROOT = $reviewB
$env:MGE_PR44_CLIENT_ROOT = $reviewA
& $reviewPython -u (Join-Path $harness 'producer.py')
~~~

After it prints an ephemeral 127.0.0.1 address, set A/harness variables in
terminal2 as above, then run:

~~~powershell
$env:MGE_PR44_CLIENT_ROOT = $reviewA
node (Join-Path $harness 'consumer.mjs')
~~~

The Node runner bundles the current client from A with A's existing esbuild
and uses native HTTP/WebSocket. It ends the local server and retains new
reports/responses. It does not regenerate the sealed independent validation
receipt or modify this export. Confirm all source/package hashes before
calling a rerun the same-source comparison.

## Reproduce independent red/green tests

The archived independent test intentionally expects installation under
A/.local/pr44-review, where it reads A's public recorded-recovery-002.
Install the test/config/source-lock and extract only the original gateway:

~~~powershell
$localReview = Join-Path $reviewA '.local\pr44-review'
Copy-Item -LiteralPath (Join-Path $packet 'review\test_review_regressions.py') -Destination (Join-Path $localReview 'test_review_regressions.py')
Copy-Item -LiteralPath (Join-Path $packet 'review\pytest.ini') -Destination (Join-Path $localReview 'pytest.ini')
Copy-Item -LiteralPath (Join-Path $packet 'review\source-lock.json') -Destination (Join-Path $localReview 'source-lock.json')
$originalZip = Join-Path $localReview 'original.zip'
git -C $reviewB archive --format=zip "--output=$originalZip" ef8f3ac2b49505d1ddebe3fdc05d6b7f2e8605bf src/mge_gateway
Expand-Archive -LiteralPath (Join-Path $localReview 'original.zip') -DestinationPath (Join-Path $localReview 'source')
$env:MGE_PR44_CLIENT_ROOT = $reviewA
$env:MGE_PR44_TEST_SOURCE = Join-Path $localReview 'source'
~~~

Run this loader to verify the imported source explicitly and avoid the root
pytest config's injection of a different current-checkout module:

~~~powershell
@'
import os, sys
from pathlib import Path
import pytest
a = Path(os.environ['MGE_PR44_CLIENT_ROOT'])
s = Path(os.environ['MGE_PR44_TEST_SOURCE'])
sys.path.insert(0, str(s / 'src/mge_gateway'))
import mge_gateway.app
assert Path(mge_gateway.app.__file__).resolve() == s / 'src/mge_gateway/mge_gateway/app.py'
raise SystemExit(pytest.main(['-c', str(a / '.local/pr44-review/pytest.ini'), str(a / '.local/pr44-review/test_review_regressions.py'), '-q', '-p', 'no:cacheprovider']))
'@ | & $reviewPython -
~~~

Original source should fail the event-loss test and pass XYZ/meta. Set
MGE_PR44_TEST_SOURCE to B and rerun the same loader: both should pass.

The corrected focal command, from B with its repository test environment, is:

~~~powershell
& $reviewPython -m pytest tests/contracts/test_gateway.py tests/contracts/test_gateway_bridge.py tests/unit/test_store.py tests/contract/test_mission_launch.py -q -p no:cacheprovider
~~~

## Verify export and AI disclosure

Every exported payload except manifest.json itself is byte-hashed under
manifest.files. Recompute its byte count and SHA256, and reject missing/extra
files. Manifest also maps all eight sealed consumer originals to public paths.

OpenAI Codex assisted with the local validation/test harness, descriptions and
bounded export manifest. Corresponding metadata is retained. Recorded input
payloads remain unchanged public MOCK data; no NASA observation is generated
or relabelled, and no optional AI authorship credit is asserted.
