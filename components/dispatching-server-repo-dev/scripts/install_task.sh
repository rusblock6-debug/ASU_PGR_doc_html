#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${1:-$PWD/.bin}"
OS_NAME="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH_NAME="$(uname -m)"

case "${ARCH_NAME}" in
  x86_64|amd64)
    ARCH_NAME="amd64"
    ;;
  aarch64|arm64)
    ARCH_NAME="arm64"
    ;;
  *)
    echo "Unsupported architecture: ${ARCH_NAME}" >&2
    exit 1
    ;;
esac

case "${OS_NAME}" in
  linux|darwin)
    ;;
  *)
    echo "Unsupported OS: ${OS_NAME}" >&2
    exit 1
    ;;
esac

mkdir -p "${INSTALL_DIR}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

ARCHIVE="${TMP_DIR}/task.tar.gz"
URL="https://github.com/go-task/task/releases/latest/download/task_${OS_NAME}_${ARCH_NAME}.tar.gz"

curl -fsSL "${URL}" -o "${ARCHIVE}"
tar -xzf "${ARCHIVE}" -C "${TMP_DIR}" task
install -m 0755 "${TMP_DIR}/task" "${INSTALL_DIR}/task"

echo "Installed task to ${INSTALL_DIR}/task"
