from __future__ import annotations

import re
from abc import ABC, abstractmethod

import httpx

from .config import Settings
from .vector_store import RetrievedChunk


SYSTEM_PROMPT = """You are an assistant analyzing a GitHub repository.

Answer the user's question using only the provided repository context.
Do not invent information that is not supported by the context.
If the context is insufficient, say that you do not have enough information.
Keep the answer concise and mention relevant files when useful."""


class LLMError(Exception):
    """Raised when the LLM cannot produce an answer."""


class LLMService(ABC):
    name: str

    @abstractmethod
    def answer(self, *, question: str, context: str, chunks: list[RetrievedChunk]) -> str:
        raise NotImplementedError


class LocalExtractiveLLMService(LLMService):
    name = "local-extractive"

    def answer(self, *, question: str, context: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "I do not have enough repository context to answer that question."

        keywords = _keywords(question)
        excerpts = _select_excerpts(chunks, keywords)
        source_files = ", ".join(dict.fromkeys(chunk.file for chunk in chunks[:3]))

        if not excerpts:
            return (
                "I found related repository files, but the retrieved context does not contain "
                f"enough direct evidence to answer confidently. The closest files are: {source_files}."
            )

        excerpt_text = "\n".join(f"- {excerpt}" for excerpt in excerpts[:5])
        return (
            "Based on the retrieved repository context, the most relevant evidence is in "
            f"{source_files}.\n\nKey excerpts:\n{excerpt_text}\n\n"
            "Set GEMINI_API_KEY and use Gemini mode for a synthesized natural-language answer."
        )


class OpenAILLMService(LLMService):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        max_answer_tokens: int,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise LLMError("GEMINI_API_KEY is required for Gemini answers.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("Install the openai package to use Gemini answers.") from exc

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_answer_tokens = max_answer_tokens

    def answer(self, *, question: str, context: str, chunks: list[RetrievedChunk]) -> str:
        if not context.strip():
            return "I do not have enough repository context to answer that question."

        prompt = f"Repository context:\n\n{context}\n\nUser question:\n\n{question}"
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=self.max_answer_tokens,
            )
        except Exception as exc:  # SDK raises provider-specific subclasses.
            raise LLMError(f"Gemini response request failed: {exc}") from exc

        answer = response.choices[0].message.content
        if not answer:
            raise LLMError("Gemini returned an empty answer.")
        return str(answer).strip()


class OllamaLLMService(LLMService):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        keep_alive: str,
        max_answer_tokens: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.keep_alive = keep_alive
        self.max_answer_tokens = max_answer_tokens

    def answer(self, *, question: str, context: str, chunks: list[RetrievedChunk]) -> str:
        if not context.strip():
            return "I do not have enough repository context to answer that question."

        prompt = f"Repository context:\n\n{context}\n\nUser question:\n\n{question}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.1,
                "num_predict": self.max_answer_tokens,
            },
        }

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMError(_ollama_error_message(exc.response, "chat")) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach Ollama at {self.base_url}: {exc}") from exc

        data = response.json()
        message = data.get("message")
        answer = message.get("content") if isinstance(message, dict) else None
        if not answer:
            answer = data.get("response")
        if not answer:
            raise LLMError("Ollama returned an empty answer.")
        return str(answer).strip()


def get_llm_service(settings: Settings) -> LLMService:
    provider = settings.llm_provider.lower()
    if provider in {"gemini", "openai"} or (provider == "auto" and settings.has_gemini_key):
        return OpenAILLMService(
            api_key=settings.gemini_api_key or settings.openai_api_key or "",
            model=settings.gemini_llm_model if provider in {"gemini", "auto"} else settings.openai_llm_model,
            max_answer_tokens=settings.max_answer_tokens,
            base_url=settings.gemini_base_url if provider in {"gemini", "auto"} else None,
        )
    if provider in {"ollama", "auto"}:
        return OllamaLLMService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_llm_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
            max_answer_tokens=settings.max_answer_tokens,
        )
    return LocalExtractiveLLMService()


def _ollama_error_message(response: httpx.Response, operation: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    detail = payload.get("error") if isinstance(payload, dict) else None
    if detail:
        return f"Ollama {operation} request failed: {detail}"
    return f"Ollama {operation} request failed with HTTP {response.status_code}."


def _keywords(question: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "does",
        "for",
        "how",
        "in",
        "is",
        "of",
        "the",
        "to",
        "what",
        "where",
        "with",
    }
    return {
        token
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", question.lower())
        if len(token) > 2 and token not in stopwords
    }


def _select_excerpts(chunks: list[RetrievedChunk], keywords: set[str]) -> list[str]:
    excerpts: list[str] = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
        ranked = sorted(
            lines,
            key=lambda line: sum(1 for keyword in keywords if keyword in line.lower()),
            reverse=True,
        )
        for line in ranked[:2]:
            if keywords and not any(keyword in line.lower() for keyword in keywords):
                continue
            excerpt = line if len(line) <= 220 else f"{line[:217]}..."
            if excerpt not in excerpts:
                excerpts.append(excerpt)
    return excerpts
