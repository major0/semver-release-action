# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Unit tests for branch validation and version extraction.

Tests validate_branch() and extract_version() functions from src/branch.py.

Validates: Requirements 1.1, 1.2, 1.3, 11.1
"""

from __future__ import annotations

from src.branch import BranchVersion, extract_version, validate_branch


class TestValidateBranch:
    """Tests for validate_branch() function."""

    def test_valid_release_branch(self) -> None:
        """Test that release/v1.2 is accepted."""
        assert validate_branch("release/v1.2") is True

    def test_valid_release_branch_zero_minor(self) -> None:
        """Test that release/v0.1 is accepted (zero major is valid)."""
        assert validate_branch("release/v0.1") is True

    def test_valid_release_branch_zero_major(self) -> None:
        """Test that release/v1.0 is accepted (zero minor is valid)."""
        assert validate_branch("release/v1.0") is True

    def test_valid_release_branch_large_numbers(self) -> None:
        """Test that large version numbers are accepted."""
        assert validate_branch("release/v10.20") is True
        assert validate_branch("release/v100.200") is True

    def test_invalid_leading_zero_major(self) -> None:
        """Test that leading zeros in major version are rejected (SemVer 2.0.0)."""
        assert validate_branch("release/v01.2") is False

    def test_invalid_leading_zero_minor(self) -> None:
        """Test that leading zeros in minor version are rejected (SemVer 2.0.0)."""
        assert validate_branch("release/v1.02") is False

    def test_invalid_missing_v_prefix(self) -> None:
        """Test that missing 'v' prefix is rejected."""
        assert validate_branch("release/1.2") is False

    def test_invalid_wrong_branch_prefix(self) -> None:
        """Test that non-release branches are rejected."""
        assert validate_branch("feature/v1.2") is False
        assert validate_branch("main") is False
        assert validate_branch("develop") is False

    def test_invalid_missing_minor(self) -> None:
        """Test that missing minor version is rejected."""
        assert validate_branch("release/v1") is False

    def test_invalid_has_patch(self) -> None:
        """Test that patch version in branch name is rejected."""
        assert validate_branch("release/v1.2.3") is False

    def test_invalid_empty_string(self) -> None:
        """Test that empty string is rejected."""
        assert validate_branch("") is False

    def test_invalid_none_like_empty(self) -> None:
        """Test that whitespace-only strings are rejected."""
        assert validate_branch("   ") is False

    def test_valid_branches_from_fixture(self, sample_branches: dict[str, list[str]]) -> None:
        """Test all valid branches from fixture are accepted."""
        for branch in sample_branches["valid"]:
            assert validate_branch(branch) is True, f"Expected {branch} to be valid"

    def test_invalid_branches_from_fixture(self, sample_branches: dict[str, list[str]]) -> None:
        """Test all invalid branches from fixture are rejected."""
        for branch in sample_branches["invalid"]:
            assert validate_branch(branch) is False, f"Expected {branch} to be invalid"


class TestExtractVersion:
    """Tests for extract_version() function."""

    def test_extract_version_basic(self) -> None:
        """Test extracting version from release/v1.2."""
        version = extract_version("release/v1.2")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2

    def test_extract_version_zero_major(self) -> None:
        """Test extracting version with zero major."""
        version = extract_version("release/v0.1")
        assert version is not None
        assert version.major == 0
        assert version.minor == 1

    def test_extract_version_zero_minor(self) -> None:
        """Test extracting version with zero minor."""
        version = extract_version("release/v1.0")
        assert version is not None
        assert version.major == 1
        assert version.minor == 0

    def test_extract_version_large_numbers(self) -> None:
        """Test extracting large version numbers."""
        version = extract_version("release/v10.20")
        assert version is not None
        assert version.major == 10
        assert version.minor == 20

    def test_extract_version_invalid_branch_returns_none(self) -> None:
        """Test that invalid branches return None."""
        assert extract_version("feature/v1.2") is None
        assert extract_version("release/v01.2") is None
        assert extract_version("main") is None

    def test_extract_version_empty_string_returns_none(self) -> None:
        """Test that empty string returns None."""
        assert extract_version("") is None


class TestBranchVersion:
    """Tests for BranchVersion dataclass."""

    def test_str_representation(self) -> None:
        """Test string representation of BranchVersion."""
        version = BranchVersion(major=1, minor=2)
        assert str(version) == "1.2"

    def test_str_representation_zeros(self) -> None:
        """Test string representation with zeros."""
        version = BranchVersion(major=0, minor=0)
        assert str(version) == "0.0"
