# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Unit tests for branch validation and version extraction.

Tests validate_branch(), extract_version(), validate_prefix(), create_branch_pattern(),
parse_branch(), and should_skip_minor_alias() functions from src/branch.py.

Validates: Requirements 1.1, 1.2, 1.3, 5.1, 5.2, 5.3, 5.4, 10.2, 11.1
"""

from __future__ import annotations

from src.branch import (
    BranchVersion,
    create_branch_pattern,
    extract_version,
    parse_branch,
    should_skip_minor_alias,
    validate_branch,
    validate_prefix,
)


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


class TestValidatePrefix:
    """Tests for validate_prefix() function.

    Validates: Requirements 1.5, 2.6, 4.1
    """

    def test_valid_default_prefix(self) -> None:
        """Test that default 'release/v' prefix is valid."""
        assert validate_prefix("release/v") is True

    def test_valid_short_prefix(self) -> None:
        """Test that short 'v' prefix is valid."""
        assert validate_prefix("v") is True

    def test_valid_custom_prefix_with_dash(self) -> None:
        """Test that custom prefix with dash is valid."""
        assert validate_prefix("pkg-") is True
        assert validate_prefix("pkg-v") is True

    def test_valid_custom_prefix_with_slash(self) -> None:
        """Test that custom prefix with slash is valid."""
        assert validate_prefix("api/") is True
        assert validate_prefix("main/v") is True

    def test_invalid_empty_prefix(self) -> None:
        """Test that empty prefix is rejected."""
        assert validate_prefix("") is False

    def test_invalid_double_dot(self) -> None:
        """Test that prefix with '..' is rejected."""
        assert validate_prefix("bad..prefix") is False
        assert validate_prefix("..start") is False
        assert validate_prefix("end..") is False

    def test_invalid_tilde(self) -> None:
        """Test that prefix with '~' is rejected."""
        assert validate_prefix("bad~prefix") is False

    def test_invalid_caret(self) -> None:
        """Test that prefix with '^' is rejected."""
        assert validate_prefix("bad^prefix") is False

    def test_invalid_colon(self) -> None:
        """Test that prefix with ':' is rejected."""
        assert validate_prefix("bad:prefix") is False

    def test_invalid_backslash(self) -> None:
        """Test that prefix with backslash is rejected."""
        assert validate_prefix("bad\\prefix") is False

    def test_invalid_space(self) -> None:
        """Test that prefix with space is rejected."""
        assert validate_prefix("bad prefix") is False

    def test_invalid_tab(self) -> None:
        """Test that prefix with tab is rejected."""
        assert validate_prefix("bad\tprefix") is False

    def test_invalid_newline(self) -> None:
        """Test that prefix with newline is rejected."""
        assert validate_prefix("bad\nprefix") is False

    def test_invalid_asterisk(self) -> None:
        """Test that prefix with '*' is rejected."""
        assert validate_prefix("bad*prefix") is False

    def test_invalid_question_mark(self) -> None:
        """Test that prefix with '?' is rejected."""
        assert validate_prefix("bad?prefix") is False

    def test_invalid_bracket(self) -> None:
        """Test that prefix with '[' is rejected."""
        assert validate_prefix("bad[prefix") is False


class TestCreateBranchPattern:
    """Tests for create_branch_pattern() function.

    Validates: Requirements 1.4, 4.2
    """

    def test_default_prefix_pattern(self) -> None:
        """Test pattern with default 'release/v' prefix."""
        pattern = create_branch_pattern("release/v")
        assert pattern.match("release/v1.2") is not None
        assert pattern.match("release/v0.0") is not None
        assert pattern.match("release/v10.20") is not None

    def test_short_prefix_pattern(self) -> None:
        """Test pattern with short 'v' prefix."""
        pattern = create_branch_pattern("v")
        assert pattern.match("v1.2") is not None
        assert pattern.match("v0.1") is not None
        assert pattern.match("v10.20") is not None

    def test_custom_prefix_with_dash(self) -> None:
        """Test pattern with custom 'pkg-' prefix."""
        pattern = create_branch_pattern("pkg-")
        assert pattern.match("pkg-1.2") is not None
        assert pattern.match("pkg-0.1") is not None

    def test_custom_prefix_with_v(self) -> None:
        """Test pattern with custom 'pkg-v' prefix."""
        pattern = create_branch_pattern("pkg-v")
        assert pattern.match("pkg-v1.2") is not None
        assert pattern.match("pkg-v0.1") is not None

    def test_path_style_prefix(self) -> None:
        """Test pattern with path-style 'api/' prefix."""
        pattern = create_branch_pattern("api/")
        assert pattern.match("api/1.2") is not None
        assert pattern.match("api/0.1") is not None

    def test_pattern_rejects_wrong_prefix(self) -> None:
        """Test that pattern rejects branches with wrong prefix."""
        pattern = create_branch_pattern("release/v")
        assert pattern.match("v1.2") is None
        assert pattern.match("pkg-1.2") is None

    def test_pattern_rejects_leading_zeros(self) -> None:
        """Test that pattern rejects leading zeros in version numbers."""
        pattern = create_branch_pattern("release/v")
        assert pattern.match("release/v01.2") is None
        assert pattern.match("release/v1.02") is None
        assert pattern.match("release/v00.0") is None

    def test_pattern_rejects_missing_minor(self) -> None:
        """Test that pattern rejects branches without minor version."""
        pattern = create_branch_pattern("release/v")
        assert pattern.match("release/v1") is None

    def test_pattern_rejects_patch_version(self) -> None:
        """Test that pattern rejects branches with patch version."""
        pattern = create_branch_pattern("release/v")
        assert pattern.match("release/v1.2.3") is None

    def test_pattern_escapes_special_regex_chars(self) -> None:
        """Test that special regex characters in prefix are escaped."""
        # Prefix with dot should be escaped
        pattern = create_branch_pattern("v1.x-")
        assert pattern.match("v1.x-1.2") is not None
        # Should not match if dot is treated as regex wildcard
        assert pattern.match("v1ax-1.2") is None


class TestParseBranch:
    """Tests for parse_branch() function with configurable prefixes.

    Validates: Requirements 3.1, 3.5, 4.1, 5.1, 5.2, 5.3
    """

    def test_default_prefix(self) -> None:
        """Test parsing with default 'release/v' prefix."""
        version = parse_branch("release/v1.2")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2

    def test_default_prefix_explicit(self) -> None:
        """Test parsing with explicit default prefix."""
        version = parse_branch("release/v1.2", release_prefix="release/v")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2

    def test_short_prefix(self) -> None:
        """Test parsing with short 'v' prefix."""
        version = parse_branch("v1.2", release_prefix="v")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2

    def test_custom_prefix_pkg_dash(self) -> None:
        """Test parsing with custom 'pkg-' prefix."""
        version = parse_branch("pkg-1.2", release_prefix="pkg-")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2

    def test_custom_prefix_pkg_v(self) -> None:
        """Test parsing with custom 'pkg-v' prefix."""
        version = parse_branch("pkg-v1.2", release_prefix="pkg-v")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2

    def test_path_style_prefix_api(self) -> None:
        """Test parsing with path-style 'api/' prefix."""
        version = parse_branch("api/1.2", release_prefix="api/")
        assert version is not None
        assert version.major == 1
        assert version.minor == 2

    def test_zero_versions(self) -> None:
        """Test parsing with zero major and minor versions."""
        version = parse_branch("v0.0", release_prefix="v")
        assert version is not None
        assert version.major == 0
        assert version.minor == 0

    def test_large_version_numbers(self) -> None:
        """Test parsing with large version numbers."""
        version = parse_branch("v100.200", release_prefix="v")
        assert version is not None
        assert version.major == 100
        assert version.minor == 200

    def test_wrong_prefix_returns_none(self) -> None:
        """Test that wrong prefix returns None."""
        # Using default prefix but branch has short prefix
        assert parse_branch("v1.2") is None
        # Using short prefix but branch has default prefix
        assert parse_branch("release/v1.2", release_prefix="v") is None

    def test_leading_zero_major_rejected(self) -> None:
        """Test that leading zeros in major version are rejected."""
        assert parse_branch("release/v01.2") is None
        assert parse_branch("v01.2", release_prefix="v") is None
        assert parse_branch("pkg-01.2", release_prefix="pkg-") is None

    def test_leading_zero_minor_rejected(self) -> None:
        """Test that leading zeros in minor version are rejected."""
        assert parse_branch("release/v1.02") is None
        assert parse_branch("v1.02", release_prefix="v") is None
        assert parse_branch("pkg-1.02", release_prefix="pkg-") is None

    def test_empty_branch_returns_none(self) -> None:
        """Test that empty branch name returns None."""
        assert parse_branch("") is None
        assert parse_branch("", release_prefix="v") is None


class TestShouldSkipMinorAlias:
    """Tests for should_skip_minor_alias() function.

    Validates: Requirements 2.5
    """

    def test_different_prefixes_no_skip(self) -> None:
        """Test that different prefixes do not skip minor alias."""
        # Default case: release/v branch with v tag
        assert should_skip_minor_alias("release/v", "v") is False

    def test_same_prefixes_skip(self) -> None:
        """Test that same prefixes skip minor alias."""
        # Short prefix case: v branch with v tag
        assert should_skip_minor_alias("v", "v") is True

    def test_same_custom_prefixes_skip(self) -> None:
        """Test that same custom prefixes skip minor alias."""
        assert should_skip_minor_alias("pkg-v", "pkg-v") is True
        assert should_skip_minor_alias("pkg-", "pkg-") is True
        assert should_skip_minor_alias("api/", "api/") is True

    def test_different_custom_prefixes_no_skip(self) -> None:
        """Test that different custom prefixes do not skip minor alias."""
        assert should_skip_minor_alias("pkg-release/v", "pkg-v") is False
        assert should_skip_minor_alias("api/", "api-") is False
