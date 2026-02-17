# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Unit tests for alias tag management functions.

Tests find_highest_major_version(), find_highest_minor_version(),
update_alias_tags(), and helper functions from src/aliases.py.

Validates: Requirements 11.1
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.aliases import (
    find_highest_major_version,
    find_highest_minor_version,
    is_rc_tag,
    parse_release_tag,
    should_update_major_alias,
    should_update_minor_alias,
    update_alias_tags,
)
from tests.conftest import make_tag


class TestParseReleaseTag:
    """Tests for parse_release_tag() function."""

    def test_valid_ga_tag(self) -> None:
        """Test parsing GA tag."""
        assert parse_release_tag("v1.2.0") == (1, 2, 0)

    def test_valid_patch_tag(self) -> None:
        """Test parsing patch tag."""
        assert parse_release_tag("v1.2.3") == (1, 2, 3)

    def test_zero_versions(self) -> None:
        """Test parsing tags with zero versions."""
        assert parse_release_tag("v0.0.0") == (0, 0, 0)
        assert parse_release_tag("v0.1.0") == (0, 1, 0)

    def test_rc_tag_returns_none(self) -> None:
        """Test that RC tags return None."""
        assert parse_release_tag("v1.2.0-rc1") is None

    def test_invalid_tag_returns_none(self) -> None:
        """Test that invalid tags return None."""
        assert parse_release_tag("invalid") is None
        assert parse_release_tag("") is None
        assert parse_release_tag("v1.2") is None
        assert parse_release_tag("1.2.3") is None


class TestIsRcTag:
    """Tests for is_rc_tag() function."""

    def test_rc_tag_returns_true(self) -> None:
        """Test that RC tags return True."""
        assert is_rc_tag("v1.2.0-rc1") is True
        assert is_rc_tag("v0.1.0-rc99") is True

    def test_ga_tag_returns_false(self) -> None:
        """Test that GA tags return False."""
        assert is_rc_tag("v1.2.0") is False

    def test_patch_tag_returns_false(self) -> None:
        """Test that patch tags return False."""
        assert is_rc_tag("v1.2.1") is False


class TestFindHighestMajorVersion:
    """Tests for find_highest_major_version() function."""

    def test_no_tags_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that empty tag list returns None."""
        mock_github_api.list_tags.return_value = []
        result = find_highest_major_version(mock_github_api, 1)
        assert result is None

    def test_no_matching_major_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that no matching major version returns None."""
        mock_github_api.list_tags.return_value = [
            make_tag("v2.0.0"),
            make_tag("v3.0.0"),
        ]
        result = find_highest_major_version(mock_github_api, 1)
        assert result is None

    def test_single_release(self, mock_github_api: MagicMock) -> None:
        """Test finding single release."""
        mock_github_api.list_tags.return_value = [make_tag("v1.0.0")]
        result = find_highest_major_version(mock_github_api, 1)
        assert result == (1, 0, 0)

    def test_multiple_releases_same_minor(self, mock_github_api: MagicMock) -> None:
        """Test finding highest patch in same minor."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.0.0"),
            make_tag("v1.0.1"),
            make_tag("v1.0.5"),
        ]
        result = find_highest_major_version(mock_github_api, 1)
        assert result == (1, 0, 5)

    def test_multiple_releases_different_minors(self, mock_github_api: MagicMock) -> None:
        """Test finding highest across different minors."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.0.5"),
            make_tag("v1.1.0"),
            make_tag("v1.2.3"),
        ]
        result = find_highest_major_version(mock_github_api, 1)
        assert result == (1, 2, 3)

    def test_filters_by_major(self, mock_github_api: MagicMock) -> None:
        """Test that only matching major versions are considered."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.5.0"),
            make_tag("v2.0.0"),
            make_tag("v2.1.0"),
        ]
        result = find_highest_major_version(mock_github_api, 2)
        assert result == (2, 1, 0)

    def test_ignores_rc_tags(self, mock_github_api: MagicMock) -> None:
        """Test that RC tags are ignored."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.0.0"),
            make_tag("v1.1.0-rc1"),
            make_tag("v1.1.0-rc5"),
        ]
        result = find_highest_major_version(mock_github_api, 1)
        assert result == (1, 0, 0)

    def test_multiple_branches(self, mock_github_api: MagicMock) -> None:
        """Test finding highest across multiple release branches."""
        mock_github_api.list_tags.return_value = [
            make_tag("v2.0.0"),
            make_tag("v2.0.3"),
            make_tag("v2.1.0"),
            make_tag("v2.1.2"),
            make_tag("v2.2.0"),
        ]
        result = find_highest_major_version(mock_github_api, 2)
        assert result == (2, 2, 0)


