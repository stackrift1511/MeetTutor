import os
from pathlib import Path
import time

import httpx
from dotenv import load_dotenv
from ollama import Client, ResponseError

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT_DIR = BACKEND_DIR.parent
ENV_CANDIDATES = (BACKEND_DIR / ".env", REPO_ROOT_DIR / ".env")
LOADED_ENV_FILE = next((path for path in ENV_CANDIDATES if path.exists()), None)

if LOADED_ENV_FILE is not None:
    load_dotenv(LOADED_ENV_FILE)
else:
    load_dotenv()

DEFAULT_MODEL_NAME = "mistral"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 180.0
DEFAULT_OLLAMA_NUM_PREDICT = 1200
TIMEOUT_ERROR_MESSAGE = """Ollama took too long to respond. Consider:

1. Increasing OLLAMA_TIMEOUT_SECONDS
2. Switching to MODEL_NAME=mistral
3. Verifying Ollama is running
4. Testing the model directly with 'ollama run mistral'
5. Lowering OLLAMA_NUM_PREDICT for faster local responses"""


class TutorServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _model_name() -> str:
    return os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME


def _ollama_timeout() -> float:
    raw_timeout = os.getenv(
        "OLLAMA_TIMEOUT_SECONDS", str(int(DEFAULT_OLLAMA_TIMEOUT_SECONDS))
    ).strip()

    try:
        return float(raw_timeout)
    except ValueError:
        return DEFAULT_OLLAMA_TIMEOUT_SECONDS


def _ollama_num_predict() -> int:
    raw_num_predict = os.getenv(
        "OLLAMA_NUM_PREDICT", str(DEFAULT_OLLAMA_NUM_PREDICT)
    ).strip()

    try:
        return max(100, int(raw_num_predict))
    except ValueError:
        return DEFAULT_OLLAMA_NUM_PREDICT


def generate_with_ollama(prompt: str, *, task_name: str) -> str:
    model = _model_name()
    timeout = _ollama_timeout()
    num_predict = _ollama_num_predict()
    client = Client(timeout=timeout)

    print(f"Ollama task '{task_name}' using model: {model}")
    print(f"Ollama timeout: {timeout} seconds")
    print(f"Ollama max generated tokens: {num_predict}")
    print("Sending request to Ollama...")

    try:
        start_time = time.time()
        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "num_predict": num_predict,
                "temperature": 0.2,
            },
        )
        elapsed = time.time() - start_time
        print("Received response from Ollama")
        print(f"Ollama task '{task_name}' completed in {elapsed:.2f} seconds")
    except ResponseError as exc:
        message = str(exc).lower()
        if exc.status_code == 404 or "not found" in message:
            raise TutorServiceError(
                f"Model {model} is not installed. Run: ollama pull {model}",
                status_code=502,
            ) from exc

        raise TutorServiceError(
            f"Ollama generation failed: {exc}",
            status_code=502,
        ) from exc
    except httpx.ConnectError as exc:
        raise TutorServiceError(
            "Ollama service is not running. Start it with: ollama serve",
            status_code=502,
        ) from exc
    except httpx.TimeoutException as exc:
        raise TutorServiceError(TIMEOUT_ERROR_MESSAGE, status_code=504) from exc
    except Exception as exc:
        message = str(exc).lower()
        if "connection" in message or "refused" in message:
            raise TutorServiceError(
                "Ollama service is not running. Start it with: ollama serve",
                status_code=502,
            ) from exc

        raise TutorServiceError(
            "Ollama failed to generate a response.",
            status_code=502,
        ) from exc

    content = response["message"]["content"].strip()
    if not content:
        raise TutorServiceError("Ollama returned an empty response.", status_code=502)
    return content
