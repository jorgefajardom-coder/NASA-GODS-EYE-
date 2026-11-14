#!/usr/bin/env bash
# Run a command inside the ROS 2 Jazzy container with the repository mounted.
#   scripts/dev.sh                      -> interactive shell
#   scripts/dev.sh colcon build ...     -> one command
# MGE_IMAGE selects the image; it must provide ROS 2 Jazzy (and Gazebo Harmonic
# for simulation work).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${MGE_IMAGE:-osrf/ros:jazzy-desktop-full}"
TTY=(); [ -t 0 ] && TTY=(-it)
if [ $# -eq 0 ]; then set -- bash; fi
exec docker run --rm "${TTY[@]}" \
  --user "$(id -u):$(id -g)" -e HOME=/tmp -e ROS_LOG_DIR=/tmp/ros_log \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}" \
  --network host -v "$ROOT":/ws -w /ws "$IMAGE" \
  bash -c 'source /opt/ros/jazzy/setup.bash; [ -f install/setup.bash ] && source install/setup.bash; exec "$@"' -- "$@"
