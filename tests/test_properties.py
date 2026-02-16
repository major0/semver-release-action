# Copyright (c) 2026 Mark Ferrell. MIT License.
"""Property-based tests for the Semantic Versioning Release Action.

Uses hypothesis to generate random inputs and verify invariants hold
across all valid cases.

References:
    - Testing Strategy: .kiro/steering/testing-strategy.md
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.branch import extract_version, validate_branch

# Strategy for generating valid major/minor version numbers (SemVer 2.0.0 compliant)
# - 0 is valid
# - Positive integers without leading zeros
valid_version_number = st.integers(min_value=0, max_value=999)


# Strategy for generating valid release branch names
@st.composite
def valid_release_branch(draw: st.DrawFn) -> str:
    """Generate valid release/vX.Y branch names."""
    major = draw(valid_version_number)
    minor = draw(valid_version_number)
    return f"release/v{major}.{minor}"


# Strategy for generating invalid branch names with leading zeros
@st.composite
def branch_with_leading_zero(draw: st.DrawFn) -> str:
    """Generate branch names with leading zeros (invalid per SemVer 2.0.0)."""
    major = draw(st.integers(min_value=0, max_value=99))
    minor = draw(st.integers(min_value=0, max_value=99))
    # Decide which part gets the leading zero
    choice = draw(st.sampled_from(["major", "minor", "both"]))

    if choice == "major":
        # Leading zero in major (e.g., release/v01.2)
        major_str = f"0{major}" if major < 10 else f"0{major}"
        return f"release/v{major_str}.{minor}"
    elif choice == "minor":
        # Leading zero in minor (e.g., release/v1.02)
        minor_str = f"0{minor}" if minor < 10 else f"0{minor}"
        return f"release/v{major}.{minor_str}"
    else:
        # Leading zeros in both
        major_str = f"0{major}" if major < 10 else f"0{major}"
        minor_str = f"0{minor}" if minor < 10 else f"0{minor}"
        return f"release/v{major_str}.{minor_str}"


# Strategy for generating branch names with wrong prefix
@st.composite
def branch_with_wrong_prefix(draw: st.DrawFn) -> str:
    """Generate branch names with wrong prefix (not release/)."""
    prefix = draw(st.sampled_from(["feature/v", "bugfix/v", "hotfix/v", "main/v", "develop/v", "v", ""]))
    major = draw(valid_version_number)
    minor = draw(valid_version_number)
    return f"{prefix}{major}.{minor}"


# Strategy for generating branch names missing the 'v' prefix
@st.composite
def branch_missing_v(draw: st.DrawFn) -> str:
    """Generate release branches missing the 'v' prefix."""
    major = draw(valid_version_number)
    minor = draw(valid_version_number)
    return f"release/{major}.{minor}"


# Strategy for generating branch names with patch version (invalid)
@st.composite
def branch_with_patch(draw: st.DrawFn) -> str:
    """Generate branch names with patch version (invalid for release branches)."""
    major = draw(valid_version_number)
    minor = draw(valid_version_number)
    patch = draw(st.integers(min_value=0, max_value=99))
    return f"release/v{major}.{minor}.{patch}"


# Strategy for generating completely random strings
random_string = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=0,
    max_size=50,
)


class TestBranchPatternValidation:
    """Property 1: Branch Pattern Validation.

    *For any* branch name, the action SHALL only process branches matching
    `release/vX.Y` where X and Y are non-negative integers.

    **Validates: Requirements 1.1, 1.2**
    """

    @settings(max_examples=100)
    @given(branch=valid_release_branch())
    def test_valid_branches_are_accepted(self, branch: str) -> None:
        """Valid release/vX.Y patterns SHALL be accepted.

        **Validates: Requirements 1.1**
        """
        assert validate_branch(branch) is True, f"Expected valid branch '{branch}' to be accepted"

    @settings(max_examples=100)
    @given(branch=valid_release_branch())
    def test_valid_branches_extract_correct_version(self, branch: str) -> None:
        """Valid branches SHALL have correct version extraction.

        **Validates: Requirements 1.1, 1.3**
        """
        version = extract_version(branch)
        assert version is not None, f"Expected version extraction for '{branch}'"

        # Parse expected values from branch name
        # Format: release/vX.Y
        parts = branch.replace("release/v", "").split(".")
        expected_major = int(parts[0])
        expected_minor = int(parts[1])

        assert version.major == expected_major, (
            f"Major version mismatch for '{branch}': " f"expected {expected_major}, got {version.major}"
        )
        assert version.minor == expected_minor, (
            f"Minor version mismatch for '{branch}': " f"expected {expected_minor}, got {version.minor}"
        )

    @settings(max_examples=100)
    @given(branch=branch_with_leading_zero())
    def test_leading_zeros_are_rejected(self, branch: str) -> None:
        """Branches with leading zeros SHALL be rejected (SemVer 2.0.0).

        **Validates: Requirements 1.2**
        """
        # Skip if the branch accidentally matches valid pattern
        # (e.g., "release/v00.0" has leading zero but "release/v0.0" doesn't)
        if branch in ("release/v0.0", "release/v0.1", "release/v1.0"):
            assume(False)

        assert validate_branch(branch) is False, f"Expected branch with leading zero '{branch}' to be rejected"

    @settings(max_examples=100)
    @given(branch=branch_with_wrong_prefix())
    def test_wrong_prefix_is_rejected(self, branch: str) -> None:
        """Branches with wrong prefix SHALL be rejected.

        **Validates: Requirements 1.1, 1.2**
        """
        assert validate_branch(branch) is False, f"Expected branch with wrong prefix '{branch}' to be rejected"

    @settings(max_examples=100)
    @given(branch=branch_missing_v())
    def test_missing_v_prefix_is_rejected(self, branch: str) -> None:
        """Branches missing 'v' prefix SHALL be rejected.

        **Validates: Requirements 1.1, 1.2**
        """
        assert validate_branch(branch) is False, f"Expected branch missing 'v' prefix '{branch}' to be rejected"

    @settings(max_examples=100)
    @given(branch=branch_with_patch())
    def test_patch_version_in_branch_is_rejected(self, branch: str) -> None:
        """Branches with patch version SHALL be rejected.

        **Validates: Requirements 1.1, 1.2**
        """
        assert validate_branch(branch) is False, f"Expected branch with patch version '{branch}' to be rejected"

    @settings(max_examples=100)
    @given(text=random_string)
    def test_random_strings_handled_gracefully(self, text: str) -> None:
        """Random strings SHALL not crash the validator.

        **Validates: Requirements 1.2**
        """
        # Should not raise any exceptions
        result = validate_branch(text)
        # Result should be boolean
        assert isinstance(result, bool), f"Expected boolean result for '{text}', got {type(result)}"

    @settings(max_examples=100)
    @given(branch=valid_release_branch())
    def test_validation_and_extraction_consistency(self, branch: str) -> None:
        """If validate_branch returns True, extract_version SHALL return a value.

        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        is_valid = validate_branch(branch)
        version = extract_version(branch)

        if is_valid:
            assert version is not None, f"Valid branch '{branch}' should have extractable version"
        # Note: The inverse (invalid -> None) is tested implicitly
        # by the rejection tests above


