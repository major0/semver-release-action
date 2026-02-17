# Semantic Versioning Release Action

[![CI](https://github.com/major0/semver-release-action/actions/workflows/ci.yml/badge.svg)](https://github.com/major0/semver-release-action/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/major0/semver-release-action)

A GitHub Action that automates semantic versioning and release management
following [Semantic Versioning 2.0.0](https://semver.org/).

## Overview

This action manages releases using a branch-based workflow:

```text
release/v1.2 branch created → v1.2.0-rc1
         ↓
    commit pushed → v1.2.0-rc2
         ↓
    commit pushed → v1.2.0-rc3
         ↓
  manual tag v1.2.0 (GA Release)
         ↓
    commit pushed → v1.2.1
         ↓
    commit pushed → v1.2.2
```

## Usage

```yaml
- uses: major0/semver-release-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `token` | GitHub token for API operations | No | `${{ github.token }}` |
| `debug` | Enable verbose debug logging | No | `false` |
| `dry-run` | Simulate actions without creating tags | No | `false` |
| `target-branch` | Target release branch for workflow_dispatch | No | `''` |
| `aliases` | Create version alias tags (vX, vX.Y) | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `tag` | The tag that was created or validated |
| `tag-type` | Type of tag: `rc`, `patch`, `ga`, or `skipped` |
| `major` | Major version number |
| `minor` | Minor version number |

## Branch Naming Convention

Release branches must follow the pattern `release/vX.Y` where X and Y are
non-negative integers without leading zeros (per SemVer 2.0.0).

Examples:

- ✅ `release/v1.0`
- ✅ `release/v2.15`
- ❌ `release/v01.0` (leading zero)
- ❌ `release/1.0` (missing `v` prefix)

### Branch Protection

The `release/` prefix enables GitHub branch protection rules using wildcards.
Configure branch protection for `release/*` to protect all release branches
with a single rule.

## Tag Types

| Pattern | Example | Description |
|---------|---------|-------------|
| `vX.Y.0-rcN` | `v1.2.0-rc3` | Release candidate |
| `vX.Y.0` | `v1.2.0` | GA (General Availability) release |
| `vX.Y.Z` | `v1.2.5` | Patch release |
| `vX` | `v2` | Major alias (movable, points to latest) |
| `vX.Y` | `v2.1` | Minor alias (movable, points to latest) |

## Workflow Events

The action responds to these GitHub events:

- **Branch creation**: Creates initial `vX.Y.0-rc1` tag
- **Commit push**: Creates next RC or patch tag
- **Tag push**: Validates manual tags and updates aliases
- **Workflow dispatch**: Manual trigger for testing

## Examples

See the [example/](example/) directory for complete workflow examples:

- [basic-workflow.yml](example/basic-workflow.yml) - Simple release branch workflow
- [multi-branch.yml](example/multi-branch.yml) - Multiple release branches
- [manual-ga-release.yml](example/manual-ga-release.yml) - Manual GA transition
- [workflow-dispatch.yml](example/workflow-dispatch.yml) - Manual testing with dry-run

## License

[MIT](LICENSE)
