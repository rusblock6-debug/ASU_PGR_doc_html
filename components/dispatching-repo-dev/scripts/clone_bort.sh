#!/usr/bin/env bash
set -eu
if (set -o 2>/dev/null | grep -q '^pipefail'); then
  set -o pipefail
fi

BRANCH="${DEPLOY_BRANCH:-${CI_COMMIT_REF_NAME:-dev}}"
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

        [[ -z "${line:-}" || "$line" =~ ^# ]] && continue

        if [[ "$in_bort_section" == true ]]; then
            echo "$line"
        fi
    done < repos.list
}

extract_bort_repos | while IFS=$' \t' read -r name url; do
    [[ -z "${name:-}" ]] && continue
    name="${name%$'\r'}"; url="${url%$'\r'}"
    echo "==> $name: $url ($BRANCH branch)"

    if [ -d "../repos/$name/.git" ]; then
        echo "    Репозиторий $name уже существует, обновляем..."
        git -C "../repos/$name" fetch --all --prune
        if git -C "../repos/$name" checkout "$BRANCH" 2>/dev/null; then
            :
        elif [ "$BRANCH" != "dev" ] && git -C "../repos/$name" checkout "dev" 2>/dev/null; then
            echo "    Ветка $BRANCH не найдена, переключаемся на dev..."
        else
            echo "    Ветка $BRANCH не найдена, остаемся на текущей ветке"
        fi
        git -C "../repos/$name" pull --ff-only
    else
        echo "    Клонируем $name..."
        git clone --recurse-submodules -b "$BRANCH" "$url" "../repos/$name" || {
            if [ "$BRANCH" != "dev" ]; then
                echo "    Не удалось клонировать с веткой $BRANCH, пробуем dev..."
                git clone --recurse-submodules -b "dev" "$url" "../repos/$name"
            else
                echo "    Не удалось клонировать с веткой dev, клонируем по умолчанию..."
                git clone --recurse-submodules "$url" "../repos/$name"
            fi
        }
    fi
done

echo "Клонирование репозиториев бортовой части завершено!"
