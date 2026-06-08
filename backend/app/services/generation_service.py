import json
from typing import Any

from app.services.cache_service import (
    extract_topic_name,
    find_cached_topic,
    store_cached_topic,
)
from app.services.provider_router import generate_with_fallback, require_content
from app.services.tutor_service import TutorServiceError


RETEACHING_PROMPT_TEMPLATE = """You are MeetTutor, a patient personal teacher.

The transcript below is only a clue for identifying the student's topic.
Do not summarize the transcript.
Infer the underlying topic and teach it comprehensively from scratch.

Rules:
- Assume the student knows nothing.
- Fill in missing prerequisite knowledge before using advanced terms.
- Define terminology in simple language.
- Prefer teaching over brevity.
- Use analogies, concrete examples, and progressive explanations.
- Use headings and bullet points.
- Cover the full learning path from basics to advanced understanding.

Your lesson must follow exactly this structure:
1. Motivation
2. Prerequisites
3. Foundations
4. Intermediate Concepts
5. Advanced Concepts
6. Examples
7. Real-World Applications
8. Common Mistakes
9. Quick Recap

Topic to teach: {topic_name}

Transcript for context:
{transcript}
"""


FLASHCARD_PROMPT_TEMPLATE = """You are an expert tutor creating study flashcards.

Do not summarize the transcript.
Infer the underlying topic and create flashcards that reteach the topic from basics to advanced ideas.

Topic: {topic_name}

Return ONLY valid JSON in this format:
[
  {{
    "question": "...",
    "answer": "..."
  }}
]

Requirements:
- Generate 6 to 12 flashcards.
- Cover prerequisites, foundations, intermediate ideas, advanced ideas, and common mistakes.
- Keep answers concise but educational.
- Avoid duplicates.

Transcript for context:
{transcript}
"""


QUIZ_PROMPT_TEMPLATE = """You are an expert tutor creating a quiz.

Do not summarize the transcript.
Infer the underlying topic and create a quiz that checks understanding from basics to advanced concepts.

Topic: {topic_name}

Return ONLY valid JSON in this format:
[
  {{
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "answer": "..."
  }}
]

Requirements:
- Generate 5 to 10 questions.
- Every answer must match one option exactly.
- Include foundational, intermediate, advanced, and common-mistake checks.
- Avoid duplicates.

Transcript for context:
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
        raise ValueError("Expected a JSON array.")

    return parsed


def _validate_flashcards(raw_flashcards: list[Any]) -> list[dict[str, str]]:
    flashcards: list[dict[str, str]] = []
    seen_questions: set[str] = set()

    for item in raw_flashcards:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        normalized_question = question.lower()

        if not question or not answer or normalized_question in seen_questions:
            continue

        seen_questions.add(normalized_question)
        flashcards.append({"question": question, "answer": answer})

    return flashcards[:12]


def _validate_quiz(raw_quiz: list[Any]) -> list[dict[str, Any]]:
    quiz: list[dict[str, Any]] = []
    seen_questions: set[str] = set()

    for item in raw_quiz:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        options = item.get("options", [])
        normalized_question = question.lower()

        if (
            not question
            or normalized_question in seen_questions
            or not isinstance(options, list)
        ):
            continue

        clean_options = [str(option).strip() for option in options if str(option).strip()]
        if len(clean_options) < 2 or answer not in clean_options:
            continue

        seen_questions.add(normalized_question)
        quiz.append(
            {
                "question": question,
                "options": clean_options[:4],
                "answer": answer,
            }
        )

    return quiz[:10]


def _generate_flashcards(topic_name: str, transcript: str) -> list[dict[str, str]]:
    prompt = FLASHCARD_PROMPT_TEMPLATE.format(
        topic_name=topic_name,
        transcript=transcript,
    )

    try:
        result = generate_with_fallback(prompt, task_name="flashcards")
        raw_flashcards = _extract_json_array(result.content)
        flashcards = _validate_flashcards(raw_flashcards)
        if not flashcards:
            raise ValueError("No valid flashcards returned.")
        return flashcards
    except Exception as exc:
        print(f"Flashcard generation failed without blocking reteaching: {exc}")
        return []


def _generate_quiz(topic_name: str, transcript: str) -> list[dict[str, Any]]:
    prompt = QUIZ_PROMPT_TEMPLATE.format(
        topic_name=topic_name,
        transcript=transcript,
    )

    try:
        result = generate_with_fallback(prompt, task_name="quiz")
        raw_quiz = _extract_json_array(result.content)
        quiz = _validate_quiz(raw_quiz)
        if not quiz:
            raise ValueError("No valid quiz returned.")
        return quiz
    except Exception as exc:
        print(f"Quiz generation failed without blocking reteaching: {exc}")
        return []


def generate_learning_package(transcript: str) -> dict[str, Any]:
    cleaned_transcript = transcript.strip()
    if not cleaned_transcript:
        raise TutorServiceError("Transcript cannot be empty.", status_code=400)

    topic_name = extract_topic_name(cleaned_transcript)
    print(f"Extracted topic name: {topic_name}")

    cached_payload = find_cached_topic(topic_name)
    if cached_payload:
        print("Returning cached learning package")
        return {
            "topic_name": cached_payload.get("topic_name", topic_name),
            "provider": cached_payload.get("provider", "cache"),
            "reteaching": str(cached_payload.get("reteaching", "")).strip(),
            "flashcards": list(cached_payload.get("flashcards", [])),
            "quiz": list(cached_payload.get("quiz", [])),
            "cache_hit": True,
        }

    reteaching_prompt = RETEACHING_PROMPT_TEMPLATE.format(
        topic_name=topic_name,
        transcript=cleaned_transcript,
    )
    reteaching_result = generate_with_fallback(reteaching_prompt, task_name="reteaching")
    reteaching = require_content(
        reteaching_result.content,
        empty_message="The AI provider returned an empty reteaching response.",
    )

    flashcards = _generate_flashcards(topic_name, cleaned_transcript)
    quiz = _generate_quiz(topic_name, cleaned_transcript)

    stored_payload = store_cached_topic(
        topic_name=topic_name,
        reteaching=reteaching,
        flashcards=flashcards,
        quiz=quiz,
        provider=reteaching_result.provider,
    )

    return {
        "topic_name": stored_payload["topic_name"],
        "provider": stored_payload["provider"],
        "reteaching": stored_payload["reteaching"],
        "flashcards": stored_payload["flashcards"],
        "quiz": stored_payload["quiz"],
        "cache_hit": False,
    }
