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
| `release-prefix` | Prefix for release branch names | No | `release/v` |
| `tag-prefix` | Prefix for version tags and aliases | No | `v` |

### Configurable Prefixes

The `release-prefix` and `tag-prefix` inputs allow customizing branch and tag
naming conventions. This is useful for mono-repos or teams with different
naming standards.

**Default behavior (backward compatible):**

```yaml
- uses: major0/semver-release-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    # release-prefix: 'release/v'  # default
    # tag-prefix: 'v'              # default
```

- Branch: `release/v1.2` → Tags: `v1.2.0-rc1`, `v1.2.0`, `v1.2.1`
- Aliases: `v1`, `v1.2`

**Short prefix example:**

```yaml
- uses: major0/semver-release-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    release-prefix: 'v'
    tag-prefix: 'v'
```

- Branch: `v1.2` → Tags: `v1.2.0-rc1`, `v1.2.0`
- Aliases: `v1` only (minor alias `v1.2` skipped to avoid conflict with branch name)

**Custom prefix example:**

```yaml
- uses: major0/semver-release-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    release-prefix: 'pkg-v'
    tag-prefix: 'pkg-v'
```

- Branch: `pkg-v1.2` → Tags: `pkg-v1.2.0-rc1`, `pkg-v1.2.0`
- Aliases: `pkg-v1` only (minor alias skipped when prefixes match)

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

## Mono-Repo Usage

For mono-repos with multiple packages, use custom prefixes to version each
package independently:

```yaml
# Package A workflow
- uses: major0/semver-release-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    release-prefix: 'pkg-a/v'
    tag-prefix: 'pkg-a-v'
    aliases: true
```

```yaml
# Package B workflow
- uses: major0/semver-release-action@v1
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    release-prefix: 'pkg-b/v'
    tag-prefix: 'pkg-b-v'
    aliases: true
```

This creates independent version streams:

- `pkg-a/v1.0` branch → `pkg-a-v1.0.0`, `pkg-a-v1.0.1`,
  aliases `pkg-a-v1`, `pkg-a-v1.0`
- `pkg-b/v2.3` branch → `pkg-b-v2.3.0`, `pkg-b-v2.3.1`,
  aliases `pkg-b-v2`, `pkg-b-v2.3`

**Alias skip behavior:** When `release-prefix` equals `tag-prefix`, the minor
alias (`{tag-prefix}X.Y`) is skipped to avoid conflicts with the branch name.
For example, with `release-prefix: 'v'` and `tag-prefix: 'v'`, the branch
`v1.2` would conflict with a `v1.2` alias tag, so only the major alias `v1`
is created.

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

## Workflow Triggers for Custom Prefixes

When using custom prefixes, update your workflow triggers to match:

**Default prefix (`release/v`):**

```yaml
on:
  push:
    branches:
      - 'release/v[0-9]+.[0-9]+'
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+*'
  create:
    branches:
      - 'release/v[0-9]+.[0-9]+'
```

**Short prefix (`v`):**

```yaml
on:
  push:
    branches:
      - 'v[0-9]+.[0-9]+'
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+*'
  create:
    branches:
      - 'v[0-9]+.[0-9]+'
```

**Custom prefix (`pkg-v`):**

```yaml
on:
  push:
    branches:
      - 'pkg-v[0-9]+.[0-9]+'
    tags:
      - 'pkg-v[0-9]+.[0-9]+.[0-9]+*'
  create:
    branches:
      - 'pkg-v[0-9]+.[0-9]+'
```

## Examples

See the [example/](example/) directory for complete workflow examples:

- [basic-workflow.yml](example/basic-workflow.yml) - Simple release branch workflow
- [multi-branch.yml](example/multi-branch.yml) - Multiple release branches
- [manual-ga-release.yml](example/manual-ga-release.yml) - Manual GA transition
- [workflow-dispatch.yml](example/workflow-dispatch.yml) - Manual testing with dry-run

## License

[MIT](LICENSE)
