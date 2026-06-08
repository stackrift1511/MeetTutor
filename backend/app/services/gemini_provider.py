import os
from pathlib import Path
import time

import httpx
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT_DIR = BACKEND_DIR.parent
ENV_CANDIDATES = (BACKEND_DIR / ".env", REPO_ROOT_DIR / ".env")
LOADED_ENV_FILE = next((path for path in ENV_CANDIDATES if path.exists()), None)

if LOADED_ENV_FILE is not None:
    load_dotenv(LOADED_ENV_FILE)
else:
    load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_GEMINI_TIMEOUT_SECONDS = 45.0
GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiProviderError(Exception):
    pass


def _gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def _gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


def _gemini_timeout() -> float:
    raw_timeout = os.getenv(
        "GEMINI_TIMEOUT_SECONDS", str(int(DEFAULT_GEMINI_TIMEOUT_SECONDS))
    ).strip()

    try:
        return float(raw_timeout)
    except ValueError:
        return DEFAULT_GEMINI_TIMEOUT_SECONDS


def generate_with_gemini(prompt: str, *, task_name: str) -> str:
    api_key = _gemini_api_key()
    print(f"Gemini env file: {LOADED_ENV_FILE or 'None found'}")
    print("Gemini key found:", bool(os.getenv("GEMINI_API_KEY")))
    print("Gemini key value:", os.getenv("GEMINI_API_KEY"))
    if not api_key:
        raise GeminiProviderError("Missing GEMINI_API_KEY")

    model = _gemini_model()
    timeout = _gemini_timeout()
    url = GEMINI_API_URL_TEMPLATE.format(model=model)

    print(f"Gemini task '{task_name}' using model: {model}")
    print(f"Gemini timeout: {timeout} seconds")

    try:
        start_time = time.time()
        response = httpx.post(
            url,
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=timeout,
        )
        elapsed = time.time() - start_time
        print(f"Gemini task '{task_name}' completed in {elapsed:.2f}s")
    except httpx.TimeoutException as exc:
        raise GeminiProviderError("Gemini request timed out") from exc
    except httpx.HTTPError as exc:
        raise GeminiProviderError(f"Gemini network error: {exc}") from exc

    if response.status_code >= 400:
        raise GeminiProviderError(
            f"Gemini API failure {response.status_code}: {response.text[:200]}"
        )

    payload = response.json()
    candidates = payload.get("candidates", [])
    if not candidates:
        raise GeminiProviderError("Gemini returned no candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    content = "\n".join(
        part.get("text", "").strip() for part in parts if part.get("text")
    ).strip()
    if not content:
        raise GeminiProviderError("Gemini returned empty content")

    return content
