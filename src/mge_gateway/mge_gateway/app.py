"""Web side of the gateway. Translates the RunStore to versioned JSON; it
holds no planning or mission logic and never exposes DDS to the browser.

Until a mission state of the configured run has been received there is no
active run: reads and commands answer 503 with an envelope whose run, mode,
map version and time are null. A running process alone is never LIVE.
"""
import asyncio
from contextlib import asynccontextmanager
import hmac
import math
import os
from typing import Literal, Optional
import uuid

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, confloat

from mge_gateway.store import to_json, unavailable

NO_ACTIVE_RUN = 'NO_ACTIVE_RUN'

# Match float64 geometry and float32 resource fields on the existing ROS wire.
FiniteCoordinate = confloat(allow_inf_nan=False)
ResourceValue = confloat(ge=0, le=3.4028234663852886e38, allow_inf_nan=False)


class PointIn(BaseModel):
    x: FiniteCoordinate
    y: FiniteCoordinate
    z: FiniteCoordinate = 0.0


class GoalIn(BaseModel):
    request_id: Optional[str] = Field(None, description='Idempotency key; generated if absent.')
    primary_agent_id: str
    base: PointIn
    goal: PointIn
    mode: Literal['FAST', 'EFFICIENT', 'SAFE'] = 'FAST'
    time_budget_s: ResourceValue
    energy_budget_wh: ResourceValue
    # Preserve the omitted-oxygen ROS sentinel; explicitly supplied values
    # must be finite. Mission remains responsible for agent applicability.
    oxygen_budget_l: ResourceValue = math.nan
    reserve_time_s: ResourceValue = 0.0
    reserve_wh: ResourceValue = 0.0
    reserve_oxygen_l: ResourceValue = 0.0


def create_app(bridge):
    """`bridge` provides: store, now_s(), set_goal(fields), on_update,
    cors_origins."""
    store = bridge.store
    control_token = os.environ.get('MGE_CONTROL_TOKEN', '')
    clients = set()

    @asynccontextmanager
    async def lifespan(_app):
        loop = asyncio.get_running_loop()

        def fan_out(kind, payload):
            message = envelope(type=kind, **{kind: payload})
            for queue in list(clients):
                queue.put_nowait(message)

        # Called from the ROS thread; hand over to the web event loop.
        bridge.on_update = lambda kind, payload: loop.call_soon_threadsafe(
            fan_out, kind, payload)
        yield
        bridge.on_update = None

    app = FastAPI(title='Mars Gods Eye gateway', version='0.2.0', lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=list(bridge.cors_origins),
        allow_methods=['GET', 'POST'], allow_headers=['*'])

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, error):
        # Pydantic may include the rejected NaN/inf in its error details.
        # Keep FastAPI's standard 422 shape without invalid JSON numbers.
        return JSONResponse(status_code=422, content={
            'detail': to_json(jsonable_encoder(error.errors())),
        })

    def active():
        return store.state() is not None

    def envelope(**payload):
        return store.envelope(bridge.now_s(), **payload)

    def not_ready(run_id=None):
        return JSONResponse(status_code=503, content=unavailable(NO_ACTIVE_RUN, run_id))

    def require_run(run_id):
        if run_id != store.run_id:
            raise HTTPException(404, f'Unknown run {run_id!r}; current run is {store.run_id!r}.')

    @app.get('/api/health')
    def health():
        flags = {'ros_connected': active(), 'terrain_meta_received': store.meta() is not None}
        if not active():
            return {**unavailable(NO_ACTIVE_RUN), **flags}
        return envelope(status='READY', **flags)

    @app.get('/api/manifest')
    def manifest():
        if not active():
            return not_ready()
        return envelope(
            terrain_meta=store.meta(),
            agents=[{'agent_id': a['agent_id'], 'agent_kind': a['agent_kind']}
                    for a in store.state()['agents']],
            endpoints={
                'snapshot': f'/api/run/{store.run_id}/snapshot',
                'events': f'/api/run/{store.run_id}/events',
                'goal': '/api/mission/goal',
                'websocket': '/api/events',
            })

    @app.get('/api/run/{run_id}/snapshot')
    def snapshot(run_id: str):
        if not active():
            return not_ready(run_id)
        require_run(run_id)
        return envelope(mission_state=store.state(), terrain_meta=store.meta(),
                        events=store.events())

    @app.get('/api/run/{run_id}/events')
    def events(run_id: str, after_seq: int = 0):
        """Polling fallback for clients whose WebSocket fails."""
        if not active():
            return not_ready(run_id)
        require_run(run_id)
        return envelope(events=store.events(after_seq))

    @app.post('/api/mission/goal')
    def set_goal(body: GoalIn, authorization: str = Header('')):
        if control_token and not hmac.compare_digest(
                authorization, f'Bearer {control_token}'):
            raise HTTPException(401, 'Missing or invalid control token.')
        if not active():
            return not_ready()
        fields = body.model_dump() if hasattr(body, 'model_dump') else body.dict()
        fields['request_id'] = fields['request_id'] or uuid.uuid4().hex
        answer = bridge.set_goal(fields)
        if answer is None:
            return JSONResponse(status_code=503, content=unavailable(
                'MISSION_SERVICE_UNAVAILABLE', store.run_id, status='ERROR'))
        return envelope(**answer)

    @app.websocket('/api/events')
    async def ws_events(ws: WebSocket, after_seq: int = 0):
        await ws.accept()
        if not active():
            await ws.send_json(unavailable(NO_ACTIVE_RUN))
            await ws.close(code=1013, reason='No active run')
            return
        queue = asyncio.Queue()
        clients.add(queue)

        async def pump():
            for event in store.events(after_seq):
                await ws.send_json(envelope(type='event', event=event))
            await ws.send_json(envelope(type='state', state=store.state()))
            while True:
                await ws.send_json(await queue.get())

        # Sending alone never notices a client that left while the run is
        # quiet, so the socket is also read: a disconnect ends the stream.
        sender = asyncio.create_task(pump())
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()
            clients.discard(queue)

    return app
