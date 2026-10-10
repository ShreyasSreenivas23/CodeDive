from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

from .loader import LoadedFile


@dataclass(frozen=True)
class Chunk:
    id: str
    content: str
    file: str
    language: str
    start_line: int
    end_line: int
    chunk_index: int


def chunk_documents(
    documents: Iterable[LoadedFile],
    *,
    repository_id: str,
    chunk_size: int = 1_000,
    overlap: int = 200,
    max_chunks: int = 5_000,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        for chunk_index, chunk in enumerate(
            chunk_text(document.content, chunk_size=chunk_size, overlap=overlap)
        ):
            content, start_line, end_line = chunk
            chunk_id = _chunk_id(repository_id, document.path, chunk_index, content)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=content,
                    file=document.path,
                    language=document.language,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_index=chunk_index,
                )
            )
            if len(chunks) >= max_chunks:
                return chunks
    return chunks


def chunk_text(text: str, *, chunk_size: int = 1_000, overlap: int = 200) -> list[tuple[str, int, int]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    if not text.strip():
        return []

    chunks: list[tuple[str, int, int]] = []
    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            end = _preferred_breakpoint(text, start, end, chunk_size)

        raw_content = text[start:end]
        content = raw_content.strip()
        if content:
            adjusted_start = start + (len(raw_content) - len(raw_content.lstrip()))
            adjusted_end = end - (len(raw_content) - len(raw_content.rstrip()))
            chunks.append(
                (
                    content,
                    _line_number_at(text, adjusted_start),
                    _line_number_at(text, max(adjusted_end - 1, adjusted_start)),
                )
            )

        if end >= text_length:
            break

        next_start = max(0, end - overlap)
        if next_start <= start:
            next_start = start + (chunk_size - overlap)
        start = next_start

    return chunks


def _preferred_breakpoint(text: str, start: int, end: int, chunk_size: int) -> int:
    minimum = min(end, start + max(1, int(chunk_size * 0.6)))
    newline = text.rfind("\n", minimum, end)
    whitespace = text.rfind(" ", minimum, end)
    breakpoint = max(newline, whitespace)
    if breakpoint > start:
        return breakpoint + 1
    return end


def _line_number_at(text: str, index: int) -> int:
    if index <= 0:
        return 1
    return text.count("\n", 0, min(index, len(text))) + 1


def _chunk_id(repository_id: str, file_path: str, chunk_index: int, content: str) -> str:
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    safe_file = hashlib.sha1(file_path.encode("utf-8")).hexdigest()[:10]
    return f"{repository_id}:{safe_file}:{chunk_index}:{digest}"
