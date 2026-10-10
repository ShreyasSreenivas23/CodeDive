from backend.config import Settings


def test_settings_accepts_gemini_key_alias(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings()

    assert settings.gemini_api_key == "gemini-test-key"
    assert settings.has_gemini_key is True


def test_settings_accepts_gemini_provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings(llm_provider="gemini", embedding_provider="gemini")

    assert settings.llm_provider == "gemini"
    assert settings.embedding_provider == "gemini"
    assert settings.has_gemini_key is True
