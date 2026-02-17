# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Branch validation and version extraction for release branches.

This module validates release branch patterns and extracts version information
according to SemVer 2.0.0 conventions.

References:
    - Semantic Versioning 2.0.0: https://semver.org/
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# SemVer 2.0.0 compliant pattern: no leading zeros allowed
# Pattern: release/vX.Y where X and Y are non-negative integers without leading zeros
RELEASE_BRANCH_PATTERN = re.compile(r"^release/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")

# Characters invalid in git refs (branch names and tags)
# See: https://git-scm.com/docs/git-check-ref-format
INVALID_PREFIX_CHARS = ["..", "~", "^", ":", "\\", " ", "\t", "\n", "*", "?", "["]


def validate_prefix(prefix: str) -> bool:
    """Validate that a prefix is valid for git branch names and tags.

    A valid prefix must be non-empty and must not contain characters that are
    invalid in git refs.

    Args:
        prefix: The prefix string to validate.

    Returns:
        True if the prefix is valid, False otherwise.

    Examples:
        >>> validate_prefix("release/v")
        True
        >>> validate_prefix("v")
        True
        >>> validate_prefix("pkg-")
        True
        >>> validate_prefix("")  # Empty - invalid
        False
        >>> validate_prefix("bad..prefix")  # Contains '..' - invalid
        False

    References:
        - git-check-ref-format: https://git-scm.com/docs/git-check-ref-format
        - Requirements 1.5, 2.6, 4.1
    """
    if not prefix:
        logger.warning("Empty prefix provided")
        return False

    for invalid_char in INVALID_PREFIX_CHARS:
        if invalid_char in prefix:
            logger.warning(
                "Prefix '%s' contains invalid character '%s'",
                prefix,
                repr(invalid_char),
            )
            return False

    return True


def create_branch_pattern(release_prefix: str) -> re.Pattern[str]:
    """Create regex pattern for release branches with given prefix.

    The pattern matches branches of the form {prefix}X.Y where X and Y are
    non-negative integers without leading zeros (SemVer 2.0.0 compliant).

    Args:
        release_prefix: The prefix for release branches (e.g., 'release/v', 'v', 'pkg-v').

    Returns:
        Compiled regex pattern matching {prefix}X.Y where X, Y are valid SemVer numbers.

    Examples:
        >>> pattern = create_branch_pattern("release/v")
        >>> bool(pattern.match("release/v1.2"))
        True
        >>> pattern = create_branch_pattern("v")
        >>> bool(pattern.match("v1.2"))
        True
        >>> pattern = create_branch_pattern("pkg-")
        >>> bool(pattern.match("pkg-1.2"))
        True

    References:
        - Semantic Versioning 2.0.0: https://semver.org/
        - Requirements 1.4, 4.2
    """
    escaped_prefix = re.escape(release_prefix)
    pattern = f"^{escaped_prefix}(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$"
    return re.compile(pattern)


@dataclass
class BranchVersion:
    """Version information extracted from a release branch name."""

    major: int
    minor: int

    def __str__(self) -> str:
        """Return the version as a string (e.g., '1.2')."""
        return f"{self.major}.{self.minor}"


def validate_branch(branch_name: str) -> bool:
    """Validate that a branch name matches the release/vX.Y pattern.

    The pattern enforces SemVer 2.0.0 rule 2: version numbers MUST NOT
    contain leading zeroes (except for 0 itself).

    Args:
        branch_name: The branch name to validate (e.g., 'release/v1.2').

    Returns:
        True if the branch matches the release/vX.Y pattern, False otherwise.

    Examples:
        >>> validate_branch("release/v1.2")
        True
        >>> validate_branch("release/v0.1")
        True
        >>> validate_branch("release/v01.2")  # Leading zero - invalid
        False
        >>> validate_branch("feature/v1.2")  # Wrong prefix - invalid
        False

    References:
        - SemVer 2.0.0 Rule 2: https://semver.org/#spec-item-2
    """
    if not branch_name:
        logger.warning("Empty branch name provided")
        return False

    match = RELEASE_BRANCH_PATTERN.match(branch_name)
    if match:
        return True

    logger.warning(
        "Branch '%s' does not match release/vX.Y pattern. Skipping.",
        branch_name,
    )
    return False


