#!/bin/sh
# Generate Docker image tags for a version
# Usage: docker-tags.sh v1.2.3

POSIXLY_CORRECT='no bashing shell'
set -eu

major() {
  set -- "${1#v}"
  echo "v${1%%.*}"
}

minor() {
  set -- "${1#v}"
  set -- "${1%%.*}" "${1#*.}"
  echo "v${1}.${2%%.*}"
}

is_rc() {
  case "${1}" in
  (*-rc*) return 0 ;;
  (*)     return 1 ;;
  esac
}

# Main
VERSION="${1}"
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_NAME="${IMAGE_NAME:-${GITHUB_REPOSITORY}}"

# Always include exact version tag
TAGS="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

# Add alias tags for GA releases only
if ! is_rc "${VERSION}"; then
  TAGS="${TAGS},${REGISTRY}/${IMAGE_NAME}:$(minor "${VERSION}")"
  TAGS="${TAGS},${REGISTRY}/${IMAGE_NAME}:$(major "${VERSION}")"
  TAGS="${TAGS},${REGISTRY}/${IMAGE_NAME}:latest"
fi

echo "tags=${TAGS}" >> "${GITHUB_OUTPUT}"
