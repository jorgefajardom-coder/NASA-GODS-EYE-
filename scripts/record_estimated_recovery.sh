#!/usr/bin/env bash
# Run in a built/sourced Ubuntu 24.04 / ROS 2 Jazzy checkout. Never overwrite a cut.
set -eo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
if [ "$#" -ne 1 ] || [ -e "$1" ]; then
  echo 'Usage: scripts/record_estimated_recovery.sh NEW_OUTPUT_DIRECTORY' >&2
  exit 2
fi
mkdir -p "$1"
output=$(cd "$1" && pwd)
export MGE_RECORDING_OUTPUT="$output"
python - <<'PY'
import hashlib, json, os, pathlib, subprocess
root = pathlib.Path.cwd()
revision = os.environ.get('MGE_SOURCE_COMMIT')
dirty = os.environ.get('MGE_SOURCE_DIRTY', 'true') == 'true'
if not revision:
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip())
paths = []
for directory in ('src', 'config', 'scripts', 'tests'):
    paths += [p for p in (root/directory).rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix != '.pyc']
paths += [root/p for p in ('pyproject.toml', 'requirements-dev.lock.txt',
          'data/sample/manifest.json', 'data/sample/terrain.npz',
          'data/sample/provenance_details.json')]
record = dict(source_commit=revision, source_has_uncommitted_changes=dirty,
    source_sha256={str(p.relative_to(root)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(set(paths))},
    command='python -m pytest tests/integration/test_estimated_exploration.py -q',
    source_mode='MOCK', scope='Real public data/mapping/planner; MOCK mission and kinematic human; robots idle',
    scientific_mission_complete=False,
    ai_assistance={'tool': 'OpenAI Codex', 'use': 'Code, tests and deterministic SIMULATED observation; no NASA local measurement'})
(pathlib.Path(os.environ['MGE_RECORDING_OUTPUT'])/'source-lock.json').write_text(json.dumps(record, indent=2)+'\n')
PY
set +e
python -m pytest tests/integration/test_estimated_exploration.py -q \
  --basetemp "$output/pytest" --junitxml="$output/integration.junit.xml" > "$output/command.log" 2>&1
result=$?
set -e
cat "$output/command.log"
if [ "$result" -ne 0 ]; then
  exit "$result"
fi
python - <<'PY'
import hashlib, json, os, pathlib, shutil
from mge_gateway.replay_check import check_package
output = pathlib.Path(os.environ['MGE_RECORDING_OUTPUT'])
packages = sorted({p.resolve() for p in (output/'pytest').glob('estimated-replay*/it-execution')})
if len(packages) != 1:
    raise SystemExit(f'Expected one exact recorder package, found {len(packages)}')
package = packages[0]
problems = check_package(package)
if problems:
    raise SystemExit(str(problems))
shutil.copytree(package, output/'package')
shutil.copyfile(package.parent/'estimated-run-result.json', output/'estimated-run-result.json')
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.iterdir()) if p.is_file()}
(output/'package-sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
print('Closed and checked exact MOCK recorder package:', output/'package')
PY