class TestRCTagSequencing:
    """Property 2: RC Tag Sequencing.

    *For any* sequence of commits to a release branch before GA release,
    the RC tags SHALL be sequential (rc1, rc2, rc3...) with no gaps or duplicates.

    **Validates: Requirements 2.1, 3.1, 3.2, 3.3**
    """

    @settings(max_examples=100)
    @given(num_commits=st.integers(min_value=1, max_value=50))
    def test_rc_tags_are_sequential(self, num_commits: int) -> None:
        """RC tags SHALL be sequential with no gaps.

        Simulates a sequence of commits to a release branch before GA release
        and verifies that RC tags are created sequentially (rc1, rc2, rc3...).

        **Validates: Requirements 2.1, 3.1, 3.2, 3.3**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_rc_tag

        # Simulate a mock API that tracks created tags
        mock_api = MagicMock()
        created_tags: list[str] = []

        def list_tags_side_effect() -> list[MagicMock]:
            """Return mock tag objects for all created tags."""
            result = []
            for tag_name in created_tags:
                tag = MagicMock()
                tag.name = tag_name
                result.append(tag)
            return result

        mock_api.list_tags.side_effect = list_tags_side_effect

        # Simulate commits to release/v1.0 branch before GA
        major, minor = 1, 0

        for i in range(num_commits):
            # Get the next RC tag
            next_tag = get_next_rc_tag(mock_api, major, minor)

            # Verify the tag follows the expected pattern
            expected_rc_num = i + 1
            expected_tag = f"v{major}.{minor}.0-rc{expected_rc_num}"
            assert next_tag == expected_tag, f"Commit {i + 1}: Expected '{expected_tag}', got '{next_tag}'"

            # Simulate tag creation
            created_tags.append(next_tag)

        # Verify all RC tags are sequential with no gaps
        for i, tag in enumerate(created_tags):
            expected_rc_num = i + 1
            expected_tag = f"v{major}.{minor}.0-rc{expected_rc_num}"
            assert tag == expected_tag, f"Tag at index {i}: Expected '{expected_tag}', got '{tag}'"

    @settings(max_examples=100)
    @given(num_commits=st.integers(min_value=1, max_value=50))
    def test_rc_tags_have_no_duplicates(self, num_commits: int) -> None:
        """RC tags SHALL have no duplicates.

        **Validates: Requirements 3.2, 3.3**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_rc_tag

        mock_api = MagicMock()
        created_tags: list[str] = []

        def list_tags_side_effect() -> list[MagicMock]:
            result = []
            for tag_name in created_tags:
                tag = MagicMock()
                tag.name = tag_name
                result.append(tag)
            return result

        mock_api.list_tags.side_effect = list_tags_side_effect

        major, minor = 2, 5

        for _ in range(num_commits):
            next_tag = get_next_rc_tag(mock_api, major, minor)
            created_tags.append(next_tag)

        # Verify no duplicates
        assert len(created_tags) == len(set(created_tags)), f"Duplicate tags found: {created_tags}"

    @settings(max_examples=100)
    @given(
        major=valid_version_number,
        minor=valid_version_number,
        num_commits=st.integers(min_value=1, max_value=30),
    )
    def test_rc_sequencing_across_versions(self, major: int, minor: int, num_commits: int) -> None:
        """RC tags SHALL be sequential for any valid major.minor version.

        **Validates: Requirements 2.1, 3.1, 3.2, 3.3**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_rc_tag

        mock_api = MagicMock()
        created_tags: list[str] = []

        def list_tags_side_effect() -> list[MagicMock]:
            result = []
            for tag_name in created_tags:
                tag = MagicMock()
                tag.name = tag_name
                result.append(tag)
            return result

        mock_api.list_tags.side_effect = list_tags_side_effect

        for i in range(num_commits):
            next_tag = get_next_rc_tag(mock_api, major, minor)
            expected_tag = f"v{major}.{minor}.0-rc{i + 1}"
            assert next_tag == expected_tag, (
                f"Version v{major}.{minor}, commit {i + 1}: " f"Expected '{expected_tag}', got '{next_tag}'"
            )
            created_tags.append(next_tag)

    @settings(max_examples=100)
    @given(starting_rc=st.integers(min_value=1, max_value=100))
    def test_increment_rc_always_increases(self, starting_rc: int) -> None:
        """increment_rc SHALL always return a value greater than input.

        **Validates: Requirements 3.2**
        """
        from src.tags import increment_rc

        result = increment_rc(starting_rc)
        assert result == starting_rc + 1, f"Expected {starting_rc + 1}, got {result}"
        assert result > starting_rc, f"Result {result} should be greater than input {starting_rc}"

    @settings(max_examples=100)
    @given(num_commits=st.integers(min_value=1, max_value=50))
    def test_first_rc_is_always_rc1(self, num_commits: int) -> None:
        """First RC tag SHALL always be rc1 when no RCs exist.

        **Validates: Requirements 2.1**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_rc_tag

        mock_api = MagicMock()
        # Empty tag list - no existing tags
        mock_api.list_tags.return_value = []

        # For any major.minor, first RC should be rc1
        for major in range(min(num_commits, 10)):
            for minor in range(min(num_commits, 10)):
                if major + minor >= num_commits:
                    break
                first_tag = get_next_rc_tag(mock_api, major, minor)
                expected = f"v{major}.{minor}.0-rc1"
                assert first_tag == expected, (
                    f"First RC for v{major}.{minor} should be '{expected}', " f"got '{first_tag}'"
                )


