# Web gateway scaffold

Owner: Jesus. R13/R15/R17/R18; F06; WebGateway/ReplayRecorder.

The FastAPI surface exists for `/api/health`, `/api/manifest`,
`/api/run/{run_id}/snapshot`, `/api/mission/goal` and WebSocket `/api/events`.
There is **no ROS executor, recorder, mission store or control forwarding yet**.
Health returns `NOT_READY` with `ros_connected=false`; all data/command routes
return HTTP 503 and events close with 1013. `mode`, map version and simulated time
are null without an active run. This inactive envelope is not LIVE or REPLAY.

After installing this package and its `requirements.txt`, use
`ros2 run mge_gateway gateway` (or `uvicorn mge_gateway.api:app --host 127.0.0.1`).
The service binds to loopback by default. Do not expose ROS control publicly
without authentication, origin restrictions and HTTPS/WSS design.

Next: typed JSON adapters, a ROS executor separated from the web event loop,
idempotent request/event handling, stale-response rejection and replay recording.
MissionManager remains the only authority of mission state and active routes.
A recorder must save manifest, timeline, snapshot and referenced rasters by run ID.

Validation: HTTP tests can verify 503/no invented state without ROS; real
message-to-route and replay tests remain pending. Maintainer contact and repository
license are placeholders awaiting a team decision.
