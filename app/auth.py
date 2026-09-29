import asyncio
import json

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.config import BACKEND_SHARED_KEY

AUTH_TIMEOUT_SECONDS = 10


async def authenticate(websocket: WebSocket) -> bool:
    """Wait for the first client message and validate it as an auth
    handshake. Returns True if the connection should proceed, False if it
    was rejected (the caller is responsible for closing the socket)."""
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS
        )
    except (asyncio.TimeoutError, WebSocketDisconnect):
        return False

    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        return False

    if not isinstance(message, dict) or message.get("type") != "auth":
        return False

    return message.get("key") == BACKEND_SHARED_KEY
