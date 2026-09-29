from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY

GEMINI_LIVE_MODEL = "gemini-3.5-transcribe-live"

_client = genai.Client(api_key=GEMINI_API_KEY)


class TranscriptionResult:
    def __init__(self, text: str, is_final: bool):
        self.text = text
        self.is_final = is_final


@asynccontextmanager
async def live_session():
    async with _client.aio.live.connect(
        model=GEMINI_LIVE_MODEL,
        config=types.LiveConnectConfig(
            input_audio_transcription=types.AudioTranscriptionConfig(
                language_codes=["en-US"],
            ),
        ),
    ) as session:
        yield session


async def send_audio_chunk(session, pcm_bytes: bytes) -> None:
    await session.send_realtime_input(
        audio=types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000"),
    )


async def send_audio_stream_end(session) -> None:
    await session.send_realtime_input(audio_stream_end=True)


async def receive_transcriptions(session) -> AsyncIterator[TranscriptionResult]:
    async for message in session.receive():
        content = message.server_content
        if not content:
            continue

        interim = content.interim_input_transcription
        if interim and interim.text:
            yield TranscriptionResult(text=interim.text, is_final=False)

        final = content.input_transcription
        if final and final.text:
            yield TranscriptionResult(text=final.text, is_final=True)
