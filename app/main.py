import asyncio
import base64
import json
import logging

from fastapi import FastAPI, WebSocket
from google.genai import errors as genai_errors
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.auth import authenticate
from app.gemini import (
    live_session,
    receive_transcriptions,
    send_audio_chunk,
    send_audio_stream_end,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("transcribe-live-backend")

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/live-translate")
async def live_translate(websocket: WebSocket):
    await websocket.accept()

    if not await authenticate(websocket):
        await websocket.close(code=4401)
        return

    try:
        async with live_session() as session:
            await websocket.send_text(json.dumps({"type": "ready"}))

            forward_task = asyncio.create_task(
                _forward_transcriptions(session, websocket)
            )
            try:
                await _pump_client_audio(websocket, session)
            finally:
                forward_task.cancel()
                try:
                    await forward_task
                except asyncio.CancelledError:
                    pass
    except WebSocketDisconnect:
        pass
    except genai_errors.APIError as err:
        logger.exception("Gemini Live API rejected the session: %s", err)
        await _send_error(websocket, f"Gemini rejected the connection: {err.message or err}")
    except Exception:
        logger.exception("live_translate session failed with an unexpected error")
        await _send_error(websocket, "Unexpected server error.")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()


async def _send_error(websocket: WebSocket, message: str) -> None:
    if websocket.client_state != WebSocketState.CONNECTED:
        return
    try:
        await websocket.send_text(json.dumps({"type": "error", "message": message}))
    except Exception:
        logger.exception("Failed to deliver error message to client")


async def _pump_client_audio(websocket: WebSocket, session) -> None:
    while True:
        raw = await websocket.receive_text()

        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if not isinstance(message, dict):
            continue

        message_type = message.get("type")

        if message_type == "audio":
            data = message.get("data")
            if not isinstance(data, str):
                continue
            pcm_bytes = base64.b64decode(data)
            await send_audio_chunk(session, pcm_bytes)
        elif message_type == "end":
            await send_audio_stream_end(session)


async def _forward_transcriptions(session, websocket: WebSocket) -> None:
    async for result in receive_transcriptions(session):
        await websocket.send_text(
            json.dumps({"original_en": result.text, "is_final": result.is_final})
        )