class TestFindHighestMinorVersion:
    """Tests for find_highest_minor_version() function."""

    def test_no_tags_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that empty tag list returns None."""
        mock_github_api.list_tags.return_value = []
        result = find_highest_minor_version(mock_github_api, 1, 2)
        assert result is None

    def test_no_matching_minor_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that no matching minor version returns None."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.0.0"),
            make_tag("v1.1.0"),
        ]
        result = find_highest_minor_version(mock_github_api, 1, 2)
        assert result is None

    def test_single_release(self, mock_github_api: MagicMock) -> None:
        """Test finding single release."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        result = find_highest_minor_version(mock_github_api, 1, 2)
        assert result == (1, 2, 0)

    def test_multiple_patches(self, mock_github_api: MagicMock) -> None:
        """Test finding highest patch."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0"),
            make_tag("v1.2.1"),
            make_tag("v1.2.5"),
            make_tag("v1.2.3"),
        ]
        result = find_highest_minor_version(mock_github_api, 1, 2)
        assert result == (1, 2, 5)

    def test_filters_by_major_minor(self, mock_github_api: MagicMock) -> None:
        """Test that only matching major.minor versions are considered."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.2"),
            make_tag("v1.3.10"),
            make_tag("v2.2.20"),
        ]
        result = find_highest_minor_version(mock_github_api, 1, 2)
        assert result == (1, 2, 2)

    def test_ignores_rc_tags(self, mock_github_api: MagicMock) -> None:
        """Test that RC tags are ignored."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0"),
            make_tag("v1.2.0-rc1"),
            make_tag("v1.2.0-rc5"),
        ]
        result = find_highest_minor_version(mock_github_api, 1, 2)
        assert result == (1, 2, 0)


class TestUpdateAliasTags:
    """Tests for update_alias_tags() function."""

    def test_skips_rc_releases(self, mock_github_api: MagicMock) -> None:
        """Test that RC releases don't update aliases."""
        result = update_alias_tags(mock_github_api, "v1.2.0-rc1", "abc123")
        assert result == {"major": False, "minor": False}
        mock_github_api.update_tag.assert_not_called()
        mock_github_api.create_tag.assert_not_called()

    def test_updates_both_aliases_for_highest(self, mock_github_api: MagicMock) -> None:
        """Test that both aliases are updated for highest release."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        mock_github_api.tag_exists.return_value = False

        result = update_alias_tags(mock_github_api, "v1.2.0", "abc123")

        assert result == {"major": True, "minor": True}

    def test_force_updates_existing_aliases(self, mock_github_api: MagicMock) -> None:
        """Test that existing aliases are force-updated."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        mock_github_api.tag_exists.return_value = True

        update_alias_tags(mock_github_api, "v1.2.0", "abc123")

        # Should call update_tag for both aliases
        assert mock_github_api.update_tag.call_count == 2

    def test_creates_new_aliases(self, mock_github_api: MagicMock) -> None:
        """Test that new aliases are created when they don't exist."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        mock_github_api.tag_exists.return_value = False

        update_alias_tags(mock_github_api, "v1.2.0", "abc123")

        # Should call create_tag for both aliases
        assert mock_github_api.create_tag.call_count == 2

    def test_updates_minor_only_for_patch(self, mock_github_api: MagicMock) -> None:
        """Test that patch release updates minor alias but not major if not highest."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0"),
            make_tag("v1.2.1"),
            make_tag("v1.3.0"),  # Higher minor exists
        ]
        mock_github_api.tag_exists.return_value = True

        result = update_alias_tags(mock_github_api, "v1.2.1", "abc123")

        assert result["minor"] is True
        assert result["major"] is False

    def test_lower_patch_skips_minor_alias(self, mock_github_api: MagicMock) -> None:
        """Test that lower patch version skips minor alias update."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0"),
            make_tag("v1.2.5"),  # Higher patch exists
        ]
        mock_github_api.tag_exists.return_value = True

        # v1.2.3 is lower than v1.2.5, so minor alias should NOT be updated
        result = update_alias_tags(mock_github_api, "v1.2.3", "abc123")

        assert result["minor"] is False
        assert result["major"] is False  # Also not highest major

    def test_invalid_tag_returns_no_updates(self, mock_github_api: MagicMock) -> None:
        """Test that invalid tags don't update aliases."""
        result = update_alias_tags(mock_github_api, "invalid", "abc123")
        assert result == {"major": False, "minor": False}

    def test_multi_branch_alias_updates(self, mock_github_api: MagicMock) -> None:
        """Test alias updates with multiple active branches."""
        # Simulate releases from multiple branches: v1.1.x, v1.2.x
        mock_github_api.list_tags.return_value = [
            make_tag("v1.1.0"),
            make_tag("v1.1.1"),
            make_tag("v1.2.0"),
        ]
        mock_github_api.tag_exists.return_value = True

        # v1.2.0 should update both major and minor aliases
        result = update_alias_tags(mock_github_api, "v1.2.0", "abc123")
        assert result == {"major": True, "minor": True}


