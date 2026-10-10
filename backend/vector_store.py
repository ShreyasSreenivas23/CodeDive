from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .chunker import Chunk


class VectorStoreError(Exception):
    """Raised when vector-store operations fail."""


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    file: str
    start_line: int | None
    end_line: int | None
    language: str | None
    score: float | None


class ChromaVectorStore:
    def __init__(self, persist_dir: Path) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise VectorStoreError("Install chromadb to use vector storage.") from exc

        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir))

    def reset_repository(self, repository_id: str) -> None:
        name = collection_name(repository_id)
        try:
            self.client.delete_collection(name=name)
        except Exception:
            pass

    def add_chunks(
        self,
        repository_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        *,
        batch_size: int = 200,
    ) -> None:
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunk and embedding counts do not match.")
        if not chunks:
            raise VectorStoreError("No chunks were provided for indexing.")

        collection = self.client.get_or_create_collection(name=collection_name(repository_id))
        for start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[start : start + batch_size]
            batch_embeddings = embeddings[start : start + batch_size]
            try:
                collection.upsert(
                    ids=[chunk.id for chunk in batch_chunks],
                    documents=[chunk.content for chunk in batch_chunks],
                    embeddings=batch_embeddings,
                    metadatas=[
                        {
                            "file": chunk.file,
                            "language": chunk.language,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "chunk_index": chunk.chunk_index,
                        }
                        for chunk in batch_chunks
                    ],
                )
            except Exception as exc:
                raise VectorStoreError(f"Could not add chunks to Chroma: {exc}") from exc

    def query(self, repository_id: str, query_embedding: list[float], *, k: int = 5) -> list[RetrievedChunk]:
        collection = self.client.get_or_create_collection(name=collection_name(repository_id))
        try:
            results: dict[str, Any] = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"Could not query Chroma: {exc}") from exc

        documents = _first(results.get("documents"))
        metadatas = _first(results.get("metadatas"))
        distances = _first(results.get("distances"))

        retrieved: list[RetrievedChunk] = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
            distance = distances[index] if index < len(distances) else None
            retrieved.append(
                RetrievedChunk(
                    content=document,
                    file=str(metadata.get("file", "unknown")),
                    start_line=_as_int(metadata.get("start_line")),
                    end_line=_as_int(metadata.get("end_line")),
                    language=metadata.get("language"),
                    score=_distance_to_score(distance),
                )
            )

        return retrieved


def collection_name(repository_id: str) -> str:
    cleaned = "".join(character if character.isalnum() else "_" for character in repository_id)
    return f"repo_{cleaned}"


def _first(value: Any) -> list[Any]:
    if isinstance(value, list) and value:
        return value[0] or []
    return []


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _distance_to_score(distance: Any) -> float | None:
    if distance is None:
        return None
    try:
        numeric = float(distance)
    except (TypeError, ValueError):
        return None
    return 1.0 / (1.0 + max(numeric, 0.0))
