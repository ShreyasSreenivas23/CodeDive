from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


INCLUDED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".sql",
    ".css",
    ".scss",
    ".html",
    ".sh",
    ".ps1",
}

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    "target",
    ".next",
    ".turbo",
    ".pytest_cache",
}

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp4",
    ".mov",
    ".avi",
    ".zip",
    ".gz",
    ".tar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pdf",
}

INCLUDED_FILENAMES = {
    "readme",
    "license",
    "notice",
    "changelog",
    "contributing",
    "code_of_conduct",
    "security",
    "dockerfile",
    "makefile",
}

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".css": "css",
    ".scss": "scss",
    ".html": "html",
    ".sh": "shell",
    ".ps1": "powershell",
}

LANGUAGE_BY_FILENAME = {
    "readme": "markdown",
    "license": "text",
    "notice": "text",
    "changelog": "markdown",
    "contributing": "markdown",
    "code_of_conduct": "markdown",
    "security": "markdown",
    "dockerfile": "dockerfile",
    "makefile": "makefile",
}


@dataclass(frozen=True)
class LoadedFile:
    path: str
    content: str
    language: str
    size_bytes: int


class RepositoryLoadError(Exception):
    """Raised when repository files cannot be loaded."""


def load_repository(
    repo_path: Path,
    *,
    max_file_size_bytes: int = 512_000,
    max_files: int = 1_000,
) -> list[LoadedFile]:
    root = Path(repo_path)
    if not root.exists() or not root.is_dir():
        raise RepositoryLoadError(f"Repository path does not exist: {repo_path}")

    files: list[LoadedFile] = []
    for path in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break

        if not path.is_file() or path.is_symlink():
            continue

        if _has_ignored_directory(path, root):
            continue

        extension = path.suffix.lower()
        filename = path.name.lower()
        if extension in BINARY_EXTENSIONS:
            continue
        if extension not in INCLUDED_EXTENSIONS and filename not in INCLUDED_FILENAMES:
            continue

        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue

        if size_bytes > max_file_size_bytes:
            continue

        content = _read_text_file(path)
        if content is None:
            continue

        files.append(
            LoadedFile(
                path=path.relative_to(root).as_posix(),
                content=content,
                language=LANGUAGE_BY_EXTENSION.get(extension)
                or LANGUAGE_BY_FILENAME.get(filename, "text"),
                size_bytes=size_bytes,
            )
        )

    return files


def _has_ignored_directory(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in IGNORED_DIRECTORIES for part in relative_parts[:-1])


def _read_text_file(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if b"\0" in data[:4096]:
        return None

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")
