from dataclasses import dataclass

from app.services.gemini_provider import GeminiProviderError, generate_with_gemini
from app.services.tutor_service import TutorServiceError, generate_with_ollama


@dataclass
class ProviderResult:
    content: str
    provider: str


def generate_with_fallback(prompt: str, *, task_name: str) -> ProviderResult:
    try:
        print("Using Gemini provider")
        return ProviderResult(
            content=generate_with_gemini(prompt, task_name=task_name),
            provider="gemini",
        )
    except GeminiProviderError as exc:
        print(f"Gemini failed, switching to Ollama: {exc}")

    print("Using Ollama provider")
    return ProviderResult(
        content=generate_with_ollama(prompt, task_name=task_name),
        provider="ollama",
    )


def require_content(content: str, *, empty_message: str) -> str:
    cleaned = content.strip()
    if not cleaned:
        raise TutorServiceError(empty_message, status_code=502)
    return cleaned
