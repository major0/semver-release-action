#!/bin/sh
# Extract version components from a SemVer tag
# Usage: extract-version.sh v1.2.3 or extract-version.sh v1.2.3-rc1

POSIXLY_CORRECT='no bashing shell'
set -eu

strip_v() { echo "${1#v}"; }
major() { echo "${1%%.*}"; }

minor() {
  set -- "${1#*.}"
  echo "${1%%.*}"
}

patch() {
  set -- "${1#*.}"
  set -- "${1#*.}"
  echo "${1%%-*}"
}

prerelease() {
  case "${1}" in
  (*-*) echo "${1#*-}" ;;
  (*)   echo '' ;;
  esac
}

is_ga() {
  case "${1}" in
  (*-*) echo 'false' ;;
  (*)   echo 'true' ;;
  esac
}

# Main
{
  VERSION="$(strip_v "${1}")"
  echo "version=${VERSION}"
  echo "major=$(major "${VERSION}")"
  echo "minor=$(minor "${VERSION}")"
  echo "patch=$(patch "${VERSION}")"
  echo "prerelease=$(prerelease "${VERSION}")"
  echo "is_ga=$(is_ga "${VERSION}")"
} >> "${GITHUB_OUTPUT}"
