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
