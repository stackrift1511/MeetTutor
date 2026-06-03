import json
import time
from typing import Any

import httpx
from ollama import Client, ResponseError

from app.services.tutor_service import (
    TIMEOUT_ERROR_MESSAGE,
    TutorServiceError,
    _model_name,
    _ollama_timeout,
)


FLASHCARD_PROMPT_TEMPLATE = """You are an expert educator.

Generate educational flashcards from the transcript.

Rules:

* Focus on concepts actually discussed.
* Questions should test understanding.
* Answers should be concise.
* Avoid duplicate flashcards.
* Prefer conceptual understanding over memorization.
* Generate between 5 and 15 flashcards.

Return ONLY valid JSON.

Required format:

[
  {{
    "question": "...",
    "answer": "..."
  }}
]

Transcript:

{transcript}
"""


STRICT_FLASHCARD_PROMPT_TEMPLATE = """Return ONLY a valid JSON array of flashcards.

Do not include markdown, explanations, code fences, comments, or extra text.

Each item must have exactly these string fields:
- question
- answer

Generate 5 to 15 flashcards from this transcript:

{transcript}
"""


def _extract_json_array(raw_output: str) -> list[Any]:
    cleaned_output = raw_output.strip()

    if cleaned_output.startswith("```"):
        cleaned_output = cleaned_output.removeprefix("```json").removeprefix("```")
        cleaned_output = cleaned_output.removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned_output)
    except json.JSONDecodeError:
        start = cleaned_output.find("[")
        end = cleaned_output.rfind("]")

        if start == -1 or end == -1 or end <= start:
            raise

        parsed = json.loads(cleaned_output[start : end + 1])

    if not isinstance(parsed, list):
        raise ValueError("Flashcard response must be a JSON array.")

    return parsed


def _validate_flashcards(raw_flashcards: list[Any]) -> list[dict[str, str]]:
    flashcards: list[dict[str, str]] = []
    seen_questions: set[str] = set()

    for item in raw_flashcards:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()

        if not question or not answer:
            continue

        normalized_question = question.lower()
        if normalized_question in seen_questions:
            continue

        seen_questions.add(normalized_question)
        flashcards.append({"question": question, "answer": answer})

    return flashcards[:15]


def _request_flashcards(prompt: str) -> str:
    model = _model_name()
    timeout = _ollama_timeout()
    client = Client(timeout=timeout)

    print(f"Using model for flashcards: {model}")
    print(f"Flashcard timeout: {timeout} seconds")
    print("Sending flashcard request to Ollama...")

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
            "num_predict": 600,
            "temperature": 0.1,
        },
    )
    elapsed = time.time() - start_time
    print("Received flashcard response from Ollama")
    print(f"Flashcard generation completed in {elapsed:.2f} seconds")

    return response["message"]["content"].strip()


def generate_flashcards(transcript: str) -> list[dict[str, str]]:
    service_start = time.time()
    ollama_call_count = 0
    cleaned_transcript = transcript.strip()

    if not cleaned_transcript:
        raise TutorServiceError("Transcript cannot be empty.", status_code=400)

    prompts = [
        FLASHCARD_PROMPT_TEMPLATE.format(transcript=cleaned_transcript),
        STRICT_FLASHCARD_PROMPT_TEMPLATE.format(transcript=cleaned_transcript),
    ]

    for attempt, prompt in enumerate(prompts, start=1):
        try:
            attempt_start = time.time()
            ollama_call_count += 1
            print(f"Flashcard attempt {attempt} started")
            raw_output = _request_flashcards(prompt)
            attempt_elapsed = time.time() - attempt_start
            print(f"Flashcard attempt {attempt} Ollama call took {attempt_elapsed:.2f}s")
            parsed = _extract_json_array(raw_output)
            flashcards = _validate_flashcards(parsed)

            if flashcards:
                total_elapsed = time.time() - service_start
                print(f"Flashcard service made {ollama_call_count} Ollama call(s)")
                print(f"Flashcard service total time: {total_elapsed:.2f}s")
                return flashcards

            print(f"Flashcard attempt {attempt} returned no valid flashcards.")
        except json.JSONDecodeError:
            print(f"Flashcard attempt {attempt} returned invalid JSON.")
        except ValueError as exc:
            print(f"Flashcard attempt {attempt} failed validation: {exc}")
        except ResponseError as exc:
            message = str(exc).lower()
            if exc.status_code == 404 or "not found" in message:
                print(f"Flashcard model error: Model {_model_name()} is not installed.")
                total_elapsed = time.time() - service_start
                print(f"Flashcard service made {ollama_call_count} Ollama call(s)")
                print(f"Flashcard service total time: {total_elapsed:.2f}s")
                return []

            print(f"Flashcard Ollama response error: {exc}")
            total_elapsed = time.time() - service_start
            print(f"Flashcard service made {ollama_call_count} Ollama call(s)")
            print(f"Flashcard service total time: {total_elapsed:.2f}s")
            return []
        except httpx.ConnectError:
            print("Flashcard generation skipped because Ollama is not running.")
            total_elapsed = time.time() - service_start
            print(f"Flashcard service made {ollama_call_count} Ollama call(s)")
            print(f"Flashcard service total time: {total_elapsed:.2f}s")
            return []
        except httpx.TimeoutException:
            print(TIMEOUT_ERROR_MESSAGE)
            total_elapsed = time.time() - service_start
            print(f"Flashcard service made {ollama_call_count} Ollama call(s)")
            print(f"Flashcard service total time: {total_elapsed:.2f}s")
            return []
        except Exception as exc:
            print(f"Flashcard generation failed: {exc}")
            total_elapsed = time.time() - service_start
            print(f"Flashcard service made {ollama_call_count} Ollama call(s)")
            print(f"Flashcard service total time: {total_elapsed:.2f}s")
            return []

    total_elapsed = time.time() - service_start
    print(f"Flashcard service made {ollama_call_count} Ollama call(s)")
    print(f"Flashcard service total time: {total_elapsed:.2f}s")
    return []
