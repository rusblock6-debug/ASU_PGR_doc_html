#!/usr/bin/env bash

set -euo pipefail

ENV_FILE="${1:-.env}"
COMPOSE_FILE="${2:-docker-compose.bort.yaml}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Ошибка: env файл не найден: $ENV_FILE" >&2
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Ошибка: compose файл не найден: $COMPOSE_FILE" >&2
    exit 1
fi

set +u
set -a
. "$ENV_FILE"
set +a
set -u

resolve_default_value() {
    local raw_value="$1"

    if [[ "$raw_value" =~ ^\$\{([A-Z0-9_]+):-([^}]+)\}$ ]]; then
        local nested_var="${BASH_REMATCH[1]}"
        local nested_default="${BASH_REMATCH[2]}"
        printf '%s\n' "${!nested_var:-$nested_default}"
        return 0
    fi

    printf '%s\n' "$raw_value"
}

while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*image:[[:space:]]*\$\{([A-Z0-9_]+):-([^}]+)\}:\$\{([A-Z0-9_]+):-(.+)\}[[:space:]]*$ ]]; then
        image_var="${BASH_REMATCH[1]}"
        default_repo="${BASH_REMATCH[2]}"
        tag_var="${BASH_REMATCH[3]}"
        default_tag="$(resolve_default_value "${BASH_REMATCH[4]}")"

        image_repo="${!image_var:-$default_repo}"
        image_tag="${!tag_var:-$default_tag}"

        printf '%s\t%s\t%s\t%s\n' "$image_repo" "$image_tag" "$image_var" "$tag_var"
    fi
done < "$COMPOSE_FILE"