class TestPatchTagSequencing:
    """Property 3: Patch Tag Sequencing.

    *For any* sequence of commits to a release branch after GA release,
    the patch tags SHALL be sequential (vX.Y.1, vX.Y.2...) with no gaps or duplicates.

    **Validates: Requirements 4.1, 4.2, 4.3**
    """

    @settings(max_examples=100)
    @given(num_commits=st.integers(min_value=1, max_value=50))
    def test_patch_tags_are_sequential(self, num_commits: int) -> None:
        """Patch tags SHALL be sequential with no gaps.

        Simulates a sequence of commits to a release branch after GA release
        and verifies that patch tags are created sequentially (vX.Y.1, vX.Y.2...).

        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_patch_tag

        # Simulate a mock API that tracks created tags
        mock_api = MagicMock()
        created_tags: list[str] = []

        # Start with GA release (v1.0.0) already existing
        major, minor = 1, 0
        ga_tag = f"v{major}.{minor}.0"
        created_tags.append(ga_tag)

        def list_tags_side_effect() -> list[MagicMock]:
            """Return mock tag objects for all created tags."""
            result = []
            for tag_name in created_tags:
                tag = MagicMock()
                tag.name = tag_name
                result.append(tag)
            return result

        mock_api.list_tags.side_effect = list_tags_side_effect

        # Simulate commits to release/v1.0 branch after GA
        for i in range(num_commits):
            # Get the next patch tag
            next_tag = get_next_patch_tag(mock_api, major, minor)

            # Verify the tag follows the expected pattern
            expected_patch_num = i + 1
            expected_tag = f"v{major}.{minor}.{expected_patch_num}"
            assert next_tag == expected_tag, f"Commit {i + 1}: Expected '{expected_tag}', got '{next_tag}'"

            # Simulate tag creation
            created_tags.append(next_tag)

        # Verify all patch tags are sequential with no gaps (excluding GA)
        patch_tags = [t for t in created_tags if t != ga_tag]
        for i, tag in enumerate(patch_tags):
            expected_patch_num = i + 1
            expected_tag = f"v{major}.{minor}.{expected_patch_num}"
            assert tag == expected_tag, f"Tag at index {i}: Expected '{expected_tag}', got '{tag}'"

    @settings(max_examples=100)
    @given(num_commits=st.integers(min_value=1, max_value=50))
    def test_patch_tags_have_no_duplicates(self, num_commits: int) -> None:
        """Patch tags SHALL have no duplicates.

        **Validates: Requirements 4.2, 4.3**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_patch_tag

        mock_api = MagicMock()
        created_tags: list[str] = []

        # Start with GA release
        major, minor = 2, 5
        ga_tag = f"v{major}.{minor}.0"
        created_tags.append(ga_tag)

        def list_tags_side_effect() -> list[MagicMock]:
            result = []
            for tag_name in created_tags:
                tag = MagicMock()
                tag.name = tag_name
                result.append(tag)
            return result

        mock_api.list_tags.side_effect = list_tags_side_effect

        for _ in range(num_commits):
            next_tag = get_next_patch_tag(mock_api, major, minor)
            created_tags.append(next_tag)

        # Verify no duplicates (excluding GA which is added once)
        assert len(created_tags) == len(set(created_tags)), f"Duplicate tags found: {created_tags}"

    @settings(max_examples=100)
    @given(
        major=valid_version_number,
        minor=valid_version_number,
        num_commits=st.integers(min_value=1, max_value=30),
    )
    def test_patch_sequencing_across_versions(self, major: int, minor: int, num_commits: int) -> None:
        """Patch tags SHALL be sequential for any valid major.minor version.

        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_patch_tag

        mock_api = MagicMock()
        created_tags: list[str] = []

        # Start with GA release
        ga_tag = f"v{major}.{minor}.0"
        created_tags.append(ga_tag)

        def list_tags_side_effect() -> list[MagicMock]:
            result = []
            for tag_name in created_tags:
                tag = MagicMock()
                tag.name = tag_name
                result.append(tag)
            return result

        mock_api.list_tags.side_effect = list_tags_side_effect

        for i in range(num_commits):
            next_tag = get_next_patch_tag(mock_api, major, minor)
            expected_tag = f"v{major}.{minor}.{i + 1}"
            assert next_tag == expected_tag, (
                f"Version v{major}.{minor}, commit {i + 1}: " f"Expected '{expected_tag}', got '{next_tag}'"
            )
            created_tags.append(next_tag)

    @settings(max_examples=100)
    @given(starting_patch=st.integers(min_value=0, max_value=100))
    def test_increment_patch_always_increases(self, starting_patch: int) -> None:
        """increment_patch SHALL always return a value greater than input.

        **Validates: Requirements 4.2**
        """
        from src.tags import increment_patch

        result = increment_patch(starting_patch)
        assert result == starting_patch + 1, f"Expected {starting_patch + 1}, got {result}"
        assert result > starting_patch, f"Result {result} should be greater than input {starting_patch}"

    @settings(max_examples=100)
    @given(num_commits=st.integers(min_value=1, max_value=50))
    def test_first_patch_is_always_v1(self, num_commits: int) -> None:
        """First patch tag SHALL always be vX.Y.1 when only GA exists.

        **Validates: Requirements 4.1**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_patch_tag

        # For any major.minor, first patch after GA should be vX.Y.1
        for major in range(min(num_commits, 10)):
            for minor in range(min(num_commits, 10)):
                if major + minor >= num_commits:
                    break

                mock_api = MagicMock()
                # Only GA tag exists
                ga_tag = MagicMock()
                ga_tag.name = f"v{major}.{minor}.0"
                mock_api.list_tags.return_value = [ga_tag]

                first_patch = get_next_patch_tag(mock_api, major, minor)
                expected = f"v{major}.{minor}.1"
                assert first_patch == expected, (
                    f"First patch for v{major}.{minor} should be '{expected}', " f"got '{first_patch}'"
                )

    @settings(max_examples=100)
    @given(
        major=valid_version_number,
        minor=valid_version_number,
        existing_patches=st.integers(min_value=1, max_value=20),
    )
    def test_patch_continues_from_existing(self, major: int, minor: int, existing_patches: int) -> None:
        """Patch tags SHALL continue from the highest existing patch.

        **Validates: Requirements 4.2, 4.3**
        """
        from unittest.mock import MagicMock

        from src.tags import get_next_patch_tag

        mock_api = MagicMock()

        # Create existing tags: GA + patches up to existing_patches
        existing_tags = []
        for patch in range(existing_patches + 1):  # 0 to existing_patches
            tag = MagicMock()
            tag.name = f"v{major}.{minor}.{patch}"
            existing_tags.append(tag)

        mock_api.list_tags.return_value = existing_tags

        next_tag = get_next_patch_tag(mock_api, major, minor)
        expected = f"v{major}.{minor}.{existing_patches + 1}"
        assert next_tag == expected, (
            f"After v{major}.{minor}.{existing_patches}, " f"next should be '{expected}', got '{next_tag}'"
        )


