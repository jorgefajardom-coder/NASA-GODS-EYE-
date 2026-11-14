#!/usr/bin/env bash
# Build a source snapshot on Linux; install requirements-dev.txt in the active
# Python environment first. rosidl does not support every Windows path.
set -eo pipefail

mission_repository_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p -- "$mission_repository_root/tmp"
mission_validation_log=$(mktemp "$mission_repository_root/tmp/mission-ros.XXXXXX.log")
exec > >(tee "$mission_validation_log") 2>&1
printf 'VALIDATION_LOG=%s\n' "$mission_validation_log"
mission_validation_root=$(mktemp -d /tmp/mge-mission-jazzy.XXXXXX)
printf 'VALIDATION_ROOT=%s\n' "$mission_validation_root"
tar -C "$mission_repository_root" --exclude=__pycache__ --exclude=.pytest_cache \
  -cf - src config tests docs scripts pyproject.toml | tar -C "$mission_validation_root" -xf -
# Copy explicit public inputs only; never mount/copy evaluator reference assets.
mkdir -p -- "$mission_validation_root/data"
cp -a -- "$mission_repository_root/data/dataset.schema.json" \
  "$mission_repository_root/data/manifest.schema.json" \
  "$mission_repository_root/data/sample" "$mission_repository_root/data/planner_provisional" \
  "$mission_validation_root/data/"
cd -- "$mission_validation_root"
python3 - "$mission_validation_log.source.json" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path.cwd()
paths = [root / "pyproject.toml"]
for directory in ("src", "config", "tests", "docs", "scripts", "data"):
    paths.extend(path for path in (root / directory).rglob("*")
                 if path.is_file() and "__pycache__" not in path.parts
                 and path.suffix != ".pyc")
record = {"kind": "software_source_hashes", "scientific_result": False,
          "sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted(paths)}}
Path(sys.argv[1]).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
PY

# Retain the snapshot and build logs for inspection, including failed runs.
source /opt/ros/jazzy/setup.bash
mission_python=${MGE_PYTHON_EXECUTABLE:-$(command -v python3)}
"$mission_python" "$(command -v colcon)" build --symlink-install \
  --cmake-args -DPython3_EXECUTABLE="$mission_python"
source install/setup.bash
for mission_interface in TerrainMeta TerrainObservation AgentState MissionEvent MissionState RouteDecision; do
  ros2 interface show "mge_interfaces/msg/$mission_interface" >> checked_interfaces.txt
done
ros2 interface show mge_interfaces/srv/PlanRoute >> checked_interfaces.txt
ros2 interface show mge_interfaces/srv/SetMissionGoal >> checked_interfaces.txt
printf 'Inspected six messages and two services.\n'
ROS_DOMAIN_ID="${MGE_TEST_ROS_DOMAIN_ID:-83}" "$mission_python" -m pytest tests/mission tests/contract tests/integration -q \
  --tb=short --junitxml="$mission_validation_log.junit.xml"
