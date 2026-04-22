#!/usr/bin/env bash
set -eu
if (set -o 2>/dev/null | grep -q '^pipefail'); then
  set -o pipefail
fi
BRANCH="${DEPLOY_BRANCH:-dev}"
echo "Клонирование репозиториев для бортовой части (Dispa bort), ветка: $BRANCH..."
mkdir -p ../repos
extract_bort_repos() {
    local in_bort_section=false
    while IFS=$' \t' read -r line || [[ -n "${line:-}" ]]; do
        line="${line%$'\r'}"
        if [[ "$line" == "# Dispa bort" ]]; then
            in_bort_section=true
            continue
        fi
        if [[ "$line" =~ ^#[[:space:]].* && "$in_bort_section" == true ]]; then
            break
        fi
        [[ -z "${line:-}" || "$line" =~ ^# ]] && continue
        if [[ "$in_bort_section" == true ]]; then
            echo "$line"
        fi
    done < repos.list
}
extract_bort_repos | while IFS=$' \t' read -r name url; do
    [[ -z "${name:-}" ]] && continue
    [[ "$name" == "cursor-rules" ]] && continue
    name="${name%$'\r'}"; url="${url%$'\r'}"
    echo "==> $name: $url ($BRANCH branch)"
    if [ -d "../repos/$name/.git" ]; then
        echo "    Репозиторий $name уже существует, обновляем..."
        git -C "../repos/$name" fetch origin
        git -C "../repos/$name" checkout "$BRANCH" 2>/dev/null || echo "    Ветка $BRANCH не найдена, остаемся на текущей ветке"
        git -C "../repos/$name" reset --hard "origin/$BRANCH"
    else
        echo "    Клонируем $name..."
        git clone --recurse-submodules -b "$BRANCH" "$url" "../repos/$name" || {
            echo "    Не удалось клонировать с веткой $BRANCH, клонируем по умолчанию..."
            git clone --recurse-submodules "$url" "../repos/$name"
        }
    fi
done
echo "Клонирование завершено!"