# Strategy for generating release version tuples (major, minor, patch)
@st.composite
def release_version(draw: st.DrawFn) -> tuple[int, int, int]:
    """Generate a valid release version tuple (major, minor, patch)."""
    major = draw(st.integers(min_value=0, max_value=10))
    minor = draw(st.integers(min_value=0, max_value=10))
    patch = draw(st.integers(min_value=0, max_value=20))
    return (major, minor, patch)


# Strategy for generating release histories across multiple branches
@st.composite
def release_history(draw: st.DrawFn) -> list[tuple[int, int, int]]:
    """Generate a random release history with multiple versions.

    Returns a list of (major, minor, patch) tuples representing releases.
    """
    num_releases = draw(st.integers(min_value=1, max_value=20))
    releases = []
    for _ in range(num_releases):
        version = draw(release_version())
        releases.append(version)
    return releases


class TestAliasTagCorrectness:
    """Property 4: Alias Tag Correctness.

    *For any* non-RC release, the major alias tag SHALL point to the highest
    vX.*.* release, and the minor alias tag SHALL point to the highest vX.Y.* release.

    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 7.3**
    """

    @settings(max_examples=100)
    @given(releases=release_history())
    def test_major_alias_points_to_highest_release(self, releases: list[tuple[int, int, int]]) -> None:
        """Major alias SHALL point to highest vX.*.* release.

        **Validates: Requirements 6.1, 7.3**
        """
        from unittest.mock import MagicMock

        from src.aliases import find_highest_major_version

        mock_api = MagicMock()

        # Create mock tags from releases
        tags = []
        for major, minor, patch in releases:
            tag = MagicMock()
            tag.name = f"v{major}.{minor}.{patch}"
            tags.append(tag)
        mock_api.list_tags.return_value = tags

        # For each unique major version, verify the highest is found
        majors = {r[0] for r in releases}
        for major in majors:
            highest = find_highest_major_version(mock_api, major)

            # Find expected highest manually
            matching = [r for r in releases if r[0] == major]
            expected = max(matching, key=lambda r: (r[1], r[2]))

            assert highest == expected, f"For major {major}, expected highest {expected}, got {highest}"

    @settings(max_examples=100)
    @given(releases=release_history())
    def test_minor_alias_points_to_highest_patch(self, releases: list[tuple[int, int, int]]) -> None:
        """Minor alias SHALL point to highest vX.Y.* release.

        **Validates: Requirements 6.2, 7.3**
        """
        from unittest.mock import MagicMock

        from src.aliases import find_highest_minor_version

        mock_api = MagicMock()

        # Create mock tags from releases
        tags = []
        for major, minor, patch in releases:
            tag = MagicMock()
            tag.name = f"v{major}.{minor}.{patch}"
            tags.append(tag)
        mock_api.list_tags.return_value = tags

        # For each unique (major, minor) pair, verify the highest patch is found
        minor_series = {(r[0], r[1]) for r in releases}
        for major, minor in minor_series:
            highest = find_highest_minor_version(mock_api, major, minor)

            # Find expected highest manually
            matching = [r for r in releases if r[0] == major and r[1] == minor]
            expected = max(matching, key=lambda r: r[2])

            assert highest == expected, f"For v{major}.{minor}, expected highest {expected}, got {highest}"

    @settings(max_examples=100)
    @given(releases=release_history())
    def test_rc_releases_do_not_update_aliases(self, releases: list[tuple[int, int, int]]) -> None:
        """RC releases SHALL NOT update alias tags.

        **Validates: Requirements 6.4**
        """
        from unittest.mock import MagicMock

        from src.aliases import update_alias_tags

        mock_api = MagicMock()
        mock_api.list_tags.return_value = []

        # Test with RC tags - should not update aliases
        for major, minor, _ in releases[:5]:  # Test first 5 to keep it fast
            rc_tag = f"v{major}.{minor}.0-rc1"
            result = update_alias_tags(mock_api, rc_tag, "abc123")

            assert result["major"] is False, f"RC tag {rc_tag} should not update major alias"
            assert result["minor"] is False, f"RC tag {rc_tag} should not update minor alias"

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=5),
        minor=st.integers(min_value=0, max_value=5),
        patches=st.lists(
            st.integers(min_value=0, max_value=10),
            min_size=1,
            max_size=10,
            unique=True,
        ),
    )
    def test_alias_updates_for_highest_in_series(self, major: int, minor: int, patches: list[int]) -> None:
        """Alias tags SHALL be updated when release is highest in series.

        **Validates: Requirements 6.1, 6.2, 6.3**
        """
        from unittest.mock import MagicMock

        from src.aliases import should_update_minor_alias

        mock_api = MagicMock()

        # Create tags for all patches in the series
        tags = []
        for patch in patches:
            tag = MagicMock()
            tag.name = f"v{major}.{minor}.{patch}"
            tags.append(tag)
        mock_api.list_tags.return_value = tags

        highest_patch = max(patches)

        # The highest patch should update minor alias
        assert should_update_minor_alias(mock_api, major, minor, highest_patch) is True

        # Lower patches should not update minor alias
        for patch in patches:
            if patch < highest_patch:
                assert should_update_minor_alias(mock_api, major, minor, patch) is False

    @settings(max_examples=100)
    @given(
        releases=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=3),  # major
                st.integers(min_value=0, max_value=5),  # minor
                st.integers(min_value=0, max_value=10),  # patch
            ),
            min_size=2,
            max_size=15,
        )
    )
    def test_multi_branch_alias_correctness(self, releases: list[tuple[int, int, int]]) -> None:
        """Alias tags SHALL point to highest version across all branches.

        **Validates: Requirements 7.3**
        """
        from unittest.mock import MagicMock

        from src.aliases import find_highest_major_version

        mock_api = MagicMock()

        # Create mock tags from releases
        tags = []
        for major, minor, patch in releases:
            tag = MagicMock()
            tag.name = f"v{major}.{minor}.{patch}"
            tags.append(tag)
        mock_api.list_tags.return_value = tags

        # For each major version, verify the highest across all minors is found
        majors = {r[0] for r in releases}
        for major in majors:
            highest = find_highest_major_version(mock_api, major)

            # Find expected highest across all minor versions
            matching = [r for r in releases if r[0] == major]
            expected = max(matching, key=lambda r: (r[1], r[2]))

            assert highest == expected, (
                f"For major {major} across branches, " f"expected highest {expected}, got {highest}"
            )

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=5),
        num_minors=st.integers(min_value=1, max_value=5),
        patches_per_minor=st.integers(min_value=1, max_value=5),
    )
    def test_independent_minor_series_tracking(self, major: int, num_minors: int, patches_per_minor: int) -> None:
        """Each minor series SHALL be tracked independently.

        **Validates: Requirements 7.2**
        """
        from unittest.mock import MagicMock

        from src.aliases import find_highest_minor_version

        mock_api = MagicMock()

        # Create tags for multiple minor series
        tags = []
        for minor in range(num_minors):
            for patch in range(patches_per_minor):
                tag = MagicMock()
                tag.name = f"v{major}.{minor}.{patch}"
                tags.append(tag)
        mock_api.list_tags.return_value = tags

        # Verify each minor series is tracked independently
        for minor in range(num_minors):
            highest = find_highest_minor_version(mock_api, major, minor)
            expected_patch = patches_per_minor - 1
            expected = (major, minor, expected_patch)

            assert highest == expected, f"For v{major}.{minor} series, " f"expected highest {expected}, got {highest}"


