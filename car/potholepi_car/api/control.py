"""
WebSocket driving channel.

Client -> car (JSON, one message per frame, ~10 Hz while driving):
    {"type": "drive",  "left": -1..1, "right": -1..1}
    {"type": "arcade", "throttle": -1..1, "steering": -1..1}
    {"type": "stop"}
    {"type": "ping"}
Car -> client:
    {"type": "ack"} for commands, {"type": "pong"} for ping,
    {"type": "error", "message": "..."} for bad input.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

router = APIRouter()


def _num(msg: dict, key: str) -> float:
    v = float(msg[key])
    if v != v:  # NaN
        raise ValueError(key)
    return v


@router.websocket("/ws/control")
async def control(ws: WebSocket):
    drive = ws.app.state.rt.drive
    await ws.accept()
    drive.client_connected()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
                kind = msg.get("type")
                if kind == "drive":
                    await run_in_threadpool(drive.drive, _num(msg, "left"), _num(msg, "right"))
                elif kind == "arcade":
                    await run_in_threadpool(drive.arcade, _num(msg, "throttle"), _num(msg, "steering"))
                elif kind == "stop":
                    await run_in_threadpool(drive.stop)
                elif kind == "ping":
                    drive.ping()
                    await ws.send_json({"type": "pong"})
                    continue
                else:
                    await ws.send_json({"type": "error", "message": f"unknown type {kind!r}"})
                    continue
                await ws.send_json({"type": "ack"})
            except (ValueError, KeyError, TypeError, AttributeError):
                await ws.send_json({"type": "error", "message": "invalid message"})
    except WebSocketDisconnect:
        pass
    finally:
        await run_in_threadpool(drive.client_disconnected)
