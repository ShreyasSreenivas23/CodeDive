import pytest

from backend.github import InvalidGitHubUrl, parse_github_url


def test_parse_github_url_normalizes_clone_url():
    parsed = parse_github_url("https://github.com/openai/openai-python")

    assert parsed.owner == "openai"
    assert parsed.repository == "openai-python"
    assert parsed.clone_url == "https://github.com/openai/openai-python.git"
    assert parsed.display_url == "https://github.com/openai/openai-python"
    assert len(parsed.repository_id) == 12


def test_parse_github_url_accepts_nested_github_url():
    parsed = parse_github_url("https://github.com/openai/openai-python/issues/1")

    assert parsed.owner == "openai"
    assert parsed.repository == "openai-python"


def test_parse_github_url_rejects_non_github_host():
    with pytest.raises(InvalidGitHubUrl):
        parse_github_url("https://example.com/openai/openai-python")


def test_parse_github_url_rejects_missing_repository():
    with pytest.raises(InvalidGitHubUrl):
        parse_github_url("https://github.com/openai")