class TestShouldUpdateMajorAlias:
    """Tests for should_update_major_alias() function."""

    def test_no_existing_tags(self, mock_github_api: MagicMock) -> None:
        """Test that first release should update major alias."""
        mock_github_api.list_tags.return_value = []
        assert should_update_major_alias(mock_github_api, 1, 0, 0) is True

    def test_higher_minor_should_update(self, mock_github_api: MagicMock) -> None:
        """Test that higher minor version should update major alias."""
        mock_github_api.list_tags.return_value = [make_tag("v1.0.0")]
        assert should_update_major_alias(mock_github_api, 1, 1, 0) is True

    def test_lower_minor_should_not_update(self, mock_github_api: MagicMock) -> None:
        """Test that lower minor version should not update major alias."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        assert should_update_major_alias(mock_github_api, 1, 1, 0) is False

    def test_equal_version_should_update(self, mock_github_api: MagicMock) -> None:
        """Test that equal version should update (idempotent)."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.3")]
        assert should_update_major_alias(mock_github_api, 1, 2, 3) is True


class TestShouldUpdateMinorAlias:
    """Tests for should_update_minor_alias() function."""

    def test_no_existing_tags(self, mock_github_api: MagicMock) -> None:
        """Test that first release should update minor alias."""
        mock_github_api.list_tags.return_value = []
        assert should_update_minor_alias(mock_github_api, 1, 2, 0) is True

    def test_higher_patch_should_update(self, mock_github_api: MagicMock) -> None:
        """Test that higher patch version should update minor alias."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        assert should_update_minor_alias(mock_github_api, 1, 2, 1) is True

    def test_lower_patch_should_not_update(self, mock_github_api: MagicMock) -> None:
        """Test that lower patch version should not update minor alias."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.5")]
        assert should_update_minor_alias(mock_github_api, 1, 2, 3) is False

    def test_equal_version_should_update(self, mock_github_api: MagicMock) -> None:
        """Test that equal version should update (idempotent)."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.3")]
        assert should_update_minor_alias(mock_github_api, 1, 2, 3) is True


class TestIndependentTagTrackingPerBranch:
    """Tests for independent tag tracking per release branch."""

    def test_tracks_tags_per_branch_independently(self, mock_github_api: MagicMock) -> None:
        """Test that tags are tracked independently per branch."""
        # Tags from different branches
        mock_github_api.list_tags.return_value = [
            make_tag("v1.1.0"),
            make_tag("v1.1.1"),
            make_tag("v1.2.0"),
            make_tag("v1.2.1"),
        ]

        # v1.1 series highest
        result = find_highest_minor_version(mock_github_api, 1, 1)
        assert result == (1, 1, 1)

        # v1.2 series highest
        result = find_highest_minor_version(mock_github_api, 1, 2)
        assert result == (1, 2, 1)

    def test_alias_updates_with_multiple_active_branches(self, mock_github_api: MagicMock) -> None:
        """Test alias updates with multiple active release branches."""
        mock_github_api.list_tags.return_value = [
            make_tag("v2.0.0"),
            make_tag("v2.0.3"),
            make_tag("v2.1.0"),
            make_tag("v2.1.2"),
        ]
        mock_github_api.tag_exists.return_value = True

        # New release on v2.0 branch - should update v2.0 alias but not v2
        result = update_alias_tags(mock_github_api, "v2.0.4", "abc123")
        assert result["minor"] is True
        assert result["major"] is False  # v2.1.2 is higher

    def test_new_minor_branch_updates_major_alias(self, mock_github_api: MagicMock) -> None:
        """Test that new minor branch updates major alias."""
        # Include the new tag in the list (simulating it was just created)
        mock_github_api.list_tags.return_value = [
            make_tag("v2.0.0"),
            make_tag("v2.0.3"),
            make_tag("v2.1.0"),
            make_tag("v2.2.0"),  # The new tag being released
        ]
        mock_github_api.tag_exists.return_value = True

        # New release on v2.2 branch - should update both aliases
        result = update_alias_tags(mock_github_api, "v2.2.0", "abc123")
        assert result["minor"] is True
        assert result["major"] is True
