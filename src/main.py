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

import logging
import os
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.aliases import update_alias_tags
from src.branch import extract_version, validate_branch
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


def parse_inputs() -> ActionInputs:
    """Parse action inputs from environment variables.

    Returns:
        ActionInputs with parsed values.

    References:
        - Requirements 8.3, 8.4, 8.5, 8.7
    """
    return ActionInputs(
        token=os.environ.get("INPUT_TOKEN", os.environ.get("GITHUB_TOKEN", "")),
        debug=os.environ.get("INPUT_DEBUG", "false").lower() == "true",
        dry_run=os.environ.get("INPUT_DRY_RUN", "false").lower() == "true",
        target_branch=os.environ.get("INPUT_TARGET_BRANCH", ""),
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

    Creates the initial vX.Y.0-rc1 tag when a release branch is created.

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

    if not validate_branch(branch_name):
        logger.info("Branch '%s' is not a release branch, skipping", branch_name)
        return outputs

    version = extract_version(branch_name)
    if version is None:
        return outputs

    tag_name = f"v{version.major}.{version.minor}.0-rc1"
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

    if not validate_branch(branch):
        logger.info("Branch '%s' is not a release branch, skipping", branch)
        return outputs

    version = extract_version(branch)
    if version is None:
        return outputs

    outputs.major = str(version.major)
    outputs.minor = str(version.minor)

    if ga_exists(api, version.major, version.minor):
        # GA exists, create next patch tag
        tag_name = get_next_patch_tag(api, version.major, version.minor)
        outputs.tag = tag_name
        outputs.tag_type = "patch"

        if inputs.dry_run:
            logger.info("[DRY-RUN] Would create patch tag '%s' at %s", tag_name, context.sha[:7])
        else:
            create_tag(api, tag_name, context.sha, f"Patch release {tag_name}")
            logger.info("Created patch tag '%s'", tag_name)
            # Update alias tags for non-RC releases
            update_alias_tags(api, tag_name, context.sha)
    else:
        # No GA, create next RC tag
        tag_name = get_next_rc_tag(api, version.major, version.minor)
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
    version = _parse_tag_version(tag_name)
    if version is None:
        logger.warning("Tag '%s' is not a valid SemVer tag, skipping", tag_name)
        return outputs

    major, minor = version
    outputs.major = str(major)
    outputs.minor = str(minor)
    outputs.tag = tag_name

    # Determine the corresponding release branch
    release_branch = f"release/v{major}.{minor}"

    # Validate tag points to a commit on the release branch
    if not _validate_tag_on_branch(api, context.sha, release_branch):
        logger.error(
            "Tag '%s' does not point to a commit on branch '%s'",
            tag_name,
            release_branch,
        )
        sys.exit(1)

    # Determine tag type
    if is_rc_tag(tag_name):
        outputs.tag_type = "rc"
        logger.info("Validated RC tag '%s'", tag_name)
    elif is_ga_tag(tag_name):
        outputs.tag_type = "ga"
        logger.info("Validated GA tag '%s'", tag_name)
        if not inputs.dry_run:
            update_alias_tags(api, tag_name, context.sha)
    else:
        outputs.tag_type = "patch"
        logger.info("Validated patch tag '%s'", tag_name)
        if not inputs.dry_run:
            update_alias_tags(api, tag_name, context.sha)

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

    if not validate_branch(target_branch):
        logger.error("target-branch '%s' must match release/vX.Y pattern", target_branch)
        sys.exit(1)

    logger.info("Processing workflow_dispatch for branch '%s'", target_branch)

    # Simulate commit push behavior for the target branch
    return handle_commit_push(api, context, inputs, branch_name=target_branch)


def _parse_tag_version(tag_name: str) -> tuple[int, int] | None:
    """Parse major and minor version from a tag name.

    Args:
        tag_name: Tag name (e.g., 'v1.2.0', 'v1.2.0-rc1', 'v1.2.3').

    Returns:
        Tuple of (major, minor) or None if not a valid version tag.
    """
    import re

    # Match RC tags: vX.Y.0-rcN
    rc_match = re.match(r"^v(\d+)\.(\d+)\.0-rc\d+$", tag_name)
    if rc_match:
        return int(rc_match.group(1)), int(rc_match.group(2))

    # Match GA/patch tags: vX.Y.Z
    patch_match = re.match(r"^v(\d+)\.(\d+)\.\d+$", tag_name)
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
    if not inputs.dry_run or inputs.token:
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
