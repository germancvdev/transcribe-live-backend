# transcribe-live-backend

FastAPI WebSocket backend for `transcribe-live-app`. Proxies audio to the
Gemini Live API and streams back transcriptions.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in GEMINI_API_KEY and BACKEND_SHARED_KEY in .env

uvicorn app.main:app --reload --port 8000
```

The WebSocket endpoint is `ws://localhost:8000/ws/live-translate`.

## Protocol

Client must send this as the first message after connecting:

```json
{ "type": "auth", "key": "<BACKEND_SHARED_KEY>" }
```

Then:

- `{ "type": "audio", "data": "<base64 PCM16 mono 16kHz>" }`
- `{ "type": "end" }`

Server sends:

- `{ "type": "ready" }`
- `{ "type": "error", "message": "..." }`
- `{ "original_en": "...", "is_final": true|false }`
