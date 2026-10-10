from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


GITHUB_HOSTS = {"github.com", "www.github.com"}
REPOSITORY_PART_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class GitHubRepositoryError(Exception):
    """Base class for GitHub repository ingestion errors."""


class InvalidGitHubUrl(GitHubRepositoryError):
    """Raised when a URL is not a usable public GitHub repository URL."""


class CloneError(GitHubRepositoryError):
    """Raised when git clone fails."""


@dataclass(frozen=True)
class ParsedRepositoryUrl:
    owner: str
    repository: str
    clone_url: str
    display_url: str
    repository_id: str


@dataclass(frozen=True)
class ClonedRepository:
    owner: str
    repository: str
    repository_id: str
    clone_url: str
    display_url: str
    path: Path


def parse_github_url(url: str) -> ParsedRepositoryUrl:
    raw_url = url.strip()
    parsed = urlparse(raw_url)

    if parsed.scheme not in {"http", "https"}:
        raise InvalidGitHubUrl("Use an http or https GitHub repository URL.")

    host = parsed.netloc.lower()
    if host not in GITHUB_HOSTS:
        raise InvalidGitHubUrl("Only github.com repository URLs are supported.")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise InvalidGitHubUrl("GitHub URL must include an owner and repository name.")

    owner = parts[0]
    repository = parts[1]
    if repository.endswith(".git"):
        repository = repository[:-4]

    if not owner or not repository:
        raise InvalidGitHubUrl("GitHub URL must include an owner and repository name.")

    if owner in {".", ".."} or repository in {".", ".."}:
        raise InvalidGitHubUrl("Repository owner and name cannot be relative paths.")

    if not REPOSITORY_PART_RE.match(owner) or not REPOSITORY_PART_RE.match(repository):
        raise InvalidGitHubUrl("Repository owner and name contain unsupported characters.")

    identity = f"{owner}/{repository}".lower()
    repository_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return ParsedRepositoryUrl(
        owner=owner,
        repository=repository,
        clone_url=f"https://github.com/{owner}/{repository}.git",
        display_url=f"https://github.com/{owner}/{repository}",
        repository_id=repository_id,
    )


def clone_repository(url: str, repos_dir: Path, timeout_seconds: int = 120) -> ClonedRepository:
    parsed = parse_github_url(url)
    repos_dir.mkdir(parents=True, exist_ok=True)
    target_path = repos_dir / parsed.repository_id

    if target_path.exists():
        remove_repository(target_path, repos_dir)

    command = ["git", "clone", "--depth", "1", parsed.clone_url, str(target_path)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        remove_repository(target_path, repos_dir)
        raise CloneError("Timed out while cloning the repository.") from exc
    except OSError as exc:
        raise CloneError("Could not run git. Make sure git is installed and on PATH.") from exc

    if result.returncode != 0:
        remove_repository(target_path, repos_dir)
        message = (result.stderr or result.stdout or "Git clone failed.").strip()
        raise CloneError(message)

    return ClonedRepository(
        owner=parsed.owner,
        repository=parsed.repository,
        repository_id=parsed.repository_id,
        clone_url=parsed.clone_url,
        display_url=parsed.display_url,
        path=target_path,
    )


def remove_repository(path: Path, repos_dir: Path) -> None:
    if not path.exists():
        return

    resolved_path = path.resolve()
    resolved_repos_dir = repos_dir.resolve()
    if not resolved_path.is_relative_to(resolved_repos_dir):
        raise ValueError(f"Refusing to remove path outside repositories directory: {path}")

    shutil.rmtree(resolved_path, onerror=_handle_remove_readonly)


def _handle_remove_readonly(function, path: str, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)
