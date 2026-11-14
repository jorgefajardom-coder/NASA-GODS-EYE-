#!/usr/bin/env bash
# Target-platform contract evidence only; not full mission or physical validation.
set -eo pipefail
source_root=$(cd "$(dirname "$0")/.." && pwd)
# rosidl/CMake path handling is unsafe with this checkout's spaces/non-ASCII.
# Copy only the tested source inputs to a fresh, explicit ASCII temp workspace.
workspace=$(mktemp -d /tmp/mge-contract-baseline-XXXXXX)
printf 'Source: %s\nTarget validation workspace: %s\n' "$source_root" "$workspace"
tar -C "$source_root" --exclude=__pycache__ --exclude=.pytest_cache -cf - src tests docs data scripts pyproject.toml | tar -C "$workspace" -xf -
cd "$workspace"
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
for name in TerrainMeta TerrainObservation AgentState MissionEvent MissionState RouteDecision; do
  ros2 interface show mge_interfaces/msg/$name
done
ros2 interface show mge_interfaces/srv/PlanRoute
ros2 interface show mge_interfaces/srv/SetMissionGoal
mkdir -p .local
python3 -m pytest tests/contract tests/integration -q --basetemp .local/ros-pytest
