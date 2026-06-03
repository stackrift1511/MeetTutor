# MeetTutor Installation Guide

This guide walks through setting up MeetTutor locally on Windows.

## Prerequisites

Install these first:

- Git
- Python 3.11 or newer
- Node.js 18 or newer
- Ollama

Recommended Ollama model for local CPU development:

```powershell
ollama pull mistral
```

You can verify Ollama is available with:

```powershell
ollama list
```

## Project Structure

MeetTutor has two parts:

- `frontend/` - Next.js app
- `backend/` - FastAPI API

## 1. Clone The Repository

```powershell
git clone <YOUR_REPOSITORY_URL>
cd MeetTutor
```

If you already have the project locally, just open the root folder:

```powershell
cd C:\Projects\MeetTutor
```

## 2. Backend Setup

Move into the backend folder:

```powershell
cd backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r requirements.txt
```

## 3. Backend Environment Variables

Create a local `.env` file inside `backend/`.

Example contents:

```env
MODEL_NAME=mistral
OLLAMA_TIMEOUT_SECONDS=180
OLLAMA_NUM_PREDICT=150
```

Notes:

- `MODEL_NAME=mistral` is the recommended default for local CPU usage.
- `OLLAMA_TIMEOUT_SECONDS=180` gives the model enough time on slower hardware.
- `OLLAMA_NUM_PREDICT=150` keeps reteaching responses shorter and faster.

## 4. Start Ollama

Make sure Ollama is running:

```powershell
ollama serve
```

If Ollama is already running in the desktop app, this may not be necessary.

You can test the model directly:

```powershell
ollama run mistral
```

## 5. Start The Backend

From the `backend/` folder:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful backend URLs:

- Health check: `http://127.0.0.1:8000/health`
- Generate endpoint: `http://127.0.0.1:8000/generate`

## 6. Frontend Setup

Open a second terminal and move into the frontend folder:

```powershell
cd C:\Projects\MeetTutor\frontend
```

Install frontend dependencies:

```powershell
npm install
```

If PowerShell blocks `npm`, use:

```powershell
npm.cmd install
```

## 7. Start The Frontend

Run the Next.js app:

```powershell
npm run dev -- -p 3000
```

If needed:

```powershell
npm.cmd run dev -- -p 3000
```

Open:

```text
http://localhost:3000
```

## 8. How To Use MeetTutor

1. Open the frontend in your browser.
2. Paste a meeting or class transcript.
3. Click `Generate Learning Material`.
4. Wait while the app:
   - analyzes the transcript
   - generates the reteaching explanation
   - generates flashcards

Current output includes:

- AI-generated reteaching
- AI-generated flashcards
- Empty quiz section for now

## Troubleshooting

### Ollama is not running

If you see an error like:

```text
Ollama service is not running.
```

Start it with:

```powershell
ollama serve
```

### Model not installed

If you see an error like:

```text
Model mistral is not installed.
```

Run:

```powershell
ollama pull mistral
```

### Generation is too slow

This project currently runs on local CPU inference, so responses may take time.

Ways to improve speed:

- Keep transcripts shorter while testing
- Use `mistral` instead of larger models
- Close other heavy applications
- Make sure Ollama is already warmed up by running a small test prompt first

Example warm-up:

```powershell
ollama run mistral
```

### Frontend cannot connect to backend

Check that:

- backend is running on `127.0.0.1:8000`
- frontend is running on `localhost:3000`
- no other process is blocking those ports

### PowerShell blocks npm

Use:

```powershell
npm.cmd install
npm.cmd run dev -- -p 3000
```

## Optional: Git Setup

If this project is not yet a Git repo:

```powershell
git init
git add .
git commit -m "Initial MeetTutor project"
```

To push to GitHub:

```powershell
git remote add origin <YOUR_REPOSITORY_URL>
git branch -M main
git push -u origin main
```
