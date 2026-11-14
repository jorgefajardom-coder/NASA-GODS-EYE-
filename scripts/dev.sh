#!/usr/bin/env bash
# Run a command inside the ROS 2 Jazzy container with the repository mounted.
#   scripts/dev.sh                      -> interactive shell
#   scripts/dev.sh colcon build ...     -> one command
# Build the image once: docker build -t mge-dev docker/   (see docker/Dockerfile)
# MGE_IMAGE selects another image.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${MGE_IMAGE:-mge-dev}"
TTY=(); [ -t 0 ] && TTY=(-it)
if [ $# -eq 0 ]; then set -- bash; fi
exec docker run --rm "${TTY[@]}" \
  --user "$(id -u):$(id -g)" -e HOME=/tmp -e ROS_LOG_DIR=/tmp/ros_log \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}" \
  --network host -v "$ROOT":/ws -w /ws "$IMAGE" \
  bash -c 'source /opt/ros/jazzy/setup.bash; [ -f install/setup.bash ] && source install/setup.bash; exec "$@"' -- "$@"
