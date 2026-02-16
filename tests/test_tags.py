# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Unit tests for tag management functions.

Tests find_latest_rc(), find_latest_patch(), ga_exists(), create_tag(),
increment_rc(), increment_patch(), and helper functions from src/tags.py.

Validates: Requirements 11.1
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.tags import (
    create_tag,
    find_latest_patch,
    find_latest_rc,
    ga_exists,
    get_next_patch_tag,
    get_next_rc_tag,
    increment_patch,
    increment_rc,
    is_ga_tag,
    is_patch_tag,
    is_rc_tag,
)
from tests.conftest import make_tag


class TestFindLatestRc:
    """Tests for find_latest_rc() function."""

    def test_no_tags_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that empty tag list returns None."""
        mock_github_api.list_tags.return_value = []
        result = find_latest_rc(mock_github_api, 1, 2)
        assert result is None

    def test_no_matching_rc_tags_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that no matching RC tags returns None."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.0.0-rc1"),
            make_tag("v2.0.0-rc1"),
        ]
        result = find_latest_rc(mock_github_api, 1, 2)
        assert result is None

    def test_single_rc_tag(self, mock_github_api: MagicMock) -> None:
        """Test finding single RC tag."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0-rc1")]
        result = find_latest_rc(mock_github_api, 1, 2)
        assert result == 1

    def test_multiple_rc_tags_returns_highest(self, mock_github_api: MagicMock) -> None:
        """Test that highest RC number is returned."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0-rc1"),
            make_tag("v1.2.0-rc3"),
            make_tag("v1.2.0-rc2"),
        ]
        result = find_latest_rc(mock_github_api, 1, 2)
        assert result == 3

    def test_filters_by_major_minor(self, mock_github_api: MagicMock) -> None:
        """Test that only matching major.minor versions are considered."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0-rc5"),
            make_tag("v1.3.0-rc10"),
            make_tag("v2.2.0-rc20"),
        ]
        result = find_latest_rc(mock_github_api, 1, 2)
        assert result == 5

    def test_ignores_non_rc_tags(self, mock_github_api: MagicMock) -> None:
        """Test that GA and patch tags are ignored."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0"),
            make_tag("v1.2.1"),
            make_tag("v1.2.0-rc2"),
        ]
        result = find_latest_rc(mock_github_api, 1, 2)
        assert result == 2


class TestFindLatestPatch:
    """Tests for find_latest_patch() function."""

    def test_no_tags_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that empty tag list returns None."""
        mock_github_api.list_tags.return_value = []
        result = find_latest_patch(mock_github_api, 1, 2)
        assert result is None

    def test_no_matching_patch_tags_returns_none(self, mock_github_api: MagicMock) -> None:
        """Test that no matching patch tags returns None."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.0.0"),
            make_tag("v2.0.0"),
        ]
        result = find_latest_patch(mock_github_api, 1, 2)
        assert result is None

    def test_ga_tag_returns_zero(self, mock_github_api: MagicMock) -> None:
        """Test that GA tag (vX.Y.0) returns 0."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        result = find_latest_patch(mock_github_api, 1, 2)
        assert result == 0

    def test_single_patch_tag(self, mock_github_api: MagicMock) -> None:
        """Test finding single patch tag."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.3")]
        result = find_latest_patch(mock_github_api, 1, 2)
        assert result == 3

    def test_multiple_patch_tags_returns_highest(self, mock_github_api: MagicMock) -> None:
        """Test that highest patch number is returned."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0"),
            make_tag("v1.2.1"),
            make_tag("v1.2.5"),
            make_tag("v1.2.3"),
        ]
        result = find_latest_patch(mock_github_api, 1, 2)
        assert result == 5

    def test_filters_by_major_minor(self, mock_github_api: MagicMock) -> None:
        """Test that only matching major.minor versions are considered."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.2"),
            make_tag("v1.3.10"),
            make_tag("v2.2.20"),
        ]
        result = find_latest_patch(mock_github_api, 1, 2)
        assert result == 2

    def test_ignores_rc_tags(self, mock_github_api: MagicMock) -> None:
        """Test that RC tags are ignored."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0-rc1"),
            make_tag("v1.2.0-rc5"),
            make_tag("v1.2.1"),
        ]
        result = find_latest_patch(mock_github_api, 1, 2)
        assert result == 1


class TestGaExists:
    """Tests for ga_exists() function."""

    def test_ga_exists_true(self, mock_github_api: MagicMock) -> None:
        """Test that ga_exists returns True when GA tag exists."""
        mock_github_api.tag_exists.return_value = True
        result = ga_exists(mock_github_api, 1, 2)
        assert result is True
        mock_github_api.tag_exists.assert_called_once_with("v1.2.0")

    def test_ga_exists_false(self, mock_github_api: MagicMock) -> None:
        """Test that ga_exists returns False when GA tag doesn't exist."""
        mock_github_api.tag_exists.return_value = False
        result = ga_exists(mock_github_api, 1, 2)
        assert result is False
        mock_github_api.tag_exists.assert_called_once_with("v1.2.0")

    def test_ga_exists_zero_versions(self, mock_github_api: MagicMock) -> None:
        """Test ga_exists with zero major/minor versions."""
        mock_github_api.tag_exists.return_value = True
        result = ga_exists(mock_github_api, 0, 1)
        assert result is True
        mock_github_api.tag_exists.assert_called_once_with("v0.1.0")


