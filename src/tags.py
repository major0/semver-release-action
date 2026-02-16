# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Tag management for semantic versioning releases.

This module handles RC tag creation, patch tag creation, and tag discovery
according to SemVer 2.0.0 conventions.

References:
    - Semantic Versioning 2.0.0: https://semver.org/
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.github_api import GitHubAPI

logger = logging.getLogger(__name__)

# Pattern for RC tags: vX.Y.0-rcN
RC_TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.0-rc(\d+)$")

# Pattern for GA/patch tags: vX.Y.Z (where Z >= 0)
PATCH_TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def find_latest_rc(api: GitHubAPI, major: int, minor: int) -> int | None:
    """Find the highest RC number for vX.Y.0-rcN tags.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number.
        minor: Minor version number.

    Returns:
        The highest RC number found, or None if no RC tags exist.

    Examples:
        >>> # With tags v1.2.0-rc1, v1.2.0-rc2, v1.2.0-rc3
        >>> find_latest_rc(api, 1, 2)
        3

    References:
        - Requirements 3.2, 3.3
    """
    tags = api.list_tags()
    highest_rc = None

    for tag in tags:
        match = RC_TAG_PATTERN.match(tag.name)
        if match:
            tag_major = int(match.group(1))
            tag_minor = int(match.group(2))
            rc_num = int(match.group(3))

            if tag_major == major and tag_minor == minor and (highest_rc is None or rc_num > highest_rc):
                highest_rc = rc_num

    return highest_rc


def find_latest_patch(api: GitHubAPI, major: int, minor: int) -> int | None:
    """Find the highest patch number for vX.Y.Z tags.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number.
        minor: Minor version number.

    Returns:
        The highest patch number found, or None if no patch tags exist.

    Examples:
        >>> # With tags v1.2.0, v1.2.1, v1.2.2
        >>> find_latest_patch(api, 1, 2)
        2

    References:
        - Requirements 4.2, 4.3
    """
    tags = api.list_tags()
    highest_patch = None

    for tag in tags:
        match = PATCH_TAG_PATTERN.match(tag.name)
        if match:
            tag_major = int(match.group(1))
            tag_minor = int(match.group(2))
            patch_num = int(match.group(3))

            if tag_major == major and tag_minor == minor and (highest_patch is None or patch_num > highest_patch):
                highest_patch = patch_num

    return highest_patch


def ga_exists(api: GitHubAPI, major: int, minor: int) -> bool:
    """Check if a GA release (vX.Y.0) exists for the given version.

    Args:
        api: GitHubAPI instance for checking tags.
        major: Major version number.
        minor: Minor version number.

    Returns:
        True if the GA release tag exists, False otherwise.

    Examples:
        >>> ga_exists(api, 1, 2)  # Checks for v1.2.0
        True

    References:
        - Requirements 3.1, 4.1
    """
    ga_tag = f"v{major}.{minor}.0"
    return api.tag_exists(ga_tag)


def create_tag(
    api: GitHubAPI,
    tag_name: str,
    commit_sha: str,
    message: str | None = None,
) -> None:
    """Create an annotated tag with release metadata.

    Args:
        api: GitHubAPI instance for creating tags.
        tag_name: Name of the tag to create (e.g., 'v1.2.0-rc1').
        commit_sha: SHA of the commit to tag.
        message: Optional tag annotation message. Defaults to 'Release {tag_name}'.

    Raises:
        GithubException: If tag creation fails.

    Examples:
        >>> create_tag(api, "v1.2.0-rc1", "abc123")
        >>> create_tag(api, "v1.2.0", "def456", "GA Release v1.2.0")

    References:
        - Requirements 2.2, 2.3
    """
    tag_message = message or f"Release {tag_name}"
    logger.info("Creating tag '%s' at commit %s", tag_name, commit_sha[:7])
    api.create_tag(tag_name, commit_sha, tag_message)


