# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Alias tag management for semantic versioning releases.

This module handles major ({prefix}X) and minor ({prefix}X.Y) alias tag updates
with multi-branch support according to SemVer 2.0.0 conventions.

References:
    - Semantic Versioning 2.0.0: https://semver.org/
    - Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from src.tags import is_rc_tag

if TYPE_CHECKING:
    from src.github_api import GitHubAPI

logger = logging.getLogger(__name__)

# Re-export is_rc_tag for backwards compatibility
__all__ = [
    "is_rc_tag",
    "parse_release_tag",
    "find_highest_major_version",
    "find_highest_minor_version",
    "update_alias_tags",
    "should_update_major_alias",
    "should_update_minor_alias",
]


def _create_patch_pattern(tag_prefix: str) -> re.Pattern[str]:
    """Create regex pattern for GA/patch tags with given prefix.

    Args:
        tag_prefix: The prefix for tags (e.g., 'v', 'pkg-v').

    Returns:
        Compiled regex pattern matching {prefix}X.Y.Z.
    """
    escaped_prefix = re.escape(tag_prefix)
    return re.compile(f"^{escaped_prefix}(\\d+)\\.(\\d+)\\.(\\d+)$")


def parse_release_tag(tag_name: str, tag_prefix: str = "v") -> tuple[int, int, int] | None:
    """Parse a release tag into (major, minor, patch) components.

    Args:
        tag_name: The tag name to parse (e.g., 'v1.2.3').
        tag_prefix: The tag prefix to match (default: 'v').

    Returns:
        Tuple of (major, minor, patch) or None if not a valid release tag.

    Examples:
        >>> parse_release_tag("v1.2.3")
        (1, 2, 3)
        >>> parse_release_tag("v1.2.0-rc1")
        None
    """
    pattern = _create_patch_pattern(tag_prefix)
    match = pattern.match(tag_name)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None


def find_highest_major_version(api: GitHubAPI, major: int, tag_prefix: str = "v") -> tuple[int, int, int] | None:
    """Find the highest {prefix}X.*.* release across all branches for a given major version.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number to search for.
        tag_prefix: The tag prefix to match (default: 'v').

    Returns:
        Tuple of (major, minor, patch) for the highest release, or None if none found.

    Examples:
        >>> # With tags v2.0.0, v2.1.3, v2.2.1
        >>> find_highest_major_version(api, 2)
        (2, 2, 1)

    References:
        - Requirements 6.1, 7.3
    """
    tags = api.list_tags()
    highest: tuple[int, int, int] | None = None

    for tag in tags:
        parsed = parse_release_tag(tag.name, tag_prefix)
        if parsed is None:
            continue

        tag_major, tag_minor, tag_patch = parsed
        if tag_major != major:
            continue

        if highest is None:
            highest = parsed
        else:
            # Compare (minor, patch) tuples
            if (tag_minor, tag_patch) > (highest[1], highest[2]):
                highest = parsed

    return highest


def find_highest_minor_version(
    api: GitHubAPI, major: int, minor: int, tag_prefix: str = "v"
) -> tuple[int, int, int] | None:
    """Find the highest {prefix}X.Y.* release in a minor series.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number.
        minor: Minor version number.
        tag_prefix: The tag prefix to match (default: 'v').

    Returns:
        Tuple of (major, minor, patch) for the highest release, or None if none found.

    Examples:
        >>> # With tags v1.2.0, v1.2.1, v1.2.5
        >>> find_highest_minor_version(api, 1, 2)
        (1, 2, 5)

    References:
        - Requirements 6.2, 7.2
    """
    tags = api.list_tags()
    highest: tuple[int, int, int] | None = None

    for tag in tags:
        parsed = parse_release_tag(tag.name, tag_prefix)
        if parsed is None:
            continue

        tag_major, tag_minor, tag_patch = parsed
        if tag_major != major or tag_minor != minor:
            continue

        if highest is None or tag_patch > highest[2]:
            highest = parsed

    return highest


