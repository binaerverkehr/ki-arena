"""WebSocket route for live debate progress updates."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.routers.api import register_ws, unregister_ws

router = APIRouter()


@router.websocket("/ws/debate/{debate_id}")
async def debate_ws(websocket: WebSocket, debate_id: str):
    await websocket.accept()
    register_ws(debate_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        unregister_ws(debate_id, websocket)
    except Exception:
        unregister_ws(debate_id, websocket)
