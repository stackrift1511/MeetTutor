import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "using",
    "what",
    "why",
    "with",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token and token not in STOP_WORDS
    ]


def _candidate_phrases(text: str) -> list[str]:
    normalized_text = re.sub(r"\s+", " ", text.strip())
    if not normalized_text:
        return []

    phrases: list[str] = []

    quoted = re.findall(r'"([^"]{3,80})"', normalized_text)
    phrases.extend(quoted)

    title_case = re.findall(
        r"\b(?:[A-Z][a-zA-Z0-9/+.-]*\s+){0,4}[A-Z][a-zA-Z0-9/+.-]*\b",
        normalized_text,
    )
    phrases.extend(title_case)

    upper_case = re.findall(r"\b[A-Z]{2,}(?:/[A-Z]{2,})*\b", normalized_text)
    phrases.extend(upper_case)

    words = _tokenize(normalized_text)
    ngrams: list[str] = []
    for size in range(3, 0, -1):
        for index in range(len(words) - size + 1):
            ngrams.append(" ".join(words[index : index + size]))
    phrases.extend(ngrams[:15])

    cleaned_phrases: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        compact = re.sub(r"\s+", " ", phrase).strip(" .,:;!?-")
        slug = _slugify(compact)
        if len(slug) < 3 or slug in seen:
            continue
        seen.add(slug)
        cleaned_phrases.append(compact)

    return cleaned_phrases


def extract_topic_name(transcript: str) -> str:
    phrases = _candidate_phrases(transcript)
    if phrases:
        return phrases[0]

    tokens = _tokenize(transcript)
    if tokens:
        return " ".join(tokens[:3]).title()

    return "General Topic"


def normalize_topic_name(topic_name: str) -> str:
    normalized = _slugify(topic_name)
    return normalized or "generaltopic"


def _topic_similarity(left: str, right: str) -> float:
    left_tokens = set(_tokenize(left))
    right_tokens = set(_tokenize(right))

    if left_tokens and right_tokens:
        overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    else:
        overlap = 0.0

    compact_similarity = SequenceMatcher(
        None, normalize_topic_name(left), normalize_topic_name(right)
    ).ratio()

    return max(overlap, compact_similarity)


def _cache_file(cache_key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{cache_key}.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def find_cached_topic(topic_name: str) -> dict[str, Any] | None:
    cache_key = normalize_topic_name(topic_name)
    direct_path = _cache_file(cache_key)

    if direct_path.exists():
        payload = _load_json(direct_path)
        if payload:
            print(f"Cache hit for topic '{topic_name}' using exact key '{cache_key}'")
            return payload

    best_match: tuple[float, dict[str, Any]] | None = None
    for path in CACHE_DIR.glob("*.json"):
        payload = _load_json(path)
        if not payload:
            continue

        candidate_topic = str(payload.get("topic_name", path.stem))
        similarity = _topic_similarity(topic_name, candidate_topic)
        if similarity < 0.82:
            continue

        if best_match is None or similarity > best_match[0]:
            best_match = (similarity, payload)

    if best_match:
        print(
            "Cache hit for similar topic "
            f"'{topic_name}' matched to '{best_match[1].get('topic_name', 'unknown')}'"
        )
        return best_match[1]

    print(f"Cache miss for topic '{topic_name}'")
    return None


def store_cached_topic(
    *,
    topic_name: str,
    reteaching: str,
    flashcards: list[dict[str, str]],
    quiz: list[dict[str, Any]],
    provider: str,
) -> dict[str, Any]:
    cache_key = normalize_topic_name(topic_name)
    payload = {
        "topic_name": topic_name,
        "cache_key": cache_key,
        "provider": provider,
        "reteaching": reteaching,
        "flashcards": flashcards,
        "quiz": quiz,
    }

    path = _cache_file(cache_key)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Cached topic '{topic_name}' at {path}")
    return payload
