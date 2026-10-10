from backend.chunker import chunk_documents, chunk_text
from backend.loader import LoadedFile


def test_chunk_text_handles_small_text():
    chunks = chunk_text("hello\nworld", chunk_size=100, overlap=10)

    assert chunks == [("hello\nworld", 1, 2)]


def test_chunk_text_overlaps_large_text():
    text = "a" * 80 + " " + "b" * 80 + " " + "c" * 80

    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) >= 2
    assert chunks[0][0][-20:] in text
    assert chunks[1][0][0] in {"a", "b"}


def test_chunk_documents_preserves_file_metadata():
    document = LoadedFile(path="src/main.py", content="x = 1\n" * 100, language="python", size_bytes=600)

    chunks = chunk_documents([document], repository_id="repo123", chunk_size=120, overlap=20)

    assert chunks
    assert chunks[0].file == "src/main.py"
    assert chunks[0].language == "python"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line >= chunks[0].start_line
