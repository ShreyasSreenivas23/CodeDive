from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from .config import get_settings
from .embeddings import EmbeddingError
from .github import CloneError, InvalidGitHubUrl
from .loader import RepositoryLoadError
from .llm import LLMError
from .rag import RAGError, RAGService, RepositoryNotIndexed
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    RepositorySummary,
)
from .vector_store import VectorStoreError


settings = get_settings()
app = FastAPI(title=settings.app_name)
rag_service = RAGService(settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repository(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = await run_in_threadpool(rag_service.analyze_repository, request.url)
    except InvalidGitHubUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CloneError as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not clone this repository. Check that the URL is valid and public.",
        ) from exc
    except (RepositoryLoadError, RAGError, EmbeddingError, VectorStoreError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AnalyzeResponse(
        status="success",
        repository_id=result.repository_id,
        repository=result.repository,
        owner=result.owner,
        files=result.files,
        chunks=result.chunks,
        message="Repository indexed",
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await run_in_threadpool(
            rag_service.chat,
            request.repository_id,
            request.question,
        )
    except RepositoryNotIndexed as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (EmbeddingError, VectorStoreError, LLMError, RAGError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ChatResponse(
        answer=result.answer,
        repository_id=request.repository_id,
        sources=result.sources,
    )


@app.get("/repositories", response_model=list[RepositorySummary])
def repositories() -> list[RepositorySummary]:
    return [RepositorySummary(**item) for item in rag_service.list_repositories()]
