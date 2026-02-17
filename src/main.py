# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Main entry point for the Semantic Versioning Release Action.

This module handles GitHub event routing and orchestrates the release workflow.

References:
    - GitHub Actions Environment Variables:
      https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables#default-environment-variables
    - GitHub Actions Outputs:
      https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/passing-information-between-jobs#setting-an-output-parameter
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.aliases import update_alias_tags
from src.branch import (
    parse_branch,
    should_skip_minor_alias,
    validate_prefix,
)
from src.github_api import GitHubAPI
from src.tags import (
    create_tag,
    ga_exists,
    get_next_patch_tag,
    get_next_rc_tag,
    is_ga_tag,
    is_rc_tag,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ActionInputs:
    """Parsed action inputs from environment variables."""

    token: str
    debug: bool
    dry_run: bool
    target_branch: str
    aliases: bool = False
    release_prefix: str = "release/v"
    tag_prefix: str = "v"


@dataclass
class GitHubContext:
    """GitHub event context from environment variables."""

    event_name: str
    ref_name: str
    ref_type: str
    sha: str
    repository: str


@dataclass
class ActionOutputs:
    """Action outputs to be written to GITHUB_OUTPUT."""

    tag: str = ""
    tag_type: str = "skipped"
    major: str = ""
    minor: str = ""


def parse_inputs(args: list[str] | None = None) -> ActionInputs:
    """Parse action inputs from CLI arguments or environment variables.

    CLI arguments take precedence over environment variables.
    When run as a GitHub Action, environment variables are used.
    When run from CLI, arguments can be provided directly.

    Args:
        args: Optional list of CLI arguments. If None, uses environment
              variables only (GitHub Actions mode). Pass sys.argv[1:] for
              CLI mode.

    Returns:
        ActionInputs with parsed values.

    References:
        - Requirements 8.3, 8.4, 8.5, 8.7
    """
    parser = argparse.ArgumentParser(
        description="Semantic Versioning Release Action - Automate SemVer tagging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (used as defaults when CLI args not provided):
  INPUT_TOKEN, GITHUB_TOKEN    GitHub token for authentication
  INPUT_DEBUG                  Enable debug logging (true/false)
  INPUT_DRY_RUN                Dry-run mode, don't create tags (true/false)
  INPUT_TARGET_BRANCH          Target branch for workflow_dispatch
  INPUT_ALIASES                Update alias tags (true/false)

Examples:
  # Run with environment variables (GitHub Actions mode)
  python -m src.main

  # Run with CLI arguments (local testing)
  python -m src.main --token ghp_xxx --dry-run --debug

  # Override specific options
  python -m src.main --target-branch release/v1.2 --dry-run
        """,
    )

    parser.add_argument(
        "--token",
        default=os.environ.get("INPUT_TOKEN", os.environ.get("GITHUB_TOKEN", "")),
        help="GitHub token for authentication (default: from INPUT_TOKEN or GITHUB_TOKEN env)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.environ.get("INPUT_DEBUG", "false").lower() == "true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("INPUT_DRY_RUN", "false").lower() == "true",
        help="Dry-run mode - don't actually create tags",
    )
    parser.add_argument(
        "--target-branch",
        default=os.environ.get("INPUT_TARGET_BRANCH", ""),
        help="Target branch for workflow_dispatch events",
    )
    parser.add_argument(
        "--aliases",
        action="store_true",
        default=os.environ.get("INPUT_ALIASES", "false").lower() == "true",
        help="Update major (vX) and minor (vX.Y) alias tags",
    )
    parser.add_argument(
        "--release-prefix",
        default=os.environ.get("INPUT_RELEASE_PREFIX", "release/v"),
        help="Prefix for release branch names (default: release/v)",
    )
    parser.add_argument(
        "--tag-prefix",
        default=os.environ.get("INPUT_TAG_PREFIX", "v"),
        help="Prefix for version tags and aliases (default: v)",
    )

    # Use empty list for GitHub Actions mode (env vars only), or provided args for CLI
    parsed = parser.parse_args(args if args is not None else [])

    # Validate prefixes
    if not validate_prefix(parsed.release_prefix):
        logger.error(
            "Invalid release-prefix '%s': must be non-empty and not contain "
            "invalid git ref characters (.. ~ ^ : \\ space tab newline * ? [)",
            parsed.release_prefix,
        )
        sys.exit(1)

    if not validate_prefix(parsed.tag_prefix):
        logger.error(
            "Invalid tag-prefix '%s': must be non-empty and not contain "
            "invalid git ref characters (.. ~ ^ : \\ space tab newline * ? [)",
            parsed.tag_prefix,
        )
        sys.exit(1)

    return ActionInputs(
        token=parsed.token,
        debug=parsed.debug,
        dry_run=parsed.dry_run,
        target_branch=parsed.target_branch,
        aliases=parsed.aliases,
        release_prefix=parsed.release_prefix,
        tag_prefix=parsed.tag_prefix,
    )


def parse_context() -> GitHubContext:
    """Parse GitHub context from environment variables.

    Returns:
        GitHubContext with event information.

    References:
        - https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables#default-environment-variables
    """
    return GitHubContext(
        event_name=os.environ.get("GITHUB_EVENT_NAME", ""),
        ref_name=os.environ.get("GITHUB_REF_NAME", ""),
        ref_type=os.environ.get("GITHUB_REF_TYPE", ""),
        sha=os.environ.get("GITHUB_SHA", ""),
        repository=os.environ.get("GITHUB_REPOSITORY", ""),
    )


def set_outputs(outputs: ActionOutputs) -> None:
    """Write action outputs to GITHUB_OUTPUT file.

    Args:
        outputs: ActionOutputs to write.

    References:
        - https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/passing-information-between-jobs#setting-an-output-parameter
    """
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if not output_file:
        logger.warning("GITHUB_OUTPUT not set, outputs will not be written")
        return

    with open(output_file, "a") as f:
        f.write(f"tag={outputs.tag}\n")
        f.write(f"tag-type={outputs.tag_type}\n")
        f.write(f"major={outputs.major}\n")
        f.write(f"minor={outputs.minor}\n")

    logger.info("Set outputs: tag=%s, tag-type=%s", outputs.tag, outputs.tag_type)


def configure_logging(debug: bool) -> None:
    """Configure logging based on debug flag.

    Args:
        debug: If True, enable DEBUG level logging.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def handle_branch_create(
    api: GitHubAPI,
    context: GitHubContext,
    inputs: ActionInputs,
) -> ActionOutputs:
    """Handle branch creation event.

    Creates the initial {tag_prefix}X.Y.0-rc1 tag when a release branch is created.

    Args:
        api: GitHubAPI instance.
        context: GitHub event context.
        inputs: Action inputs.

    Returns:
        ActionOutputs with created tag information.

    References:
        - Requirements 2.1, 2.2, 2.3
    """
    outputs = ActionOutputs()
    branch_name = context.ref_name

    version = parse_branch(branch_name, inputs.release_prefix)
    if version is None:
        logger.info(
            "Branch '%s' does not match %sX.Y pattern, skipping",
            branch_name,
            inputs.release_prefix,
        )
        return outputs

    tag_name = f"{inputs.tag_prefix}{version.major}.{version.minor}.0-rc1"
    outputs.tag = tag_name
    outputs.tag_type = "rc"
    outputs.major = str(version.major)
    outputs.minor = str(version.minor)

    if inputs.dry_run:
        logger.info("[DRY-RUN] Would create tag '%s' at %s", tag_name, context.sha[:7])
    else:
        create_tag(api, tag_name, context.sha, f"Release candidate {tag_name}")
        logger.info("Created initial RC tag '%s'", tag_name)

    return outputs


def _commit_has_version_tag(api: GitHubAPI, commit_sha: str, tag_prefix: str) -> str | None:
    """Check if a commit already has a version tag.

    Args:
        api: GitHubAPI instance.
        commit_sha: SHA of the commit to check.
        tag_prefix: The configured tag prefix.

    Returns:
        The existing tag name if found, None otherwise.
    """
    tags = api.list_tags()
    for tag in tags:
        if tag.commit.sha == commit_sha and tag.name.startswith(tag_prefix):
            return tag.name
    return None


def handle_commit_push(
    api: GitHubAPI,
    context: GitHubContext,
    inputs: ActionInputs,
    branch_name: str | None = None,
) -> ActionOutputs:
    """Handle commit push event to a release branch.

    Creates the next RC or patch tag depending on GA state.

    Args:
        api: GitHubAPI instance.
        context: GitHub event context.
        inputs: Action inputs.
        branch_name: Optional branch name override (for workflow_dispatch).

    Returns:
        ActionOutputs with created tag information.

    References:
        - Requirements 3.1, 3.2, 3.3, 4.1, 4.2, 4.3
    """
    outputs = ActionOutputs()
    branch = branch_name or context.ref_name

    version = parse_branch(branch, inputs.release_prefix)
    if version is None:
        logger.info(
            "Branch '%s' does not match %sX.Y pattern, skipping",
            branch,
            inputs.release_prefix,
        )
        return outputs

    outputs.major = str(version.major)
    outputs.minor = str(version.minor)

    # Check if commit already has a version tag
    existing_tag = _commit_has_version_tag(api, context.sha, inputs.tag_prefix)
    if existing_tag:
        logger.info(
            "Commit %s already has tag '%s', skipping tag creation",
            context.sha[:7],
            existing_tag,
        )
        outputs.tag = existing_tag
        outputs.tag_type = "skipped"
        return outputs

    if ga_exists(api, version.major, version.minor, inputs.tag_prefix):
        # GA exists, create next patch tag
        tag_name = get_next_patch_tag(api, version.major, version.minor, inputs.tag_prefix)
        outputs.tag = tag_name
        outputs.tag_type = "patch"

        if inputs.dry_run:
            logger.info("[DRY-RUN] Would create patch tag '%s' at %s", tag_name, context.sha[:7])
        else:
            create_tag(api, tag_name, context.sha, f"Patch release {tag_name}")
            logger.info("Created patch tag '%s'", tag_name)
            # Update alias tags for non-RC releases if enabled
            if inputs.aliases:
                _update_aliases_with_skip_logic(api, tag_name, context.sha, inputs)
    else:
        # No GA, create next RC tag
        tag_name = get_next_rc_tag(api, version.major, version.minor, inputs.tag_prefix)
        outputs.tag = tag_name
        outputs.tag_type = "rc"

        if inputs.dry_run:
            logger.info("[DRY-RUN] Would create RC tag '%s' at %s", tag_name, context.sha[:7])
        else:
            create_tag(api, tag_name, context.sha, f"Release candidate {tag_name}")
            logger.info("Created RC tag '%s'", tag_name)

    return outputs


def handle_tag_push(
    api: GitHubAPI,
    context: GitHubContext,
    inputs: ActionInputs,
) -> ActionOutputs:
    """Handle manual tag push event.

    Validates the tag points to a commit on the corresponding release branch
    and updates alias tags for GA/patch releases.

    Args:
        api: GitHubAPI instance.
        context: GitHub event context.
        inputs: Action inputs.

    Returns:
        ActionOutputs with validated tag information.

    References:
        - Requirements 5.1, 5.2, 5.3
    """
    outputs = ActionOutputs()
    tag_name = context.ref_name

    # Parse the tag to extract version info
    version = _parse_tag_version(tag_name, inputs.tag_prefix)
    if version is None:
        logger.warning(
            "Tag '%s' is not a valid SemVer tag with prefix '%s', skipping",
            tag_name,
            inputs.tag_prefix,
        )
        return outputs

    major, minor = version
    outputs.major = str(major)
    outputs.minor = str(minor)
    outputs.tag = tag_name

    # Determine the corresponding release branch
    release_branch = f"{inputs.release_prefix}{major}.{minor}"

    # Validate tag points to a commit on the release branch
    if not _validate_tag_on_branch(api, context.sha, release_branch):
        logger.error(
            "Tag '%s' does not point to a commit on branch '%s'",
            tag_name,
            release_branch,
        )
        sys.exit(1)

    # Determine tag type
    if is_rc_tag(tag_name, inputs.tag_prefix):
        outputs.tag_type = "rc"
        logger.info("Validated RC tag '%s'", tag_name)
    elif is_ga_tag(tag_name, inputs.tag_prefix):
        outputs.tag_type = "ga"
        logger.info("Validated GA tag '%s'", tag_name)
        if not inputs.dry_run and inputs.aliases:
            _update_aliases_with_skip_logic(api, tag_name, context.sha, inputs)
    else:
        outputs.tag_type = "patch"
        logger.info("Validated patch tag '%s'", tag_name)
        if not inputs.dry_run and inputs.aliases:
            _update_aliases_with_skip_logic(api, tag_name, context.sha, inputs)

    return outputs


def handle_workflow_dispatch(
    api: GitHubAPI,
    context: GitHubContext,
    inputs: ActionInputs,
) -> ActionOutputs:
    """Handle workflow_dispatch event for manual testing.

    Args:
        api: GitHubAPI instance.
        context: GitHub event context.
        inputs: Action inputs.

    Returns:
        ActionOutputs with created/simulated tag information.

    References:
        - Requirements 8.7, 9.4
    """
    # Get target branch from input or fall back to GITHUB_REF_NAME
    target_branch = inputs.target_branch or context.ref_name

    version = parse_branch(target_branch, inputs.release_prefix)
    if version is None:
        logger.error(
            "target-branch '%s' must match %sX.Y pattern",
            target_branch,
            inputs.release_prefix,
        )
        sys.exit(1)

    logger.info("Processing workflow_dispatch for branch '%s'", target_branch)

    # Simulate commit push behavior for the target branch
    return handle_commit_push(api, context, inputs, branch_name=target_branch)


def _parse_tag_version(tag_name: str, tag_prefix: str = "v") -> tuple[int, int] | None:
    """Parse major and minor version from a tag name.

    Args:
        tag_name: Tag name (e.g., 'v1.2.0', 'v1.2.0-rc1', 'v1.2.3').
        tag_prefix: The tag prefix to match (default: 'v').

    Returns:
        Tuple of (major, minor) or None if not a valid version tag.
    """
    import re

    escaped_prefix = re.escape(tag_prefix)

    # Match RC tags: {prefix}X.Y.0-rcN
    rc_pattern = f"^{escaped_prefix}(\\d+)\\.(\\d+)\\.0-rc\\d+$"
    rc_match = re.match(rc_pattern, tag_name)
    if rc_match:
        return int(rc_match.group(1)), int(rc_match.group(2))

    # Match GA/patch tags: {prefix}X.Y.Z
    patch_pattern = f"^{escaped_prefix}(\\d+)\\.(\\d+)\\.\\d+$"
    patch_match = re.match(patch_pattern, tag_name)
    if patch_match:
        return int(patch_match.group(1)), int(patch_match.group(2))

    return None


def _validate_tag_on_branch(api: GitHubAPI, commit_sha: str, branch_name: str) -> bool:
    """Validate that a commit is reachable from a branch.

    Args:
        api: GitHubAPI instance.
        commit_sha: SHA of the commit to validate.
        branch_name: Name of the branch to check.

    Returns:
        True if the commit is on the branch, False otherwise.
    """
    try:
        commits = api.get_branch_commits(branch_name)
        commit_shas = {c.sha for c in commits}
        return commit_sha in commit_shas
    except Exception as e:
        logger.error("Failed to get commits from branch '%s': %s", branch_name, e)
        return False


def _update_aliases_with_skip_logic(
    api: GitHubAPI,
    tag_name: str,
    commit_sha: str,
    inputs: ActionInputs,
) -> dict[str, bool]:
    """Update alias tags with skip logic for minor alias when prefixes match.

    Args:
        api: GitHubAPI instance for tag operations.
        tag_name: The release tag name (e.g., 'v1.2.3').
        commit_sha: SHA of the commit the release tag points to.
        inputs: Action inputs containing prefix configuration.

    Returns:
        Dict with 'major' and 'minor' keys indicating if each alias was updated.

    References:
        - Requirements 2.5
    """
    skip_minor = should_skip_minor_alias(inputs.release_prefix, inputs.tag_prefix)
    return update_alias_tags(
        api,
        tag_name,
        commit_sha,
        tag_prefix=inputs.tag_prefix,
        skip_minor_alias=skip_minor,
    )


def main() -> None:
    """Main entry point for the action."""
    inputs = parse_inputs()
    configure_logging(inputs.debug)

    context = parse_context()
    logger.debug(
        "Event: %s, Ref: %s (%s), SHA: %s", context.event_name, context.ref_name, context.ref_type, context.sha[:7]
    )

    if not inputs.token:
        logger.error("GitHub token is required. Set INPUT_TOKEN or GITHUB_TOKEN.")
        sys.exit(1)

    # Initialize API (skip for dry-run without token)
    api: GitHubAPI | None = None
    if not inputs.dry_run or inputs.token:  # pragma: no branch
        try:
            api = GitHubAPI(token=inputs.token, repository=context.repository)
        except ValueError as e:
            logger.error("Failed to initialize GitHub API: %s", e)
            sys.exit(1)

    # Route events to handlers
    outputs = ActionOutputs()

    if context.event_name == "create" and context.ref_type == "branch":
        if api is None:  # pragma: no cover
            logger.error("GitHub API required for branch creation")
            sys.exit(1)
        outputs = handle_branch_create(api, context, inputs)

    elif context.event_name == "push" and context.ref_type == "tag":
        if api is None:  # pragma: no cover
            logger.error("GitHub API required for tag push")
            sys.exit(1)
        outputs = handle_tag_push(api, context, inputs)

    elif context.event_name == "push" and context.ref_type == "branch":
        if api is None:  # pragma: no cover
            logger.error("GitHub API required for commit push")
            sys.exit(1)
        outputs = handle_commit_push(api, context, inputs)

    elif context.event_name == "workflow_dispatch":
        if api is None:  # pragma: no cover
            logger.error("GitHub API required for workflow_dispatch")
            sys.exit(1)
        outputs = handle_workflow_dispatch(api, context, inputs)

    else:
        logger.warning(
            "Unhandled event: %s (ref_type: %s). Skipping.",
            context.event_name,
            context.ref_type,
        )

    set_outputs(outputs)


if __name__ == "__main__":  # pragma: no cover
    main()
