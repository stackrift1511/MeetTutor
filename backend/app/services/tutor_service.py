import os
import time

import httpx
from dotenv import load_dotenv
from ollama import Client, ResponseError

load_dotenv()

DEFAULT_MODEL_NAME = "mistral"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 180.0
DEFAULT_OLLAMA_NUM_PREDICT = 150
TIMEOUT_ERROR_MESSAGE = """Ollama took too long to respond. Consider:

1. Increasing OLLAMA_TIMEOUT_SECONDS
2. Switching to MODEL_NAME=mistral
3. Verifying Ollama is running
4. Testing the model directly with 'ollama run mistral'
5. Lowering OLLAMA_NUM_PREDICT for faster local responses"""


TUTOR_PROMPT_TEMPLATE = """You are an expert teacher.

Teach the following transcript to a complete beginner.

Rules:

* Assume zero prior knowledge.
* Explain only the most important prerequisite concepts first.
* Define technical terms.
* Use simple language.
* Use examples.
* Focus on teaching rather than summarizing.
* Keep the lesson under 140 words.
* Use exactly three short sections.
* Each section must be one or two sentences.
* Finish with a complete final sentence.

Transcript:

{transcript}
"""


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


def generate_reteaching(transcript: str) -> str:
    cleaned_transcript = transcript.strip()

    if not cleaned_transcript:
        raise TutorServiceError("Transcript cannot be empty.", status_code=400)

    model = _model_name()
    timeout = _ollama_timeout()
    num_predict = _ollama_num_predict()
    prompt = TUTOR_PROMPT_TEMPLATE.format(transcript=cleaned_transcript)
    client = Client(timeout=timeout)

    print(f"Using model: {model}")
    print(f"Timeout: {timeout} seconds")
    print(f"Max generated tokens: {num_predict}")
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
        print(f"Generation completed in {elapsed:.2f} seconds")
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

    reteaching = response["message"]["content"].strip()

    if not reteaching:
        raise TutorServiceError(
            "Ollama returned an empty explanation.",
            status_code=502,
        )

    return reteaching
