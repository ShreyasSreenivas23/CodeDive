from backend.rag import build_context, unique_sources
from backend.vector_store import RetrievedChunk


def test_build_context_deduplicates_and_limits_chunks():
    chunks = [
        RetrievedChunk("alpha", "a.py", 1, 2, "python", 0.9),
        RetrievedChunk("alpha duplicate", "a.py", 1, 2, "python", 0.8),
        RetrievedChunk("beta", "b.py", 3, 4, "python", 0.7),
    ]

    context = build_context(repository="owner/repo", chunks=chunks, max_chars=500)

    assert "Repository: owner/repo" in context
    assert context.count("FILE: a.py:1-2") == 1
    assert "FILE: b.py:3-4" in context


def test_unique_sources_preserves_retrieval_order():
    chunks = [
        RetrievedChunk("alpha", "a.py", 1, 2, "python", 0.9),
        RetrievedChunk("alpha duplicate", "a.py", 1, 2, "python", 0.8),
        RetrievedChunk("beta", "b.py", 3, 4, "python", 0.7),
    ]

    sources = unique_sources(chunks)

    assert [source.file for source in sources] == ["a.py", "b.py"]
