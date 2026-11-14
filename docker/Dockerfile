# Development image: ROS 2 Jazzy (+ Gazebo Harmonic if the base has it) plus
# the Python web dependencies of mge_gateway.
#   docker build -t mge-dev --build-arg BASE=<jazzy image> docker/
ARG BASE=osrf/ros:jazzy-desktop-full
FROM ${BASE}
# Some base images default to a non-root user; apt needs root. scripts/dev.sh
# always runs the container as the calling host user.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-fastapi python3-uvicorn python3-websockets python3-httpx \
      python3-pytest python3-yaml python3-jsonschema \
    && rm -rf /var/lib/apt/lists/*
