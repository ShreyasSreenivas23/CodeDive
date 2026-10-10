from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable

import httpx

from .config import Settings


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+")


class EmbeddingError(Exception):
    """Raised when embeddings cannot be generated."""


class EmbeddingService(ABC):
    name: str

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        raise NotImplementedError


class LocalHashEmbeddingService(EmbeddingService):
    name = "local-hash"

    def __init__(self, dimensions: int = 384) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions
        self.model = f"local-hash:{dimensions}"

    def embed_text(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_RE.findall(text.lower())
        if not tokens:
            vector[0] = 1.0
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] % 2 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]


class OpenAIEmbeddingService(EmbeddingService):
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str | None = None, batch_size: int = 64) -> None:
        if not api_key:
            raise EmbeddingError("GEMINI_API_KEY is required for Gemini embeddings.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise EmbeddingError("Install the openai package to use Gemini embeddings.") from exc

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.batch_size = batch_size

    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        documents = [text if text.strip() else " " for text in texts]
        if not documents:
            return []

        embeddings: list[list[float]] = []
        for start in range(0, len(documents), self.batch_size):
            batch = documents[start : start + self.batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float",
                )
            except Exception as exc:  # SDK raises provider-specific subclasses.
                raise EmbeddingError(f"Gemini embedding request failed: {exc}") from exc

            ordered = sorted(response.data, key=lambda item: item.index)
            embeddings.extend([list(item.embedding) for item in ordered])

        return embeddings


class OllamaEmbeddingService(EmbeddingService):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        keep_alive: str = "5m",
        batch_size: int = 32,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.keep_alive = keep_alive
        self.batch_size = batch_size

    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        documents = [text if text.strip() else " " for text in texts]
        if not documents:
            return []

        embeddings: list[list[float]] = []
        for start in range(0, len(documents), self.batch_size):
            batch = documents[start : start + self.batch_size]
            payload = {
                "model": self.model,
                "input": batch,
                "truncate": True,
                "keep_alive": self.keep_alive,
            }
            try:
                response = httpx.post(
                    f"{self.base_url}/api/embed",
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EmbeddingError(_ollama_error_message(exc.response)) from exc
            except httpx.HTTPError as exc:
                raise EmbeddingError(f"Could not reach Ollama at {self.base_url}: {exc}") from exc

            data = response.json()
            batch_embeddings = data.get("embeddings")
            if not isinstance(batch_embeddings, list):
                raise EmbeddingError("Ollama did not return embeddings.")
            if len(batch_embeddings) != len(batch):
                raise EmbeddingError("Ollama embedding count did not match the input count.")
            embeddings.extend([list(embedding) for embedding in batch_embeddings])

        return embeddings


def get_embedding_service(settings: Settings) -> EmbeddingService:
    provider = settings.embedding_provider.lower()
    if provider in {"gemini", "openai"} or (provider == "auto" and settings.has_gemini_key):
        return OpenAIEmbeddingService(
            api_key=settings.gemini_api_key or settings.openai_api_key or "",
            model=settings.gemini_embedding_model if provider in {"gemini", "auto"} else settings.openai_embedding_model,
            base_url=settings.gemini_base_url if provider in {"gemini", "auto"} else None,
        )
    if provider in {"ollama", "auto"}:
        return OllamaEmbeddingService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
        )
    return LocalHashEmbeddingService(dimensions=settings.local_embedding_dimensions)


def _ollama_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    detail = payload.get("error") if isinstance(payload, dict) else None
    if detail:
        return f"Ollama embedding request failed: {detail}"
    return f"Ollama embedding request failed with HTTP {response.status_code}."
