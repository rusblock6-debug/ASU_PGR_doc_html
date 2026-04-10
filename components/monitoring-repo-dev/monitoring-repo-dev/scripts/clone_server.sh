#!/usr/bin/env bash
set -eu
if (set -o 2>/dev/null | grep -q '^pipefail'); then
  set -o pipefail
fi

BRANCH="${DEPLOY_BRANCH:-dev}"
echo "Клонирование репозиториев для серверной части (Dispa Server), ветка: $BRANCH..."

mkdir -p ../repos

extract_server_repos() {
    local in_server_section=false
    while IFS=$' \t' read -r line || [[ -n "${line:-}" ]]; do
        line="${line%$'\r'}"

        if [[ "$line" == "# Dispa Server" ]]; then
            in_server_section=true
            continue
        fi

        [[ -z "${line:-}" || "$line" =~ ^# ]] && continue

        if [[ "$in_server_section" == true ]]; then
            echo "$line"
        fi
    done < repos.list
}

extract_server_repos | while IFS=$' \t' read -r name url; do
    [[ -z "${name:-}" ]] && continue
    name="${name%$'\r'}"; url="${url%$'\r'}"
    echo "==> $name: $url ($BRANCH branch)"

    if [ -d "../repos/$name/.git" ]; then
        echo "    Репозиторий $name уже существует, обновляем..."
        git -C "../repos/$name" fetch
        git -C "../repos/$name" checkout "$BRANCH" 2>/dev/null || echo "    Ветка $BRANCH не найдена, остаемся на текущей ветке"
        git -C "../repos/$name" pull --ff-only
    else
        echo "    Клонируем $name..."
        git clone --recurse-submodules -b "$BRANCH" "$url" "../repos/$name" || {
            echo "    Не удалось клонировать с веткой $BRANCH, клонируем по умолчанию..."
            git clone --recurse-submodules "$url" "../repos/$name"
        }
    fi
done

echo "Клонирование репозиториев серверной части завершено!"
