"""Unit tests for github_api.py - GitHubAPI wrapper methods."""

from unittest.mock import MagicMock, patch

import pytest
from github.GithubException import GithubException

from src.github_api import GitHubAPI


class TestGitHubAPIInit:
    """Tests for GitHubAPI initialization and token handling."""

    def test_init_with_explicit_token_and_repo(self):
        """GitHubAPI initializes with explicit token and repository."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_github.return_value.get_repo.return_value = mock_repo

            GitHubAPI(token="test-token", repository="owner/repo")

            mock_github.assert_called_once_with("test-token")
            mock_github.return_value.get_repo.assert_called_once_with("owner/repo")

    def test_init_with_env_vars(self, monkeypatch):
        """GitHubAPI uses environment variables when parameters not provided."""
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "env-owner/env-repo")

        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_github.return_value.get_repo.return_value = mock_repo

            GitHubAPI()

            mock_github.assert_called_once_with("env-token")
            mock_github.return_value.get_repo.assert_called_once_with("env-owner/env-repo")

    def test_init_missing_token_raises_error(self, monkeypatch):
        """GitHubAPI raises ValueError when token is missing."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

        with pytest.raises(ValueError, match="GitHub token is required"):
            GitHubAPI()

    def test_init_missing_repository_raises_error(self, monkeypatch):
        """GitHubAPI raises ValueError when repository is missing."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

        with pytest.raises(ValueError, match="Repository is required"):
            GitHubAPI()


class TestListTags:
    """Tests for GitHubAPI.list_tags method."""

    def test_list_tags_returns_all_tags(self):
        """list_tags returns all repository tags."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_tags = [MagicMock(name="v1.0.0"), MagicMock(name="v1.0.1")]
            mock_repo.get_tags.return_value = mock_tags
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.list_tags()

            assert result == mock_tags
            mock_repo.get_tags.assert_called_once()

    def test_list_tags_empty_repository(self):
        """list_tags returns empty list for repository with no tags."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_repo.get_tags.return_value = []
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.list_tags()

            assert result == []


class TestCreateTag:
    """Tests for GitHubAPI.create_tag method."""

    def test_create_tag_creates_annotated_tag(self):
        """create_tag creates annotated tag with reference."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_tag_obj = MagicMock(sha="tag-sha-123")
            mock_repo.create_git_tag.return_value = mock_tag_obj
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            api.create_tag("v1.0.0", "commit-sha-456", "Release message")

            mock_repo.create_git_tag.assert_called_once_with(
                tag="v1.0.0",
                message="Release message",
                object="commit-sha-456",
                type="commit",
            )
            mock_repo.create_git_ref.assert_called_once_with(
                ref="refs/tags/v1.0.0",
                sha="tag-sha-123",
            )

    def test_create_tag_default_message(self):
        """create_tag uses default message when not provided."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_tag_obj = MagicMock(sha="tag-sha-123")
            mock_repo.create_git_tag.return_value = mock_tag_obj
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            api.create_tag("v1.0.0", "commit-sha-456")

            mock_repo.create_git_tag.assert_called_once_with(
                tag="v1.0.0",
                message="Release v1.0.0",
                object="commit-sha-456",
                type="commit",
            )

    def test_create_tag_api_failure(self):
        """create_tag raises GithubException on API failure."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_repo.create_git_tag.side_effect = GithubException(422, "Tag exists", None)
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")

            with pytest.raises(GithubException):
                api.create_tag("v1.0.0", "commit-sha-456")


class TestUpdateTag:
    """Tests for GitHubAPI.update_tag method."""

    def test_update_tag_force_pushes(self):
        """update_tag force-pushes tag to new commit."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_ref = MagicMock()
            mock_repo.get_git_ref.return_value = mock_ref
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            api.update_tag("v1", "new-commit-sha")

            mock_repo.get_git_ref.assert_called_once_with("tags/v1")
            mock_ref.edit.assert_called_once_with(sha="new-commit-sha", force=True)

    def test_update_tag_nonexistent_tag(self):
        """update_tag raises GithubException for nonexistent tag."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_repo.get_git_ref.side_effect = GithubException(404, "Not Found", None)
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")

            with pytest.raises(GithubException):
                api.update_tag("nonexistent", "commit-sha")


class TestGetBranchCommits:
    """Tests for GitHubAPI.get_branch_commits method."""

    def test_get_branch_commits_returns_commits(self):
        """get_branch_commits returns list of commits from branch."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_commits = [MagicMock(sha="abc123"), MagicMock(sha="def456")]
            mock_repo.get_commits.return_value = mock_commits
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.get_branch_commits("release/v1.0")

            assert result == mock_commits
            mock_repo.get_commits.assert_called_once_with(sha="release/v1.0")

    def test_get_branch_commits_nonexistent_branch(self):
        """get_branch_commits raises GithubException for nonexistent branch."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_repo.get_commits.side_effect = GithubException(404, "Branch not found", None)
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")

            with pytest.raises(GithubException):
                api.get_branch_commits("nonexistent/branch")


class TestTagExists:
    """Tests for GitHubAPI.tag_exists method."""

    def test_tag_exists_returns_true(self):
        """tag_exists returns True when tag exists."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_repo.get_git_ref.return_value = MagicMock()
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.tag_exists("v1.0.0")

            assert result is True
            mock_repo.get_git_ref.assert_called_once_with("tags/v1.0.0")

    def test_tag_exists_returns_false(self):
        """tag_exists returns False when tag doesn't exist."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_repo.get_git_ref.side_effect = GithubException(404, "Not Found", None)
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.tag_exists("nonexistent")

            assert result is False


class TestGetTagCommitSha:
    """Tests for GitHubAPI.get_tag_commit_sha method."""

    def test_get_tag_commit_sha_lightweight_tag(self):
        """get_tag_commit_sha returns SHA for lightweight tag."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_ref = MagicMock()
            mock_ref.object.sha = "commit-sha-123"
            mock_ref.object.type = "commit"
            mock_repo.get_git_ref.return_value = mock_ref
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.get_tag_commit_sha("v1.0.0")

            assert result == "commit-sha-123"

    def test_get_tag_commit_sha_annotated_tag(self):
        """get_tag_commit_sha dereferences annotated tag to commit SHA."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_ref = MagicMock()
            mock_ref.object.sha = "tag-object-sha"
            mock_ref.object.type = "tag"
            mock_tag_obj = MagicMock()
            mock_tag_obj.object.sha = "actual-commit-sha"
            mock_repo.get_git_ref.return_value = mock_ref
            mock_repo.get_git_tag.return_value = mock_tag_obj
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.get_tag_commit_sha("v1.0.0")

            assert result == "actual-commit-sha"
            mock_repo.get_git_tag.assert_called_once_with("tag-object-sha")

    def test_get_tag_commit_sha_nonexistent_tag(self):
        """get_tag_commit_sha returns None for nonexistent tag."""
        with patch("src.github_api.Github") as mock_github:
            mock_repo = MagicMock()
            mock_repo.get_git_ref.side_effect = GithubException(404, "Not Found", None)
            mock_github.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI(token="test-token", repository="owner/repo")
            result = api.get_tag_commit_sha("nonexistent")

            assert result is None
