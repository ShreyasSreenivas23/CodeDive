from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "codedive"
    frontend_origin: str = "http://localhost:5173"

    storage_dir: Path = PROJECT_ROOT / "storage"
    chroma_dir: Path = PROJECT_ROOT / "storage" / "chroma"
    repos_dir: Path = PROJECT_ROOT / "storage" / "repos"

    max_file_size_bytes: int = 512_000
    max_files: int = 1_000
    max_chunks: int = 5_000
    chunk_size: int = 1_000
    chunk_overlap: int = 200
    clone_timeout_seconds: int = 120

    top_k: int = 5
    max_context_chars: int = 12_000
    max_answer_tokens: int = 700

    embedding_provider: str = Field(default="local", pattern="^(auto|openai|gemini|ollama|local)$")
    llm_provider: str = Field(default="ollama", pattern="^(auto|openai|gemini|ollama|local)$")

    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "qwen3-embedding:latest"
    ollama_llm_model: str = "qwen2.5-coder:7b-instruct"
    ollama_timeout_seconds: float = 120.0
    ollama_keep_alive: str = "5m"

    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    openai_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_llm_model: str = "gemini-3.5-flash-lite"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_llm_model: str = "gpt-5.6"

    local_embedding_dimensions: int = 384

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def api_key(self) -> str | None:
        return (self.gemini_api_key or self.openai_api_key or "").strip() or None

    @property
    def has_openai_key(self) -> bool:
        return bool(self.api_key)

    @property
    def has_gemini_key(self) -> bool:
        return bool((self.gemini_api_key or self.openai_api_key or "").strip())


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for path_field in ("storage_dir", "chroma_dir", "repos_dir"):
        path = getattr(settings, path_field)
        if not path.is_absolute():
            setattr(settings, path_field, PROJECT_ROOT / path)

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    settings.repos_dir.mkdir(parents=True, exist_ok=True)
    return settings