def increment_rc(current_rc: int | None) -> int:
    """Return the next RC number.

    Args:
        current_rc: The current highest RC number, or None if no RCs exist.

    Returns:
        The next RC number (1 if no RCs exist, otherwise current + 1).

    Examples:
        >>> increment_rc(None)
        1
        >>> increment_rc(3)
        4

    References:
        - Requirements 3.2
    """
    if current_rc is None:
        return 1
    return current_rc + 1


def increment_patch(current_patch: int | None) -> int:
    """Return the next patch number.

    Args:
        current_patch: The current highest patch number, or None if no patches exist.

    Returns:
        The next patch number (1 if only GA exists, otherwise current + 1).

    Examples:
        >>> increment_patch(0)  # After GA release v1.2.0
        1
        >>> increment_patch(2)  # After v1.2.2
        3

    References:
        - Requirements 4.2
    """
    if current_patch is None:
        return 1
    return current_patch + 1


def get_next_rc_tag(api: GitHubAPI, major: int, minor: int) -> str:
    """Get the next RC tag name for a version.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number.
        minor: Minor version number.

    Returns:
        The next RC tag name (e.g., 'v1.2.0-rc1' or 'v1.2.0-rc4').

    Examples:
        >>> get_next_rc_tag(api, 1, 2)  # No existing RCs
        'v1.2.0-rc1'
        >>> get_next_rc_tag(api, 1, 2)  # After v1.2.0-rc3
        'v1.2.0-rc4'

    References:
        - Requirements 2.1, 3.1, 3.2, 3.3
    """
    latest_rc = find_latest_rc(api, major, minor)
    next_rc = increment_rc(latest_rc)
    return f"v{major}.{minor}.0-rc{next_rc}"


def get_next_patch_tag(api: GitHubAPI, major: int, minor: int) -> str:
    """Get the next patch tag name for a version.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number.
        minor: Minor version number.

    Returns:
        The next patch tag name (e.g., 'v1.2.1' or 'v1.2.5').

    Examples:
        >>> get_next_patch_tag(api, 1, 2)  # After GA v1.2.0
        'v1.2.1'
        >>> get_next_patch_tag(api, 1, 2)  # After v1.2.4
        'v1.2.5'

    References:
        - Requirements 4.1, 4.2, 4.3
    """
    latest_patch = find_latest_patch(api, major, minor)
    next_patch = increment_patch(latest_patch)
    return f"v{major}.{minor}.{next_patch}"


def is_rc_tag(tag_name: str) -> bool:
    """Check if a tag is an RC tag.

    Args:
        tag_name: The tag name to check.

    Returns:
        True if the tag matches the RC pattern, False otherwise.

    Examples:
        >>> is_rc_tag("v1.2.0-rc1")
        True
        >>> is_rc_tag("v1.2.0")
        False
    """
    return RC_TAG_PATTERN.match(tag_name) is not None


def is_ga_tag(tag_name: str) -> bool:
    """Check if a tag is a GA tag (vX.Y.0).

    Args:
        tag_name: The tag name to check.

    Returns:
        True if the tag is a GA release (patch == 0), False otherwise.

    Examples:
        >>> is_ga_tag("v1.2.0")
        True
        >>> is_ga_tag("v1.2.1")
        False
        >>> is_ga_tag("v1.2.0-rc1")
        False
    """
    match = PATCH_TAG_PATTERN.match(tag_name)
    if match:
        patch = int(match.group(3))
        return patch == 0
    return False


def is_patch_tag(tag_name: str) -> bool:
    """Check if a tag is a patch tag (vX.Y.Z where Z > 0).

    Args:
        tag_name: The tag name to check.

    Returns:
        True if the tag is a patch release (patch > 0), False otherwise.

    Examples:
        >>> is_patch_tag("v1.2.1")
        True
        >>> is_patch_tag("v1.2.0")
        False
        >>> is_patch_tag("v1.2.0-rc1")
        False
    """
    match = PATCH_TAG_PATTERN.match(tag_name)
    if match:
        patch = int(match.group(3))
        return patch > 0
    return False
