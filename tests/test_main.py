# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Unit tests for main.py prefix configuration handling.

Tests prefix input reading, validation, tag creation with custom prefixes,
and alias skip logic when prefixes match.

Validates: Requirements 5.5, 10.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from src.main import (
    ActionInputs,
    GitHubContext,
    handle_branch_create,
    handle_commit_push,
    handle_tag_push,
    parse_inputs,
)
from tests.conftest import make_commit, make_tag

if TYPE_CHECKING:
    pass


class TestParseInputsPrefixes:
    """Tests for parse_inputs() prefix handling.

    Validates: Requirements 1.6, 2.7, 4.3, 4.4, 5.5
    """

    def test_default_release_prefix(self) -> None:
        """Test that default release-prefix is 'release/v'."""
        inputs = parse_inputs([])
        assert inputs.release_prefix == "release/v"

    def test_default_tag_prefix(self) -> None:
        """Test that default tag-prefix is 'v'."""
        inputs = parse_inputs([])
        assert inputs.tag_prefix == "v"

    def test_custom_release_prefix_cli(self) -> None:
        """Test custom release-prefix via CLI argument."""
        inputs = parse_inputs(["--release-prefix", "v"])
        assert inputs.release_prefix == "v"

    def test_custom_tag_prefix_cli(self) -> None:
        """Test custom tag-prefix via CLI argument."""
        inputs = parse_inputs(["--tag-prefix", "pkg-v"])
        assert inputs.tag_prefix == "pkg-v"

    def test_custom_prefixes_combined(self) -> None:
        """Test both custom prefixes together."""
        inputs = parse_inputs(["--release-prefix", "pkg-", "--tag-prefix", "pkg-"])
        assert inputs.release_prefix == "pkg-"
        assert inputs.tag_prefix == "pkg-"

    def test_release_prefix_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test release-prefix from environment variable."""
        monkeypatch.setenv("INPUT_RELEASE_PREFIX", "api/")
        inputs = parse_inputs([])
        assert inputs.release_prefix == "api/"

    def test_tag_prefix_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test tag-prefix from environment variable."""
        monkeypatch.setenv("INPUT_TAG_PREFIX", "api-")
        inputs = parse_inputs([])
        assert inputs.tag_prefix == "api-"

    def test_cli_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that CLI arguments override environment variables."""
        monkeypatch.setenv("INPUT_RELEASE_PREFIX", "env-prefix/")
        monkeypatch.setenv("INPUT_TAG_PREFIX", "env-")
        inputs = parse_inputs(["--release-prefix", "cli/", "--tag-prefix", "cli-"])
        assert inputs.release_prefix == "cli/"
        assert inputs.tag_prefix == "cli-"

    def test_invalid_release_prefix_exits(self) -> None:
        """Test that invalid release-prefix causes exit."""
        with pytest.raises(SystemExit) as exc_info:
            parse_inputs(["--release-prefix", "bad..prefix"])
        assert exc_info.value.code == 1

    def test_invalid_tag_prefix_exits(self) -> None:
        """Test that invalid tag-prefix causes exit."""
        with pytest.raises(SystemExit) as exc_info:
            parse_inputs(["--tag-prefix", "bad~prefix"])
        assert exc_info.value.code == 1

    def test_empty_release_prefix_exits(self) -> None:
        """Test that empty release-prefix causes exit."""
        with pytest.raises(SystemExit) as exc_info:
            parse_inputs(["--release-prefix", ""])
        assert exc_info.value.code == 1

    def test_empty_tag_prefix_exits(self) -> None:
        """Test that empty tag-prefix causes exit."""
        with pytest.raises(SystemExit) as exc_info:
            parse_inputs(["--tag-prefix", ""])
        assert exc_info.value.code == 1


class TestTagCreationWithCustomPrefixes:
    """Tests for tag creation with custom prefixes.

    Validates: Requirements 2.3, 2.4, 5.5
    """

    def test_branch_create_with_short_prefix(self, mock_github_api: MagicMock) -> None:
        """Test branch creation with short 'v' prefix creates correct RC tag."""
        mock_github_api.list_tags.return_value = []

        context = GitHubContext(
            event_name="create",
            ref_name="v1.2",
            ref_type="branch",
            sha="abc123def456",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="v",
            tag_prefix="v",
        )

        outputs = handle_branch_create(mock_github_api, context, inputs)

        assert outputs.tag == "v1.2.0-rc1"
        assert outputs.tag_type == "rc"
        mock_github_api.create_tag.assert_called_once_with(
            "v1.2.0-rc1",
            "abc123def456",
            "Release candidate v1.2.0-rc1",
        )

    def test_branch_create_with_custom_prefix(self, mock_github_api: MagicMock) -> None:
        """Test branch creation with custom 'pkg-' prefix."""
        mock_github_api.list_tags.return_value = []

        context = GitHubContext(
            event_name="create",
            ref_name="pkg-1.0",
            ref_type="branch",
            sha="abc123",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="pkg-",
            tag_prefix="pkg-",
        )

        outputs = handle_branch_create(mock_github_api, context, inputs)

        assert outputs.tag == "pkg-1.0.0-rc1"
        assert outputs.tag_type == "rc"

    def test_branch_create_with_different_prefixes(self, mock_github_api: MagicMock) -> None:
        """Test branch creation with different release and tag prefixes."""
        mock_github_api.list_tags.return_value = []

        context = GitHubContext(
            event_name="create",
            ref_name="pkg-release/v2.0",
            ref_type="branch",
            sha="abc123",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="pkg-release/v",
            tag_prefix="pkg-v",
        )

        outputs = handle_branch_create(mock_github_api, context, inputs)

        assert outputs.tag == "pkg-v2.0.0-rc1"
        assert outputs.tag_type == "rc"

    def test_commit_push_rc_with_custom_prefix(self, mock_github_api: MagicMock) -> None:
        """Test commit push creates RC tag with custom prefix."""
        mock_github_api.list_tags.return_value = [make_tag("pkg-v1.0.0-rc1")]
        mock_github_api.tag_exists.return_value = False

        context = GitHubContext(
            event_name="push",
            ref_name="pkg-v1.0",
            ref_type="branch",
            sha="commit2",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="pkg-v",
            tag_prefix="pkg-v",
        )

        outputs = handle_commit_push(mock_github_api, context, inputs)

        assert outputs.tag == "pkg-v1.0.0-rc2"
        assert outputs.tag_type == "rc"

    def test_commit_push_patch_with_custom_prefix(self, mock_github_api: MagicMock) -> None:
        """Test commit push creates patch tag with custom prefix after GA."""
        mock_github_api.list_tags.return_value = [
            make_tag("api-1.0.0-rc1"),
            make_tag("api-1.0.0"),
        ]
        mock_github_api.tag_exists.return_value = True  # GA exists

        context = GitHubContext(
            event_name="push",
            ref_name="api/1.0",
            ref_type="branch",
            sha="patch_commit",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="api/",
            tag_prefix="api-",
        )

        outputs = handle_commit_push(mock_github_api, context, inputs)

        assert outputs.tag == "api-1.0.1"
        assert outputs.tag_type == "patch"

    def test_wrong_prefix_skips_processing(self, mock_github_api: MagicMock) -> None:
        """Test that branch with wrong prefix skips processing."""
        context = GitHubContext(
            event_name="create",
            ref_name="release/v1.0",  # Default prefix
            ref_type="branch",
            sha="abc123",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="v",  # Short prefix configured
            tag_prefix="v",
        )

        outputs = handle_branch_create(mock_github_api, context, inputs)

        assert outputs.tag == ""
        assert outputs.tag_type == "skipped"
        mock_github_api.create_tag.assert_not_called()


class TestAliasSkipLogic:
    """Tests for alias skip logic when prefixes match.

    Validates: Requirements 2.5, 5.5
    """

    def test_alias_skip_when_prefixes_match(self, mock_github_api: MagicMock) -> None:
        """Test that minor alias is skipped when release_prefix == tag_prefix."""
        mock_github_api.list_tags.return_value = [make_tag("v1.0.0")]
        mock_github_api.tag_exists.return_value = True  # GA exists
        mock_github_api.get_branch_commits.return_value = [make_commit("ga_sha")]

        context = GitHubContext(
            event_name="push",
            ref_name="v1.0.0",
            ref_type="tag",
            sha="ga_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            aliases=True,
            release_prefix="v",
            tag_prefix="v",
        )

        handle_tag_push(mock_github_api, context, inputs)

        # Should only update major alias (v1), not minor alias (v1.0)
        update_calls = mock_github_api.update_tag.call_args_list
        updated_tags = [call[0][0] for call in update_calls]
        assert "v1" in updated_tags
        assert "v1.0" not in updated_tags

    def test_alias_created_when_prefixes_differ(self, mock_github_api: MagicMock) -> None:
        """Test that both aliases are created when prefixes differ."""
        mock_github_api.list_tags.return_value = [make_tag("v1.0.0")]
        mock_github_api.tag_exists.return_value = False  # Aliases don't exist
        mock_github_api.get_branch_commits.return_value = [make_commit("ga_sha")]

        context = GitHubContext(
            event_name="push",
            ref_name="v1.0.0",
            ref_type="tag",
            sha="ga_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            aliases=True,
            release_prefix="release/v",  # Different from tag_prefix
            tag_prefix="v",
        )

        handle_tag_push(mock_github_api, context, inputs)

        # Should create both aliases
        create_calls = mock_github_api.create_tag.call_args_list
        created_tags = [call[0][0] for call in create_calls]
        assert "v1" in created_tags
        assert "v1.0" in created_tags

    def test_patch_release_skips_minor_alias_when_prefixes_match(self, mock_github_api: MagicMock) -> None:
        """Test patch release skips minor alias when prefixes match."""
        mock_github_api.list_tags.return_value = [
            make_tag("pkg-1.0.0"),
            make_tag("pkg-1.0.1"),
        ]
        mock_github_api.tag_exists.return_value = True

        context = GitHubContext(
            event_name="push",
            ref_name="pkg-1.0",
            ref_type="branch",
            sha="patch_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            aliases=True,
            release_prefix="pkg-",
            tag_prefix="pkg-",
        )

        handle_commit_push(mock_github_api, context, inputs)

        # Check that minor alias (pkg-1.0) was NOT updated
        update_calls = mock_github_api.update_tag.call_args_list
        updated_tags = [call[0][0] for call in update_calls]
        assert "pkg-1.0" not in updated_tags

    def test_major_alias_always_created(self, mock_github_api: MagicMock) -> None:
        """Test that major alias is always created regardless of prefix match."""
        mock_github_api.list_tags.return_value = [make_tag("v2.0.0")]
        mock_github_api.tag_exists.return_value = False
        mock_github_api.get_branch_commits.return_value = [make_commit("ga_sha")]

        context = GitHubContext(
            event_name="push",
            ref_name="v2.0.0",
            ref_type="tag",
            sha="ga_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            aliases=True,
            release_prefix="v",
            tag_prefix="v",
        )

        handle_tag_push(mock_github_api, context, inputs)

        # Major alias (v2) should be created
        create_calls = mock_github_api.create_tag.call_args_list
        created_tags = [call[0][0] for call in create_calls]
        assert "v2" in created_tags


class TestTagPushWithCustomPrefixes:
    """Tests for tag push handling with custom prefixes.

    Validates: Requirements 5.5
    """

    def test_tag_push_validates_with_custom_prefix(self, mock_github_api: MagicMock) -> None:
        """Test tag push validates tag with custom prefix."""
        mock_github_api.list_tags.return_value = [make_tag("pkg-v1.0.0")]
        mock_github_api.get_branch_commits.return_value = [make_commit("tag_sha")]

        context = GitHubContext(
            event_name="push",
            ref_name="pkg-v1.0.0",
            ref_type="tag",
            sha="tag_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="pkg-v",
            tag_prefix="pkg-v",
        )

        outputs = handle_tag_push(mock_github_api, context, inputs)

        assert outputs.tag == "pkg-v1.0.0"
        assert outputs.tag_type == "ga"
        assert outputs.major == "1"
        assert outputs.minor == "0"

    def test_tag_push_rc_with_custom_prefix(self, mock_github_api: MagicMock) -> None:
        """Test RC tag push with custom prefix."""
        mock_github_api.get_branch_commits.return_value = [make_commit("rc_sha")]

        context = GitHubContext(
            event_name="push",
            ref_name="api-1.0.0-rc1",
            ref_type="tag",
            sha="rc_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="api/",
            tag_prefix="api-",
        )

        outputs = handle_tag_push(mock_github_api, context, inputs)

        assert outputs.tag == "api-1.0.0-rc1"
        assert outputs.tag_type == "rc"

    def test_tag_push_patch_with_custom_prefix(self, mock_github_api: MagicMock) -> None:
        """Test patch tag push with custom prefix."""
        mock_github_api.list_tags.return_value = [
            make_tag("pkg-1.0.0"),
            make_tag("pkg-1.0.1"),
        ]
        mock_github_api.get_branch_commits.return_value = [make_commit("patch_sha")]

        context = GitHubContext(
            event_name="push",
            ref_name="pkg-1.0.1",
            ref_type="tag",
            sha="patch_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="pkg-",
            tag_prefix="pkg-",
        )

        outputs = handle_tag_push(mock_github_api, context, inputs)

        assert outputs.tag == "pkg-1.0.1"
        assert outputs.tag_type == "patch"

    def test_invalid_tag_prefix_skips(self, mock_github_api: MagicMock) -> None:
        """Test that tag with wrong prefix is skipped."""
        context = GitHubContext(
            event_name="push",
            ref_name="v1.0.0",  # Default prefix
            ref_type="tag",
            sha="tag_sha",
            repository="owner/repo",
        )
        inputs = ActionInputs(
            token="test-token",
            debug=False,
            dry_run=False,
            target_branch="",
            release_prefix="pkg-",
            tag_prefix="pkg-",  # Custom prefix configured
        )

        outputs = handle_tag_push(mock_github_api, context, inputs)

        assert outputs.tag == ""
        assert outputs.tag_type == "skipped"