# Strategy for generating valid SemVer tag names
@st.composite
def valid_semver_tag(draw: st.DrawFn) -> str:
    """Generate valid SemVer tag names (RC, GA, or patch)."""
    major = draw(st.integers(min_value=0, max_value=10))
    minor = draw(st.integers(min_value=0, max_value=10))
    tag_type = draw(st.sampled_from(["rc", "ga", "patch"]))

    if tag_type == "rc":
        rc_num = draw(st.integers(min_value=1, max_value=20))
        return f"v{major}.{minor}.0-rc{rc_num}"
    elif tag_type == "ga":
        return f"v{major}.{minor}.0"
    else:  # patch
        patch_num = draw(st.integers(min_value=1, max_value=20))
        return f"v{major}.{minor}.{patch_num}"


# Strategy for generating commit SHA-like strings
@st.composite
def commit_sha(draw: st.DrawFn) -> str:
    """Generate a commit SHA-like string (40 hex characters)."""
    chars = "0123456789abcdef"
    sha = "".join(draw(st.sampled_from(chars)) for _ in range(40))
    return sha


# Strategy for generating a commit history for a branch
@st.composite
def branch_commit_history(draw: st.DrawFn) -> list[str]:
    """Generate a list of commit SHAs representing a branch history."""
    num_commits = draw(st.integers(min_value=1, max_value=20))
    commits = [draw(commit_sha()) for _ in range(num_commits)]
    return commits


