#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Использование:
  cleanup-image-tags.sh --repo IMAGE_REPO [--keep-tag TAG ...] [--dry-run]

Примеры:
  cleanup-image-tags.sh --repo registry.dmi-msk.ru/dispa-backend --keep-tag 0.1.123 --keep-tag staging-latest
  cleanup-image-tags.sh --repo registry.dmi-msk.ru/api-gateway --keep-tag branch-latest --dry-run
EOF
}

REPO=""
DRY_RUN="0"
KEEP_TAGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --repo)
            REPO="${2:-}"
            shift 2
            ;;
        --keep-tag)
            KEEP_TAGS+=("${2:-}")
            shift 2
            ;;
        --dry-run)
            DRY_RUN="1"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Ошибка: неизвестный аргумент: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [ -z "$REPO" ]; then
    echo "Ошибка: не указан --repo" >&2
    usage >&2
    exit 1
fi

if [ ${#KEEP_TAGS[@]} -eq 0 ]; then
    KEEP_TAGS=("${DEFAULT_KEEP_TAG:-dev-latest}")
fi

declare -A KEEP_REFS=()

for tag in "${KEEP_TAGS[@]}"; do
    [ -n "$tag" ] || continue
    KEEP_REFS["${REPO}:${tag}"]=1
done

while IFS= read -r running_image; do
    case "$running_image" in
        "${REPO}:"*)
            KEEP_REFS["$running_image"]=1
            ;;
    esac
done < <(docker ps --format '{{.Image}}')

mapfile -t IMAGE_REFS < <(docker image ls --format '{{.Repository}}:{{.Tag}}' "$REPO" | awk '$0 != "<none>:<none>" { print }' | sort -u)

if [ ${#IMAGE_REFS[@]} -eq 0 ]; then
    echo "Локальные образы для ${REPO} не найдены"
    exit 0
fi

echo "===> Cleanup образов для ${REPO}"
echo "Сохраняем:"
for image_ref in "${!KEEP_REFS[@]}"; do
    echo "  ${image_ref}"
done | sort

removed_any="0"

for image_ref in "${IMAGE_REFS[@]}"; do
    if [ -n "${KEEP_REFS[$image_ref]+x}" ]; then
        echo "  keep   ${image_ref}"
        continue
    fi

    if [ "$DRY_RUN" = "1" ]; then
        echo "  dryrun ${image_ref}"
        continue
    fi

    if docker image rm "$image_ref" >/dev/null 2>&1; then
        echo "  remove ${image_ref}"
        removed_any="1"
    else
        echo "  skip   ${image_ref} (образ занят или удаление не удалось)"
    fi
done

if [ "$DRY_RUN" = "1" ]; then
    echo "Dry-run завершён"
    exit 0
fi

if [ "$removed_any" = "1" ]; then
    docker image prune -f >/dev/null
fi

echo "Cleanup завершён"
