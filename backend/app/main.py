from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.services.flashcard_service import generate_flashcards
from app.services.tutor_service import (
    TutorServiceError,
    _model_name,
    _ollama_num_predict,
    _ollama_timeout,
    generate_reteaching,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    print(f"Configured model: {_model_name()}")
    print(f"Configured timeout: {_ollama_timeout()}")
    print(f"Configured max generated tokens: {_ollama_num_predict()}")
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
        reteaching_start = time.time()
        reteaching = generate_reteaching(request.transcript)
        reteaching_elapsed = time.time() - reteaching_start
        print(f"Reteaching took {reteaching_elapsed:.2f}s")
    except TutorServiceError as exc:
        total_elapsed = time.time() - request_start
        print(f"Total request took {total_elapsed:.2f}s")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    try:
        flashcards_start = time.time()
        flashcards = generate_flashcards(request.transcript)
        flashcards_elapsed = time.time() - flashcards_start
        print(f"Flashcards took {flashcards_elapsed:.2f}s")
    except Exception as exc:
        flashcards_elapsed = time.time() - flashcards_start
        print(f"Flashcards took {flashcards_elapsed:.2f}s")
        print(f"Flashcard generation failed without blocking reteaching: {exc}")
        flashcards = []

    total_elapsed = time.time() - request_start
    print(f"Total request took {total_elapsed:.2f}s")

    return GenerateResponse(reteaching=reteaching, flashcards=flashcards, quiz=[])