def extract_version(branch_name: str) -> BranchVersion | None:
    """Extract major and minor version numbers from a release branch name.

    Args:
        branch_name: The branch name to extract version from (e.g., 'release/v1.2').

    Returns:
        BranchVersion with major and minor numbers, or None if branch is invalid.

    Examples:
        >>> version = extract_version("release/v1.2")
        >>> version.major
        1
        >>> version.minor
        2
        >>> extract_version("invalid/branch") is None
        True

    References:
        - Requirements 1.1, 1.2, 1.3
    """
    if not branch_name:
        logger.warning("Empty branch name provided")
        return None

    match = RELEASE_BRANCH_PATTERN.match(branch_name)
    if not match:
        logger.warning(
            "Cannot extract version from '%s': does not match release/vX.Y pattern",
            branch_name,
        )
        return None

    major = int(match.group(1))
    minor = int(match.group(2))

    return BranchVersion(major=major, minor=minor)


def parse_branch(branch_name: str, release_prefix: str = "release/v") -> BranchVersion | None:
    """Parse a branch name and extract version information using configurable prefix.

    This function validates the branch name against the configured release prefix
    pattern and extracts the major and minor version numbers.

    Args:
        branch_name: The branch name to parse (e.g., 'release/v1.2', 'v1.2', 'pkg-1.2').
        release_prefix: The prefix for release branches (default: 'release/v').

    Returns:
        BranchVersion with major and minor numbers, or None if branch is invalid.

    Examples:
        >>> version = parse_branch("release/v1.2")
        >>> version.major, version.minor
        (1, 2)
        >>> version = parse_branch("v1.2", release_prefix="v")
        >>> version.major, version.minor
        (1, 2)
        >>> version = parse_branch("pkg-1.2", release_prefix="pkg-")
        >>> version.major, version.minor
        (1, 2)
        >>> parse_branch("v1.2") is None  # Wrong prefix for default
        True

    References:
        - Semantic Versioning 2.0.0: https://semver.org/
        - Requirements 3.1, 3.5, 4.1
    """
    if not branch_name:
        logger.warning("Empty branch name provided")
        return None

    pattern = create_branch_pattern(release_prefix)
    match = pattern.match(branch_name)

    if not match:
        logger.warning(
            "Branch '%s' does not match %sX.Y pattern. Skipping.",
            branch_name,
            release_prefix,
        )
        return None

    major = int(match.group(1))
    minor = int(match.group(2))

    return BranchVersion(major=major, minor=minor)


def should_skip_minor_alias(release_prefix: str, tag_prefix: str) -> bool:
    """Determine if minor alias should be skipped to avoid branch/tag conflict.

    When the release prefix equals the tag prefix, creating a minor alias tag
    (e.g., 'v1.2') would conflict with the branch name (e.g., 'v1.2' branch).
    In this case, the minor alias should be skipped.

    Args:
        release_prefix: The configured release branch prefix.
        tag_prefix: The configured tag prefix.

    Returns:
        True if minor alias should be skipped (prefixes match), False otherwise.

    Examples:
        >>> should_skip_minor_alias("release/v", "v")  # Different - create alias
        False
        >>> should_skip_minor_alias("v", "v")  # Same - skip alias
        True
        >>> should_skip_minor_alias("pkg-v", "pkg-v")  # Same - skip alias
        True
        >>> should_skip_minor_alias("pkg-release/v", "pkg-v")  # Different - create alias
        False

    References:
        - Requirements 2.5
    """
    return release_prefix == tag_prefix
