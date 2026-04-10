#!/usr/bin/env bash

set -euo pipefail

ENV_FILE="${1:-}"
DEFAULT_TAG="${2:-}"
COMPOSE_FILE="${3:-docker-compose.server.yaml}"

if [ -z "$ENV_FILE" ] || [ -z "$DEFAULT_TAG" ]; then
    echo "Использование: $0 ENV_FILE DEFAULT_TAG [COMPOSE_FILE]" >&2
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Ошибка: compose файл не найден: $COMPOSE_FILE" >&2
    exit 1
fi

touch "$ENV_FILE"

ensure_var() {
    local var_name="$1"
    local var_value="$2"
    local file="$3"

    if grep -q "^${var_name}=" "$file" 2>/dev/null; then
        return 0
    fi

    printf '%s=%s\n' "$var_name" "$var_value" >> "$file"
    echo "  Добавлено значение по умолчанию: ${var_name}=${var_value}"
}

echo "===> Заполняем отсутствующие image tags значением ${DEFAULT_TAG}"

while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*image:[[:space:]]*\$\{([A-Z0-9_]+):-([^}]+)\}:\$\{([A-Z0-9_]+):-(.+)\}[[:space:]]*$ ]]; then
        tag_var="${BASH_REMATCH[3]}"
        ensure_var "$tag_var" "$DEFAULT_TAG" "$ENV_FILE"
    fi
done < "$COMPOSE_FILE"
