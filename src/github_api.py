# Copyright (c) 2026 Mark Ferrell. MIT License.
"""GitHub API wrapper for tag and branch operations.

References:
    - GitHub REST API: https://docs.github.com/en/rest
    - PyGithub Documentation: https://pygithub.readthedocs.io/
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from github import Github
from github.GithubException import GithubException

if TYPE_CHECKING:
    from github.Commit import Commit
    from github.Tag import Tag


class GitHubAPI:
    """Wrapper around PyGithub for tag and branch operations.

    Handles authentication via token input, defaulting to GITHUB_TOKEN
    environment variable if not provided.

    References:
        - Authentication: https://docs.github.com/en/rest/authentication
        - GITHUB_TOKEN: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
    """

    def __init__(self, token: str | None = None, repository: str | None = None) -> None:
        """Initialize the GitHub API client.

        Args:
            token: GitHub token for authentication. Defaults to GITHUB_TOKEN env var.
            repository: Repository in 'owner/repo' format. Defaults to GITHUB_REPOSITORY env var.

        References:
            - Get a repository: https://docs.github.com/en/rest/repos/repos#get-a-repository
        """
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._repository = repository or os.environ.get("GITHUB_REPOSITORY", "")

        if not self._token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN or pass token parameter.")
        if not self._repository:
            raise ValueError("Repository is required. Set GITHUB_REPOSITORY or pass repository parameter.")

        self._github = Github(self._token)
        self._repo = self._github.get_repo(self._repository)

    def list_tags(self) -> list[Tag]:
        """List all tags in the repository.

        Returns:
            List of Tag objects from the repository.

        References:
            - List repository tags: https://docs.github.com/en/rest/repos/repos#list-repository-tags
        """
        return list(self._repo.get_tags())

    def create_tag(
        self,
        tag_name: str,
        commit_sha: str,
        message: str = "",
    ) -> None:
        """Create an annotated tag pointing to a commit.

        Args:
            tag_name: Name of the tag to create (e.g., 'v1.2.0-rc1').
            commit_sha: SHA of the commit to tag.
            message: Tag annotation message.

        Raises:
            GithubException: If tag creation fails.

        References:
            - Create a tag object: https://docs.github.com/en/rest/git/tags#create-a-tag-object
            - Create a reference: https://docs.github.com/en/rest/git/refs#create-a-reference
        """
        # Create the tag object (annotated tag)
        tag_object = self._repo.create_git_tag(
            tag=tag_name,
            message=message or f"Release {tag_name}",
            object=commit_sha,
            type="commit",
        )

        # Create the reference pointing to the tag object
        self._repo.create_git_ref(
            ref=f"refs/tags/{tag_name}",
            sha=tag_object.sha,
        )

    def update_tag(self, tag_name: str, commit_sha: str) -> None:
        """Update an existing tag to point to a new commit (force-push).

        Used for updating movable alias tags (e.g., v1, v1.2).

        Args:
            tag_name: Name of the tag to update.
            commit_sha: SHA of the new commit to point to.

        Raises:
            GithubException: If tag update fails.

        References:
            - Update a reference: https://docs.github.com/en/rest/git/refs#update-a-reference
        """
        ref = self._repo.get_git_ref(f"tags/{tag_name}")
        ref.edit(sha=commit_sha, force=True)

    def get_branch_commits(self, branch_name: str) -> list[Commit]:
        """Get commits from a branch.

        Args:
            branch_name: Name of the branch (e.g., 'release/v1.2').

        Returns:
            List of Commit objects from the branch.

        Raises:
            GithubException: If branch doesn't exist or access fails.

        References:
            - List commits: https://docs.github.com/en/rest/commits/commits#list-commits
        """
        return list(self._repo.get_commits(sha=branch_name))

    def tag_exists(self, tag_name: str) -> bool:
        """Check if a tag exists in the repository.

        Args:
            tag_name: Name of the tag to check.

        Returns:
            True if the tag exists, False otherwise.

        References:
            - Get a reference: https://docs.github.com/en/rest/git/refs#get-a-reference
        """
        try:
            self._repo.get_git_ref(f"tags/{tag_name}")
            return True
        except GithubException:
            return False

    def get_tag_commit_sha(self, tag_name: str) -> str | None:
        """Get the commit SHA that a tag points to.

        Args:
            tag_name: Name of the tag.

        Returns:
            Commit SHA string, or None if tag doesn't exist.

        References:
            - Get a reference: https://docs.github.com/en/rest/git/refs#get-a-reference
            - Get a tag: https://docs.github.com/en/rest/git/tags#get-a-tag
        """
        try:
            ref = self._repo.get_git_ref(f"tags/{tag_name}")
            # Handle annotated tags (need to dereference)
            tag_sha = ref.object.sha
            if ref.object.type == "tag":
                tag_obj = self._repo.get_git_tag(tag_sha)
                return tag_obj.object.sha
            return tag_sha
        except GithubException:
            return None
