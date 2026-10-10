from pathlib import Path

from backend.loader import load_repository


def test_load_repository_filters_useful_text_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Hello", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x89PNG")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "index.js").write_text("ignored", encoding="utf-8")

    files = load_repository(tmp_path)

    assert [file.path for file in files] == ["LICENSE", "README.md", "src/main.py"]


def test_load_repository_skips_large_files(tmp_path: Path):
    (tmp_path / "small.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "large.py").write_text("x" * 20, encoding="utf-8")

    files = load_repository(tmp_path, max_file_size_bytes=10)

    assert [file.path for file in files] == ["small.py"]


def test_load_repository_skips_binary_text_extension(tmp_path: Path):
    (tmp_path / "bad.py").write_bytes(b"abc\x00def")

    files = load_repository(tmp_path)

    assert files == []