def update_alias_tags(
    api: GitHubAPI,
    tag_name: str,
    commit_sha: str,
    tag_prefix: str = "v",
    skip_minor_alias: bool = False,
) -> dict[str, bool]:
    """Update major ({prefix}X) and minor ({prefix}X.Y) alias tags for a release.

    Skips alias updates for RC releases. Uses force-push to update
    movable alias tags.

    Args:
        api: GitHubAPI instance for tag operations.
        tag_name: The release tag name (e.g., 'v1.2.3').
        commit_sha: SHA of the commit the release tag points to.
        tag_prefix: The tag prefix to use for aliases (default: 'v').
        skip_minor_alias: If True, skip creating the minor alias to avoid
            branch/tag conflict when release_prefix == tag_prefix.

    Returns:
        Dict with 'major' and 'minor' keys indicating if each alias was updated.

    Examples:
        >>> update_alias_tags(api, "v1.2.3", "abc123")
        {'major': True, 'minor': True}
        >>> update_alias_tags(api, "v1.2.0-rc1", "abc123")
        {'major': False, 'minor': False}

    References:
        - Requirements 2.5, 6.1, 6.2, 6.3, 6.4, 7.3
    """
    result = {"major": False, "minor": False}

    # Skip alias updates for RC releases
    if is_rc_tag(tag_name, tag_prefix):
        logger.info("Skipping alias updates for RC release '%s'", tag_name)
        return result

    parsed = parse_release_tag(tag_name, tag_prefix)
    if parsed is None:
        logger.warning("Cannot parse release tag '%s', skipping alias updates", tag_name)
        return result

    major, minor, patch = parsed

    # Update minor alias ({prefix}X.Y) if this is the highest patch in the series
    # Skip if skip_minor_alias is True (to avoid branch/tag conflict)
    if not skip_minor_alias:
        minor_alias = f"{tag_prefix}{major}.{minor}"
        highest_minor = find_highest_minor_version(api, major, minor, tag_prefix)

        if highest_minor is not None and (major, minor, patch) >= highest_minor:
            _update_or_create_alias(api, minor_alias, commit_sha)
            result["minor"] = True
            logger.info("Updated minor alias '%s' to point to '%s'", minor_alias, tag_name)
    else:
        logger.info(
            "Skipping minor alias '%s%d.%d' to avoid conflict with release branch",
            tag_prefix,
            major,
            minor,
        )

    # Update major alias ({prefix}X) if this is the highest release in the major series
    major_alias = f"{tag_prefix}{major}"
    highest_major = find_highest_major_version(api, major, tag_prefix)

    if highest_major is not None and (major, minor, patch) >= highest_major:
        _update_or_create_alias(api, major_alias, commit_sha)
        result["major"] = True
        logger.info("Updated major alias '%s' to point to '%s'", major_alias, tag_name)

    return result


def _update_or_create_alias(api: GitHubAPI, alias_name: str, commit_sha: str) -> None:
    """Update an existing alias tag or create it if it doesn't exist.

    Args:
        api: GitHubAPI instance for tag operations.
        alias_name: Name of the alias tag (e.g., 'v1' or 'v1.2').
        commit_sha: SHA of the commit to point to.

    References:
        - Requirements 6.3
    """
    if api.tag_exists(alias_name):
        logger.debug("Force-updating alias tag '%s'", alias_name)
        api.update_tag(alias_name, commit_sha)
    else:
        logger.debug("Creating new alias tag '%s'", alias_name)
        api.create_tag(alias_name, commit_sha, f"Alias tag {alias_name}")


def should_update_major_alias(
    api: GitHubAPI,
    major: int,
    minor: int,
    patch: int,
    tag_prefix: str = "v",
) -> bool:
    """Check if a release should update the major alias tag.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number.
        minor: Minor version number.
        patch: Patch version number.
        tag_prefix: The tag prefix to match (default: 'v').

    Returns:
        True if this release is the highest in the major series.

    Examples:
        >>> # With existing v2.1.3, checking v2.2.0
        >>> should_update_major_alias(api, 2, 2, 0)
        True

    References:
        - Requirements 6.1, 7.3
    """
    highest = find_highest_major_version(api, major, tag_prefix)
    if highest is None:
        return True
    return (major, minor, patch) >= highest


def should_update_minor_alias(
    api: GitHubAPI,
    major: int,
    minor: int,
    patch: int,
    tag_prefix: str = "v",
) -> bool:
    """Check if a release should update the minor alias tag.

    Args:
        api: GitHubAPI instance for fetching tags.
        major: Major version number.
        minor: Minor version number.
        patch: Patch version number.
        tag_prefix: The tag prefix to match (default: 'v').

    Returns:
        True if this release is the highest in the minor series.

    Examples:
        >>> # With existing v1.2.3, checking v1.2.4
        >>> should_update_minor_alias(api, 1, 2, 4)
        True

    References:
        - Requirements 6.2, 7.2
    """
    highest = find_highest_minor_version(api, major, minor, tag_prefix)
    if highest is None:
        return True
    return (major, minor, patch) >= highest
