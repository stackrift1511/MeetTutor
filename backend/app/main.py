from contextlib import asynccontextmanager
import os
from pathlib import Path
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT_DIR = BACKEND_DIR.parent
ENV_CANDIDATES = (BACKEND_DIR / ".env", REPO_ROOT_DIR / ".env")
LOADED_ENV_FILE = next((path for path in ENV_CANDIDATES if path.exists()), None)

if LOADED_ENV_FILE is not None:
    load_dotenv(LOADED_ENV_FILE)
else:
    load_dotenv()

from app.services.gemini_provider import _gemini_model, _gemini_timeout
from app.services.generation_service import generate_learning_package
from app.services.tutor_service import TutorServiceError, _model_name, _ollama_num_predict, _ollama_timeout

@asynccontextmanager
async def lifespan(_: FastAPI):
    print(f"Resolved env file: {LOADED_ENV_FILE or 'None found'}")
    print(f"Configured Gemini model: {_gemini_model()}")
    print(f"Configured Gemini timeout: {_gemini_timeout()}")
    print(f"Configured Ollama model: {_model_name()}")
    print(f"Configured Ollama timeout: {_ollama_timeout()}")
    print(f"Configured Ollama max generated tokens: {_ollama_num_predict()}")
    print("Gemini key found:", bool(os.getenv("GEMINI_API_KEY")))
    print("Gemini key value:", os.getenv("GEMINI_API_KEY"))
    yield


app = FastAPI(title="MeetTutor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    transcript: str


class Flashcard(BaseModel):
    question: str
    answer: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    answer: str


class GenerateResponse(BaseModel):
    reteaching: str
    flashcards: list[Flashcard]
    quiz: list[QuizQuestion]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
def generate(request: GenerateRequest) -> GenerateResponse:
    request_start = time.time()

    try:
        package = generate_learning_package(request.transcript)
    except TutorServiceError as exc:
        total_elapsed = time.time() - request_start
        print(f"Total request took {total_elapsed:.2f}s")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    total_elapsed = time.time() - request_start
    print(f"Topic: {package['topic_name']}")
    print(f"Provider used: {package['provider']}")
    print(f"Cache hit: {package['cache_hit']}")
    print(f"Total request took {total_elapsed:.2f}s")

    return GenerateResponse(
        reteaching=package["reteaching"],
        flashcards=package["flashcards"],
        quiz=package["quiz"],
    )
