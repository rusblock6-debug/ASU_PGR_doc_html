#!/usr/bin/env bash

set -euo pipefail

TARGET_ENV_FILE="${1:-}"
SOURCE_ENV_FILE="${2:-}"

if [ -z "$TARGET_ENV_FILE" ] || [ -z "$SOURCE_ENV_FILE" ]; then
    echo "Использование: $0 TARGET_ENV_FILE SOURCE_ENV_FILE" >&2
    exit 1
fi

if [ ! -f "$SOURCE_ENV_FILE" ]; then
    echo "Ошибка: source env файл не найден: $SOURCE_ENV_FILE" >&2
    exit 1
fi

mkdir -p "$(dirname "$TARGET_ENV_FILE")"
touch "$TARGET_ENV_FILE"

escape_sed_replacement() {
    printf '%s' "$1" | sed 's/[&|]/\\&/g'
}

update_or_add_var() {
    local var_name="$1"
    local var_value="$2"
    local file="$3"
    local escaped_value

    escaped_value="$(escape_sed_replacement "$var_value")"

    if grep -q "^${var_name}=" "$file" 2>/dev/null; then
        sed -i "s|^${var_name}=.*|${var_name}=${escaped_value}|" "$file"
    else
        printf '%s=%s\n' "$var_name" "$var_value" >> "$file"
    fi
}

while IFS= read -r raw_line || [ -n "${raw_line:-}" ]; do
    line="${raw_line%$'\r'}"
    [ -n "$line" ] || continue
    case "$line" in
        \#*)
            continue
            ;;
    esac

    if [[ "$line" != *=* ]]; then
        continue
    fi

    var_name="${line%%=*}"
    var_value="${line#*=}"
    update_or_add_var "$var_name" "$var_value" "$TARGET_ENV_FILE"
done < "$SOURCE_ENV_FILE"
