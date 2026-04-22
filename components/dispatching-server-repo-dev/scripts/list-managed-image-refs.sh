#!/usr/bin/env bash

set -euo pipefail

ENV_FILE="${1:-.env_server_dev}"
COMPOSE_FILE="${2:-docker-compose.server.yaml}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Ошибка: env файл не найден: $ENV_FILE" >&2
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Ошибка: compose файл не найден: $COMPOSE_FILE" >&2
    exit 1
fi

declare -A env_values=()
declare -A seen_refs=()

trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s\n' "$value"
}

strip_wrapping_quotes() {
    local value="$1"

    if [[ "$value" =~ ^\"(.*)\"$ ]]; then
        printf '%s\n' "${BASH_REMATCH[1]}"
        return 0
    fi

    if [[ "$value" =~ ^\'(.*)\'$ ]]; then
        printf '%s\n' "${BASH_REMATCH[1]}"
        return 0
    fi

    printf '%s\n' "$value"
}

load_env_file() {
    local line=""
    local key=""
    local value=""

    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%$'\r'}"

        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi

        if [[ "$line" =~ ^[[:space:]]*([A-Z0-9_]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        elif [[ "$line" =~ ^[[:space:]]*([A-Z0-9_]+):[[:space:]]*(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            continue
        fi

        value="$(trim "$value")"
        value="$(strip_wrapping_quotes "$value")"
        env_values["$key"]="$value"
    done < "$ENV_FILE"
}

lookup_var() {
    local var_name="$1"

    if [[ -n "${env_values[$var_name]+x}" ]]; then
        printf '%s\n' "${env_values[$var_name]}"
        return 0
    fi

    printf '%s\n' "${!var_name-}"
}

resolve_default_value() {
    local raw_value="$1"

    if [[ "$raw_value" =~ ^\$\{([A-Z0-9_]+):-([^}]+)\}$ ]]; then
        local nested_var="${BASH_REMATCH[1]}"
        local nested_default="${BASH_REMATCH[2]}"
        local nested_value=""
        nested_value="$(lookup_var "$nested_var")"
        printf '%s\n' "${nested_value:-$nested_default}"
        return 0
    fi

    printf '%s\n' "$raw_value"
}

load_env_file

while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*image:[[:space:]]*\$\{([A-Z0-9_]+):-([^}]+)\}:\$\{([A-Z0-9_]+):-(.+)\}[[:space:]]*$ ]]; then
        image_var="${BASH_REMATCH[1]}"
        default_repo="${BASH_REMATCH[2]}"
        tag_var="${BASH_REMATCH[3]}"
        default_tag="$(resolve_default_value "${BASH_REMATCH[4]}")"

        image_repo="$(lookup_var "$image_var")"
        image_tag="$(lookup_var "$tag_var")"
        image_repo="${image_repo:-$default_repo}"
        image_tag="${image_tag:-$default_tag}"
        ref_key="${image_var}:${tag_var}"

        if [[ -n "${seen_refs[$ref_key]+x}" ]]; then
            continue
        fi
        seen_refs["$ref_key"]=1

        printf '%s\t%s\t%s\t%s\n' "$image_repo" "$image_tag" "$image_var" "$tag_var"
    fi
done < "$COMPOSE_FILE"
