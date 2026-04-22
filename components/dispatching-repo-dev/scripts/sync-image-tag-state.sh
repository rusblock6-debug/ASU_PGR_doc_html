#!/usr/bin/env bash

set -euo pipefail

SOURCE_ENV_FILE="${1:-}"
TARGET_STATE_FILE="${2:-}"
COMPOSE_FILE="${3:-docker-compose.bort.yaml}"

if [ -z "$SOURCE_ENV_FILE" ] || [ -z "$TARGET_STATE_FILE" ]; then
    echo "Использование: $0 SOURCE_ENV_FILE TARGET_STATE_FILE [COMPOSE_FILE]" >&2
    exit 1
fi

if [ ! -f "$SOURCE_ENV_FILE" ]; then
    echo "Ошибка: source env файл не найден: $SOURCE_ENV_FILE" >&2
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Ошибка: compose файл не найден: $COMPOSE_FILE" >&2
    exit 1
fi

mkdir -p "$(dirname "$TARGET_STATE_FILE")"

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

while IFS=$'\t' read -r image_repo image_tag image_var tag_var; do
    [ -n "$image_repo" ] || continue
    printf '%s=%s\n' "$image_var" "$image_repo" >> "$tmp_file"
    printf '%s=%s\n' "$tag_var" "$image_tag" >> "$tmp_file"
done < <(bash scripts/list-managed-image-refs.sh "$SOURCE_ENV_FILE" "$COMPOSE_FILE")

mv "$tmp_file" "$TARGET_STATE_FILE"
