"use client";

import { FormEvent, useState } from "react";

type Flashcard = {
  question: string;
  answer: string;
};

type QuizQuestion = {
  question: string;
  options: string[];
  answer: string;
};

type LearningMaterial = {
  reteaching: string;
  flashcards: Flashcard[];
  quiz: QuizQuestion[];
};

const apiUrl = "http://127.0.0.1:8000/generate";

type ApiErrorResponse = {
  detail?: string;
};

export default function Home() {
  const [transcript, setTranscript] = useState("");
  const [material, setMaterial] = useState<LearningMaterial | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!transcript.trim()) {
      setError("Please paste a transcript before generating learning material.");
      setMaterial(null);
      return;
    }

    setError("");
    setLoadingStage("Analyzing transcript...");
    setIsLoading(true);

    const explanationTimer = window.setTimeout(() => {
      setLoadingStage("Generating explanation...");
    }, 800);
    const flashcardTimer = window.setTimeout(() => {
      setLoadingStage("Generating flashcards...");
    }, 3500);

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ transcript }),
      });

      if (!response.ok) {
        const errorData = (await response.json().catch(() => ({}))) as ApiErrorResponse;
        throw new Error(errorData.detail || "Failed to generate learning material.");
      }

      const data = (await response.json()) as LearningMaterial;
      setMaterial(data);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "The API request failed. Please make sure the backend is running.";
      setError(message);
      setMaterial(null);
    } finally {
      window.clearTimeout(explanationTimer);
      window.clearTimeout(flashcardTimer);
      setLoadingStage("");
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f8fb] px-6 py-10 text-[#172033]">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <header className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-[#2f6f6d]">
            MeetTutor
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight sm:text-5xl">
            Turn transcripts into clear study material.
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-[#526070]">
            Paste a meeting or class transcript and prepare the space for a
            beginner-friendly explanation, flashcards, and a quiz.
          </p>
        </header>

        <form
          onSubmit={handleGenerate}
          className="rounded-lg border border-[#d9e0e8] bg-white p-5 shadow-sm"
        >
          <label
            htmlFor="transcript"
            className="mb-3 block text-base font-semibold text-[#172033]"
          >
            Paste Transcript
          </label>
          <textarea
            id="transcript"
            name="transcript"
            rows={12}
            value={transcript}
            onChange={(event) => setTranscript(event.target.value)}
            placeholder="Paste your meeting or class transcript here..."
            className="min-h-72 w-full resize-y rounded-md border border-[#c8d2dc] bg-white p-4 leading-7 outline-none transition focus:border-[#2f6f6d] focus:ring-4 focus:ring-[#2f6f6d]/15"
          />
          {error ? (
            <p className="mt-3 rounded-md border border-[#f0b8b8] bg-[#fff4f4] px-3 py-2 text-sm font-medium text-[#9b2c2c]">
              {error}
            </p>
          ) : null}
          {isLoading ? (
            <p className="mt-3 rounded-md border border-[#d5e6e5] bg-[#f2fbfa] px-3 py-2 text-sm font-medium text-[#2f6f6d]">
              {loadingStage}
            </p>
          ) : null}
          <div className="mt-4 flex justify-end">
            <button
              type="submit"
              disabled={isLoading}
              className="rounded-md bg-[#2f6f6d] px-5 py-3 font-semibold text-white transition hover:bg-[#285f5d] focus:outline-none focus:ring-4 focus:ring-[#2f6f6d]/25 disabled:cursor-not-allowed disabled:bg-[#8aa9a8]"
            >
              {isLoading ? loadingStage : "Generate Learning Material"}
            </button>
          </div>
        </form>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="min-h-48 rounded-lg border border-[#d9e0e8] bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold">Re-Teaching</h2>
            {material ? (
              <div className="mt-4 whitespace-pre-wrap leading-7 text-[#526070]">
                {material.reteaching}
              </div>
            ) : null}
          </article>

          <article className="min-h-48 rounded-lg border border-[#d9e0e8] bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold">Flashcards</h2>
            {material ? (
              <div className="mt-4 space-y-3">
                {material.flashcards.length > 0 ? (
                  material.flashcards.map((flashcard) => (
                    <div
                      key={`${flashcard.question}-${flashcard.answer}`}
                      className="rounded-md border border-[#e4e9ef] p-3"
                    >
                      <p className="text-sm font-semibold uppercase tracking-wide text-[#2f6f6d]">
                        Question:
                      </p>
                      <p className="mt-1 font-semibold">{flashcard.question}</p>
                      <p className="mt-3 text-sm font-semibold uppercase tracking-wide text-[#2f6f6d]">
                        Answer:
                      </p>
                      <p className="mt-1 text-[#526070]">{flashcard.answer}</p>
                    </div>
                  ))
                ) : (
                  <p className="leading-7 text-[#526070]">
                    No flashcards were generated.
                  </p>
                )}
              </div>
            ) : null}
          </article>

          <article className="min-h-48 rounded-lg border border-[#d9e0e8] bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold">Quiz</h2>
            {material ? (
              <div className="mt-4 space-y-4">
                {material.quiz.map((question) => (
                  <div key={question.question}>
                    <p className="font-semibold">{question.question}</p>
                    <ul className="mt-3 space-y-2">
                      {question.options.map((option) => (
                        <li
                          key={option}
                          className="rounded-md border border-[#e4e9ef] px-3 py-2 text-[#526070]"
                        >
                          {option}
                        </li>
                      ))}
                    </ul>
                    <p className="mt-3 text-sm font-semibold text-[#2f6f6d]">
                      Answer: {question.answer}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
          </article>
        </section>
      </section>
    </main>
  );
}
