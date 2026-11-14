"""HTTP contract surface with explicit unavailable responses until ROS integration."""

from fastapi import Body, FastAPI, WebSocket
from fastapi.responses import JSONResponse

SCHEMA_VERSION = "1.0.0"
app = FastAPI(title="MARS GODS EYE gateway", version="0.0.0")


def unavailable(run_id: str | None = None) -> dict:
    """Return no invented run, map, clock or mission state."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "mode": None,
        "map_version": None,
        "timestamp_sim_s": None,
        "status": "NOT_READY",
        "reason_code": "ROS_NOT_CONNECTED",
    }


@app.get("/api/health")
def health() -> dict:
    return {
        **unavailable(),
        "ros_connected": False,
        "implementation_status": "scaffold",
    }


@app.get("/api/manifest")
def manifest() -> JSONResponse:
    return JSONResponse(status_code=503, content=unavailable())


@app.get("/api/run/{run_id}/snapshot")
def snapshot(run_id: str) -> JSONResponse:
    return JSONResponse(status_code=503, content=unavailable(run_id))


@app.post("/api/mission/goal")
def set_goal(payload: dict = Body(...)) -> JSONResponse:
    # No commands are accepted or forwarded before a real ROS bridge exists.
    run_id = payload.get("run_id")
    return JSONResponse(
        status_code=503,
        content=unavailable(run_id if isinstance(run_id, str) else None),
    )


@app.websocket("/api/events")
async def events(socket: WebSocket) -> None:
    await socket.accept()
    await socket.send_json(unavailable())
    await socket.close(code=1013, reason="ROS integration is not connected")


def main() -> None:
    import uvicorn

    # Local-only by default; remote control requires an explicit deployment design.
    uvicorn.run(app, host="127.0.0.1", port=8000)
