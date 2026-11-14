"""Web side of the gateway. Translates the RunStore to versioned JSON; it
holds no planning or mission logic and never exposes DDS to the browser."""
import asyncio
import hmac
import math
import os
from typing import Literal, Optional
import uuid

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class PointIn(BaseModel):
    x: float
    y: float
    z: float = 0.0


class GoalIn(BaseModel):
    request_id: Optional[str] = Field(None, description='Idempotency key; generated if absent.')
    primary_agent_id: str
    base: PointIn
    goal: PointIn
    mode: Literal['FAST', 'EFFICIENT', 'SAFE'] = 'FAST'
    time_budget_s: float
    energy_budget_wh: float
    oxygen_budget_l: float = math.nan
    reserve_time_s: float = 0.0
    reserve_wh: float = 0.0
    reserve_oxygen_l: float = 0.0


def create_app(bridge):
    """`bridge` provides: store, now_s(), set_goal(fields), on_update,
    cors_origins."""
    app = FastAPI(title='Mars Gods Eye gateway', version='0.1.0')
    app.add_middleware(
        CORSMiddleware, allow_origins=list(bridge.cors_origins),
        allow_methods=['GET', 'POST'], allow_headers=['*'])
    store = bridge.store
    control_token = os.environ.get('MGE_CONTROL_TOKEN', '')
    clients = set()

    def envelope(**payload):
        return store.envelope(bridge.now_s(), **payload)

    @app.on_event('startup')
    async def startup():
        loop = asyncio.get_running_loop()

        def fan_out(kind, payload):
            message = envelope(type=kind, **{kind: payload})
            for queue in list(clients):
                queue.put_nowait(message)

        # Called from the ROS thread; hand over to the web event loop.
        bridge.on_update = lambda kind, payload: loop.call_soon_threadsafe(
            fan_out, kind, payload)

    def require_run(run_id):
        if run_id != store.run_id:
            raise HTTPException(404, f'Unknown run {run_id!r}; current run is {store.run_id!r}.')

    @app.get('/api/health')
    def health():
        return envelope(status='ok', mission_state_received=store.state() is not None,
                        terrain_meta_received=store.meta() is not None)

    @app.get('/api/manifest')
    def manifest():
        state = store.state()
        return envelope(
            terrain_meta=store.meta(),
            agents=[{'agent_id': a['agent_id'], 'agent_kind': a['agent_kind']}
                    for a in (state['agents'] if state else [])],
            endpoints={
                'snapshot': f'/api/run/{store.run_id}/snapshot',
                'events': f'/api/run/{store.run_id}/events',
                'goal': '/api/mission/goal',
                'websocket': '/api/events',
            })

    @app.get('/api/run/{run_id}/snapshot')
    def snapshot(run_id: str):
        require_run(run_id)
        return envelope(mission_state=store.state(), terrain_meta=store.meta(),
                        events=store.events())

    @app.get('/api/run/{run_id}/events')
    def events(run_id: str, after_seq: int = 0):
        """Polling fallback for clients whose WebSocket fails."""
        require_run(run_id)
        return envelope(events=store.events(after_seq))

    @app.post('/api/mission/goal')
    def set_goal(body: GoalIn, authorization: str = Header('')):
        if control_token and not hmac.compare_digest(
                authorization, f'Bearer {control_token}'):
            raise HTTPException(401, 'Missing or invalid control token.')
        fields = body.dict()
        fields['request_id'] = fields['request_id'] or uuid.uuid4().hex
        answer = bridge.set_goal(fields)
        if answer is None:
            raise HTTPException(503, 'Mission service is not available.')
        return envelope(**answer)

    @app.websocket('/api/events')
    async def ws_events(ws: WebSocket, after_seq: int = 0):
        await ws.accept()
        queue = asyncio.Queue()
        clients.add(queue)
        try:
            for event in store.events(after_seq):
                await ws.send_json(envelope(type='event', event=event))
            if store.state():
                await ws.send_json(envelope(type='state', state=store.state()))
            while True:
                await ws.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            clients.discard(queue)

    return app
