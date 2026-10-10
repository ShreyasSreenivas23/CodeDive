# codedive

codedive is a small GitHub repository RAG app. It clones a public GitHub repository, reads useful source and documentation files, chunks them, embeds them, stores them in Chroma, and answers questions with source-file references.

The project intentionally stays small: FastAPI, Chroma, Ollama/OpenAI-compatible AI services, and a React/Vite frontend.

## Features

- Analyze a public GitHub repository URL.
- Shallow-clone repositories without executing their code.
- Filter common source, config, and documentation files.
- Chunk files with source path and line metadata.
- Store chunk embeddings in persistent Chroma collections.
- Ask questions and receive answers with source references.
- Keep conversation history in the browser.
- Run locally by default with Ollama-hosted models.

## Project Layout

```text
backend/
  main.py
  github.py
  loader.py
  chunker.py
  embeddings.py
  vector_store.py
  llm.py
  rag.py
  tests/
frontend/
  src/
    components/
    App.jsx
    api.js
    main.jsx
```

## Backend Setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.main:app --reload --port 8001
```

The API will run at `http://localhost:8001`.

```http
GET /health
```

```json
{
  "status": "ok"
}
```

## Frontend Setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The app will run at `http://localhost:5173`.

## AI Configuration

By default, `.env` runs fully offline: answers come from the locally hosted Ollama model `qwen2.5-coder:7b-instruct`, and embeddings use deterministic local hashing (no model downloads required):

```env
EMBEDDING_PROVIDER=local
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=qwen2.5-coder:7b-instruct
```

Just make sure Ollama is running:

```powershell
ollama serve
```

`qwen2.5-coder:7b-instruct` is used for answers. Local embeddings work offline out of the box, but RAG retrieval works best with a dedicated embedding model. If you install one, you can switch to it:

```powershell
ollama pull qwen3-embedding:latest
```

```env
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:latest
```

You can still switch providers:

- `EMBEDDING_PROVIDER=gemini` and `LLM_PROVIDER=gemini` use the Gemini API through Google's OpenAI-compatible endpoint (`GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`) with `GEMINI_LLM_MODEL` and `GEMINI_EMBEDDING_MODEL`; require `GEMINI_API_KEY` in `.env`.
- `EMBEDDING_PROVIDER=auto` and `LLM_PROVIDER=auto` use the configured Gemini key when set, otherwise Ollama.
- `EMBEDDING_PROVIDER=local` and `LLM_PROVIDER=local` use deterministic local embeddings and a conservative extractive local answer.

API keys stay on the backend and are never sent to the React frontend.

## API

### Analyze Repository

```http
POST /analyze
```

```json
{
  "url": "https://github.com/user/project"
}
```

Response:

```json
{
  "status": "success",
  "repository_id": "abc123",
  "repository": "project",
  "owner": "user",
  "files": 42,
  "chunks": 317,
  "message": "Repository indexed"
}
```

### Ask Question

```http
POST /chat
```

```json
{
  "repository_id": "abc123",
  "question": "How does authentication work?"
}
```

Response:

```json
{
  "answer": "Authentication is handled by...",
  "sources": [
    {
      "file": "src/auth.py",
      "start_line": 12,
      "end_line": 48
    }
  ]
}
```

## Tests

```powershell
python -m pytest backend/tests
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Security Notes

codedive never executes cloned repository code. It only clones, reads text files, chunks content, embeds it, and retrieves context for question answering.