class TestManualTagValidation:
    """Property 5: Manual Tag Validation.

    *For any* manually pushed tag, the action SHALL verify it points to a commit
    reachable from the corresponding release branch.

    **Validates: Requirements 5.1, 5.2, 5.3**
    """

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=10),
        minor=st.integers(min_value=0, max_value=10),
        branch_commits=branch_commit_history(),
    )
    def test_tag_on_branch_is_accepted(self, major: int, minor: int, branch_commits: list[str]) -> None:
        """Tags pointing to release branch commits SHALL be accepted.

        **Validates: Requirements 5.1**
        """
        from unittest.mock import MagicMock

        from src.main import _validate_tag_on_branch

        mock_api = MagicMock()

        # Create mock commit objects for the branch
        mock_commits = []
        for sha in branch_commits:
            commit = MagicMock()
            commit.sha = sha
            mock_commits.append(commit)
        mock_api.get_branch_commits.return_value = mock_commits

        branch_name = f"release/v{major}.{minor}"

        # Pick a commit from the branch - should be accepted
        for commit_sha in branch_commits:
            result = _validate_tag_on_branch(mock_api, commit_sha, branch_name)
            assert result is True, (
                f"Tag pointing to commit {commit_sha[:7]} on branch {branch_name} " f"should be accepted"
            )

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=10),
        minor=st.integers(min_value=0, max_value=10),
        branch_commits=branch_commit_history(),
        other_commit=commit_sha(),
    )
    def test_tag_not_on_branch_is_rejected(
        self, major: int, minor: int, branch_commits: list[str], other_commit: str
    ) -> None:
        """Tags pointing to commits NOT on release branch SHALL be rejected.

        **Validates: Requirements 5.1, 5.2**
        """
        from unittest.mock import MagicMock

        from hypothesis import assume

        from src.main import _validate_tag_on_branch

        # Ensure the other_commit is not in branch_commits
        assume(other_commit not in branch_commits)

        mock_api = MagicMock()

        # Create mock commit objects for the branch
        mock_commits = []
        for sha in branch_commits:
            commit = MagicMock()
            commit.sha = sha
            mock_commits.append(commit)
        mock_api.get_branch_commits.return_value = mock_commits

        branch_name = f"release/v{major}.{minor}"

        # A commit not on the branch should be rejected
        result = _validate_tag_on_branch(mock_api, other_commit, branch_name)
        assert result is False, (
            f"Tag pointing to commit {other_commit[:7]} NOT on branch {branch_name} " f"should be rejected"
        )

    @settings(max_examples=100)
    @given(
        tag_name=valid_semver_tag(),
        branch_commits=branch_commit_history(),
    )
    def test_tag_version_matches_branch(self, tag_name: str, branch_commits: list[str]) -> None:
        """Tag version SHALL correspond to the correct release branch.

        **Validates: Requirements 5.1, 5.3**
        """
        from unittest.mock import MagicMock

        from src.main import _parse_tag_version, _validate_tag_on_branch

        # Parse the tag to get major.minor
        version = _parse_tag_version(tag_name)
        assert version is not None, f"Tag {tag_name} should be parseable"

        major, minor = version
        expected_branch = f"release/v{major}.{minor}"

        mock_api = MagicMock()

        # Create mock commit objects for the branch
        mock_commits = []
        for sha in branch_commits:
            commit = MagicMock()
            commit.sha = sha
            mock_commits.append(commit)
        mock_api.get_branch_commits.return_value = mock_commits

        # A commit on the correct branch should be accepted
        commit_sha = branch_commits[0]
        result = _validate_tag_on_branch(mock_api, commit_sha, expected_branch)
        assert result is True, f"Tag {tag_name} pointing to commit on {expected_branch} should be accepted"

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=10),
        minor=st.integers(min_value=0, max_value=10),
    )
    def test_api_error_returns_false(self, major: int, minor: int) -> None:
        """API errors during validation SHALL result in rejection.

        **Validates: Requirements 5.2**
        """
        from unittest.mock import MagicMock

        from src.main import _validate_tag_on_branch

        mock_api = MagicMock()
        mock_api.get_branch_commits.side_effect = Exception("API error")

        branch_name = f"release/v{major}.{minor}"
        commit_sha = "a" * 40  # Valid SHA format

        result = _validate_tag_on_branch(mock_api, commit_sha, branch_name)
        assert result is False, "API errors should result in rejection"

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=10),
        minor=st.integers(min_value=0, max_value=10),
        branch_commits=branch_commit_history(),
        tag_type=st.sampled_from(["rc", "ga", "patch"]),
    )
    def test_all_tag_types_validated_consistently(
        self, major: int, minor: int, branch_commits: list[str], tag_type: str
    ) -> None:
        """All tag types (RC, GA, patch) SHALL be validated consistently.

        **Validates: Requirements 5.1, 5.3**
        """
        from unittest.mock import MagicMock

        from src.main import _validate_tag_on_branch
        from src.tags import is_ga_tag, is_patch_tag, is_rc_tag

        mock_api = MagicMock()

        # Create mock commit objects for the branch
        mock_commits = []
        for sha in branch_commits:
            commit = MagicMock()
            commit.sha = sha
            mock_commits.append(commit)
        mock_api.get_branch_commits.return_value = mock_commits

        branch_name = f"release/v{major}.{minor}"

        # Generate tag based on type
        if tag_type == "rc":
            tag_name = f"v{major}.{minor}.0-rc1"
            assert is_rc_tag(tag_name)
        elif tag_type == "ga":
            tag_name = f"v{major}.{minor}.0"
            assert is_ga_tag(tag_name)
        else:
            tag_name = f"v{major}.{minor}.1"
            assert is_patch_tag(tag_name)

        # Validation should work the same for all tag types
        commit_sha = branch_commits[0]
        result = _validate_tag_on_branch(mock_api, commit_sha, branch_name)
        assert result is True, f"{tag_type.upper()} tag {tag_name} pointing to commit on branch " f"should be accepted"

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=10),
        minor=st.integers(min_value=0, max_value=10),
    )
    def test_empty_branch_rejects_all_commits(self, major: int, minor: int) -> None:
        """Empty branch (no commits) SHALL reject all tags.

        **Validates: Requirements 5.2**
        """
        from unittest.mock import MagicMock

        from src.main import _validate_tag_on_branch

        mock_api = MagicMock()
        mock_api.get_branch_commits.return_value = []  # Empty branch

        branch_name = f"release/v{major}.{minor}"
        commit_sha = "a" * 40  # Any commit SHA

        result = _validate_tag_on_branch(mock_api, commit_sha, branch_name)
        assert result is False, "Empty branch should reject all commits"

    @settings(max_examples=100)
    @given(
        major=st.integers(min_value=0, max_value=10),
        minor=st.integers(min_value=0, max_value=10),
        wrong_major=st.integers(min_value=0, max_value=10),
        wrong_minor=st.integers(min_value=0, max_value=10),
        branch_commits=branch_commit_history(),
    )
    def test_tag_on_wrong_branch_is_rejected(
        self,
        major: int,
        minor: int,
        wrong_major: int,
        wrong_minor: int,
        branch_commits: list[str],
    ) -> None:
        """Tags validated against wrong branch SHALL be rejected.

        **Validates: Requirements 5.1, 5.2**
        """
        from unittest.mock import MagicMock

        from hypothesis import assume

        from src.main import _validate_tag_on_branch

        # Ensure we're checking against a different branch
        assume(major != wrong_major or minor != wrong_minor)

        mock_api = MagicMock()

        # The correct branch has commits
        correct_branch_commits = []
        for sha in branch_commits:
            commit = MagicMock()
            commit.sha = sha
            correct_branch_commits.append(commit)

        # The wrong branch has no commits (or different commits)
        mock_api.get_branch_commits.return_value = []

        wrong_branch = f"release/v{wrong_major}.{wrong_minor}"
        commit_sha = branch_commits[0]

        # Validating against wrong branch should fail
        result = _validate_tag_on_branch(mock_api, commit_sha, wrong_branch)
        assert result is False, (
            f"Commit from release/v{major}.{minor} validated against " f"{wrong_branch} should be rejected"
        )
