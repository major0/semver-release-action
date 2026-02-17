"""Shared pytest fixtures for the test suite."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def make_tag(name: str, commit_sha: str = "default_sha") -> MagicMock:
    """Create a mock tag object with the given name.

    This is a shared helper for creating mock GitHub tag objects
    used across multiple test modules.

    Args:
        name: The tag name (e.g., 'v1.2.0').
        commit_sha: The SHA of the commit the tag points to.
    """
    tag = MagicMock()
    tag.name = name
    tag.commit = MagicMock()
    tag.commit.sha = commit_sha
    return tag


def make_commit(sha: str) -> MagicMock:
    """Create a mock commit object with the given SHA.

    This is a shared helper for creating mock GitHub commit objects
    used across multiple test modules.
    """
    commit = MagicMock()
    commit.sha = sha
    return commit


@pytest.fixture
def mock_github_api() -> MagicMock:
    """Create a mock GitHubAPI instance for unit tests."""
    mock_api = MagicMock()
    mock_api.list_tags.return_value = []
    mock_api.create_tag.return_value = None
    mock_api.update_tag.return_value = None
    mock_api.get_branch_commits.return_value = []
    return mock_api


@pytest.fixture
def mock_github_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set up mock GitHub environment variables."""
    env_vars = {
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF_NAME": "release/v1.0",
        "GITHUB_REF_TYPE": "branch",
        "GITHUB_SHA": "abc123def456",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_OUTPUT": "/dev/null",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_pygithub() -> Generator[dict[str, Any], None, None]:
    """Patch PyGithub for unit tests."""
    with patch("github.Github") as mock_github:
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo
        yield {"github": mock_github, "repo": mock_repo}


@pytest.fixture
def sample_tags() -> list[str]:
    """Sample tag data for testing."""
    return [
        "v1.0.0-rc1",
        "v1.0.0-rc2",
        "v1.0.0",
        "v1.0.1",
        "v1.1.0-rc1",
        "v2.0.0-rc1",
    ]


@pytest.fixture
def sample_branches() -> dict[str, list[str]]:
    """Sample branch names for testing."""
    return {
        "valid": [
            "release/v1.0",
            "release/v1.2",
            "release/v0.1",
            "release/v10.20",
        ],
        "invalid": [
            "release/v01.2",  # Leading zero
            "release/1.2",  # Missing 'v'
            "feature/v1.2",  # Wrong prefix
            "release/v1",  # Missing minor
            "release/v1.2.3",  # Has patch
            "main",
            "develop",
        ],
    }
