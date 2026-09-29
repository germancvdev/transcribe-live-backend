import os


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


GEMINI_API_KEY = _require_env("GEMINI_API_KEY")
BACKEND_SHARED_KEY = _require_env("BACKEND_SHARED_KEY")
