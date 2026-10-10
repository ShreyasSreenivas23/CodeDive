from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .chunker import chunk_documents
from .config import Settings
from .embeddings import EmbeddingError, get_embedding_service
from .github import CloneError, ClonedRepository, InvalidGitHubUrl, clone_repository
from .llm import LLMError, get_llm_service
from .loader import RepositoryLoadError, load_repository
from .schemas import SourceReference
from .vector_store import ChromaVectorStore, RetrievedChunk, VectorStoreError


class RAGError(Exception):
    """Raised for RAG pipeline failures."""


class RepositoryNotIndexed(RAGError):
    """Raised when a user asks about an unknown repository."""


@dataclass(frozen=True)
class AnalyzeResult:
    repository_id: str
    owner: str
    repository: str
    url: str
    files: int
    chunks: int


@dataclass(frozen=True)
class ChatResult:
    answer: str
    sources: list[SourceReference]


class RAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vector_store = ChromaVectorStore(settings.chroma_dir)
        self.registry_path = settings.storage_dir / "repositories.json"

    def analyze_repository(self, url: str) -> AnalyzeResult:
        repository = clone_repository(
            url,
            repos_dir=self.settings.repos_dir,
            timeout_seconds=self.settings.clone_timeout_seconds,
        )
        files = load_repository(
            repository.path,
            max_file_size_bytes=self.settings.max_file_size_bytes,
            max_files=self.settings.max_files,
        )
        if not files:
            raise RepositoryLoadError("No supported source or documentation files were found.")

        chunks = chunk_documents(
            files,
            repository_id=repository.repository_id,
            chunk_size=self.settings.chunk_size,
            overlap=self.settings.chunk_overlap,
            max_chunks=self.settings.max_chunks,
        )
        if not chunks:
            raise RAGError("No chunks could be created from this repository.")

        embedding_service = get_embedding_service(self.settings)
        embeddings = embedding_service.embed_documents([chunk.content for chunk in chunks])

        self.vector_store.reset_repository(repository.repository_id)
        self.vector_store.add_chunks(repository.repository_id, chunks, embeddings)
        self._record_repository(
            repository,
            file_count=len(files),
            chunk_count=len(chunks),
            embedding_provider=embedding_service.name,
            embedding_model=getattr(embedding_service, "model", embedding_service.name),
        )

        return AnalyzeResult(
            repository_id=repository.repository_id,
            owner=repository.owner,
            repository=repository.repository,
            url=repository.display_url,
            files=len(files),
            chunks=len(chunks),
        )

    def chat(self, repository_id: str, question: str) -> ChatResult:
        repository = self.get_repository(repository_id)
        if repository is None:
            raise RepositoryNotIndexed("Analyze this repository before asking questions.")

        embedding_service = get_embedding_service(self.settings)
        indexed_provider = repository.get("embedding_provider")
        indexed_model = repository.get("embedding_model")
        active_model = getattr(embedding_service, "model", embedding_service.name)
        if indexed_provider and indexed_model:
            if indexed_provider != embedding_service.name or indexed_model != active_model:
                raise RAGError(
                    "This repository was indexed with a different embedding model. "
                    "Analyze it again before asking questions."
                )

        question_embedding = embedding_service.embed_text(question)
        retrieved = self.vector_store.query(repository_id, question_embedding, k=self.settings.top_k)
        context = build_context(
            repository=f"{repository['owner']}/{repository['repository']}",
            chunks=retrieved,
            max_chars=self.settings.max_context_chars,
        )
        llm_service = get_llm_service(self.settings)
        answer = llm_service.answer(question=question, context=context, chunks=retrieved)

        return ChatResult(answer=answer, sources=unique_sources(retrieved))

    def list_repositories(self) -> list[dict[str, Any]]:
        registry = self._load_registry()
        return sorted(registry.values(), key=lambda item: item["indexed_at"], reverse=True)

    def get_repository(self, repository_id: str) -> dict[str, Any] | None:
        return self._load_registry().get(repository_id)

    def _record_repository(
        self,
        repository: ClonedRepository,
        *,
        file_count: int,
        chunk_count: int,
        embedding_provider: str,
        embedding_model: str,
    ) -> None:
        registry = self._load_registry()
        registry[repository.repository_id] = {
            "repository_id": repository.repository_id,
            "owner": repository.owner,
            "repository": repository.repository,
            "url": repository.display_url,
            "files": file_count,
            "chunks": chunk_count,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "indexed_at": datetime.now(UTC).isoformat(),
        }
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {}
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return data


def build_context(*, repository: str, chunks: list[RetrievedChunk], max_chars: int) -> str:
    sections = [f"Repository: {repository}"]
    seen: set[tuple[str, int | None, int | None]] = set()
    total_chars = len(sections[0])

    for chunk in chunks:
        key = (chunk.file, chunk.start_line, chunk.end_line)
        if key in seen:
            continue
        seen.add(key)

        location = chunk.file
        if chunk.start_line and chunk.end_line:
            location = f"{location}:{chunk.start_line}-{chunk.end_line}"
        section = f"\n\nFILE: {location}\n\n{chunk.content}\n---"
        if total_chars + len(section) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:
                sections.append(section[:remaining].rstrip())
            break
        sections.append(section)
        total_chars += len(section)

    return "".join(sections)


def unique_sources(chunks: list[RetrievedChunk]) -> list[SourceReference]:
    sources: list[SourceReference] = []
    seen: set[tuple[str, int | None, int | None]] = set()
    for chunk in chunks:
        key = (chunk.file, chunk.start_line, chunk.end_line)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            SourceReference(
                file=chunk.file,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )
        )
    return sources
