# Web gateway

Owner: Jesus. R13/R15/R17/R18; F06; WebGateway/ReplayRecorder.

`gateway` serves `/api/health`, `/api/manifest`, `/api/run/{run_id}/snapshot`,
`/api/run/{run_id}/events`, `POST /api/mission/goal` and WebSocket `/api/events`
over the ROS graph. The contract is in `docs/ICD.md`, section 6.

- `ros_bridge.py`: ROS node in its own executor thread. Subscriptions feed the
  store; goal requests are forwarded to `/mge/mission/set_goal`.
- `store.py`: thread-safe run state with the ordering rules. It drops data of
  another run, duplicate events and mission states older than the one held.
  No ROS imports.
- `app.py`: FastAPI application. No planning or mission logic.
- `replay.py`, `recorder.py`: `replay_recorder` writes a run as `manifest.json`,
  `timeline.jsonl` and `snapshot.json`; an existing run is never overwritten.
- `replay_check.py`: `check_replay <dir>` validates a package offline.

Until a mission state of the configured run arrives there is no active run:
health reports `NOT_READY` with `ros_connected=false`, data and command routes
return HTTP 503, and the event stream closes with 1013. `mode`, map version and
simulated time are null. A running process alone is never LIVE.

Run with `ros2 run mge_gateway gateway --ros-args -p run_id:=<id>`. Parameters:
`run_id`, `host` (default `127.0.0.1`), `port` (default `8000`),
`cors_origins`. The service binds to loopback by default. If the environment
variable `MGE_CONTROL_TOKEN` is set, `POST` requires
`Authorization: Bearer <token>`. Do not expose ROS control publicly without
that token, origin restrictions and an HTTPS/WSS design.

MissionManager remains the only authority of mission state and active routes.

Validation: `tests/contracts/test_gateway.py` and `tests/unit` run without ROS.
`tests/integration` runs the ROS-to-HTTP flow and the recorder against the MOCK
producers of `mge_sim`; that is integration plumbing, not a validated mission.
Pending: rasters in the replay package, Gazebo `/clock`, and a web client.
Maintainer contact and repository license are placeholders awaiting a team
decision.