class TestCreateTag:
    """Tests for create_tag() function."""

    def test_create_tag_with_default_message(self, mock_github_api: MagicMock) -> None:
        """Test creating tag with default message."""
        create_tag(mock_github_api, "v1.2.0-rc1", "abc123")
        mock_github_api.create_tag.assert_called_once_with("v1.2.0-rc1", "abc123", "Release v1.2.0-rc1")

    def test_create_tag_with_custom_message(self, mock_github_api: MagicMock) -> None:
        """Test creating tag with custom message."""
        create_tag(mock_github_api, "v1.2.0", "def456", "GA Release v1.2.0")
        mock_github_api.create_tag.assert_called_once_with("v1.2.0", "def456", "GA Release v1.2.0")

    def test_create_tag_calls_api(self, mock_github_api: MagicMock) -> None:
        """Test that create_tag calls the API correctly."""
        create_tag(mock_github_api, "v2.0.0-rc5", "sha123456")
        assert mock_github_api.create_tag.called


class TestIncrementRc:
    """Tests for increment_rc() function."""

    def test_increment_rc_from_none(self) -> None:
        """Test that None returns 1 (first RC)."""
        assert increment_rc(None) == 1

    def test_increment_rc_from_one(self) -> None:
        """Test incrementing from rc1."""
        assert increment_rc(1) == 2

    def test_increment_rc_from_arbitrary(self) -> None:
        """Test incrementing from arbitrary RC number."""
        assert increment_rc(5) == 6
        assert increment_rc(99) == 100


class TestIncrementPatch:
    """Tests for increment_patch() function."""

    def test_increment_patch_from_none(self) -> None:
        """Test that None returns 1."""
        assert increment_patch(None) == 1

    def test_increment_patch_from_zero(self) -> None:
        """Test incrementing from 0 (after GA)."""
        assert increment_patch(0) == 1

    def test_increment_patch_from_arbitrary(self) -> None:
        """Test incrementing from arbitrary patch number."""
        assert increment_patch(2) == 3
        assert increment_patch(99) == 100


class TestGetNextRcTag:
    """Tests for get_next_rc_tag() function."""

    def test_first_rc_tag(self, mock_github_api: MagicMock) -> None:
        """Test getting first RC tag when none exist."""
        mock_github_api.list_tags.return_value = []
        result = get_next_rc_tag(mock_github_api, 1, 2)
        assert result == "v1.2.0-rc1"

    def test_next_rc_tag(self, mock_github_api: MagicMock) -> None:
        """Test getting next RC tag after existing ones."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0-rc1"),
            make_tag("v1.2.0-rc2"),
        ]
        result = get_next_rc_tag(mock_github_api, 1, 2)
        assert result == "v1.2.0-rc3"


class TestGetNextPatchTag:
    """Tests for get_next_patch_tag() function."""

    def test_first_patch_after_ga(self, mock_github_api: MagicMock) -> None:
        """Test getting first patch tag after GA."""
        mock_github_api.list_tags.return_value = [make_tag("v1.2.0")]
        result = get_next_patch_tag(mock_github_api, 1, 2)
        assert result == "v1.2.1"

    def test_next_patch_tag(self, mock_github_api: MagicMock) -> None:
        """Test getting next patch tag after existing ones."""
        mock_github_api.list_tags.return_value = [
            make_tag("v1.2.0"),
            make_tag("v1.2.1"),
            make_tag("v1.2.2"),
        ]
        result = get_next_patch_tag(mock_github_api, 1, 2)
        assert result == "v1.2.3"


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

    def test_invalid_tag_returns_false(self) -> None:
        """Test that invalid tags return False."""
        assert is_rc_tag("invalid") is False
        assert is_rc_tag("") is False


class TestIsGaTag:
    """Tests for is_ga_tag() function."""

    def test_ga_tag_returns_true(self) -> None:
        """Test that GA tags (vX.Y.0) return True."""
        assert is_ga_tag("v1.2.0") is True
        assert is_ga_tag("v0.1.0") is True

    def test_patch_tag_returns_false(self) -> None:
        """Test that patch tags return False."""
        assert is_ga_tag("v1.2.1") is False
        assert is_ga_tag("v1.2.99") is False

    def test_rc_tag_returns_false(self) -> None:
        """Test that RC tags return False."""
        assert is_ga_tag("v1.2.0-rc1") is False

    def test_invalid_tag_returns_false(self) -> None:
        """Test that invalid tags return False."""
        assert is_ga_tag("invalid") is False
        assert is_ga_tag("") is False


class TestIsPatchTag:
    """Tests for is_patch_tag() function."""

    def test_patch_tag_returns_true(self) -> None:
        """Test that patch tags (vX.Y.Z where Z > 0) return True."""
        assert is_patch_tag("v1.2.1") is True
        assert is_patch_tag("v1.2.99") is True

    def test_ga_tag_returns_false(self) -> None:
        """Test that GA tags return False."""
        assert is_patch_tag("v1.2.0") is False

    def test_rc_tag_returns_false(self) -> None:
        """Test that RC tags return False."""
        assert is_patch_tag("v1.2.0-rc1") is False

    def test_invalid_tag_returns_false(self) -> None:
        """Test that invalid tags return False."""
        assert is_patch_tag("invalid") is False
        assert is_patch_tag("") is False
