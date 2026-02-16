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
