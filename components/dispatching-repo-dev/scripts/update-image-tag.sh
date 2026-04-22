#!/bin/bash
# =============================================================================
# Скрипт обновления тегов образов в .env файлах
# =============================================================================
# Использование:
#   ./update-image-tag.sh SERVICE_NAME IMAGE_REPO IMAGE_TAG [ENV_FILE]
#
# Примеры:
#   ./update-image-tag.sh trip-service-server registry.dmi-msk.ru/trip-service-server 0.1.123
#   ./update-image-tag.sh enterprise-service registry.dmi-msk.ru/enterprise-service 0.1.456 .env_bort_1
#
# Переменные в .env формируются по шаблону:
#   registry.dmi-msk.ru/enterprise-service -> ENTERPRISE_SERVICE_IMAGE, ENTERPRISE_SERVICE_TAG
# Исключения для compose-алиасов (например wifi-event-dispatcher-bort) задаются ниже.
# =============================================================================

set -euo pipefail

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Проверка аргументов
if [ $# -lt 3 ]; then
    echo -e "${RED}Ошибка: Недостаточно аргументов${NC}"
    echo "Использование: $0 SERVICE_NAME IMAGE_REPO IMAGE_TAG [ENV_FILE]"
    echo ""
    echo "Примеры:"
    echo "  $0 trip-service-server registry.dmi-msk.ru/trip-service-server 0.1.123"
    echo "  $0 enterprise-service registry.dmi-msk.ru/enterprise-service 0.1.456 .env_bort_1"
    exit 1
fi

SERVICE_NAME="$1"
IMAGE_REPO="$2"
IMAGE_TAG="$3"
ENV_FILE="${4:-.env_server}"

normalize_to_var_prefix() {
    echo "$1" | tr '[:lower:]' '[:upper:]' | tr '-' '_'
}

resolve_var_prefix() {
    local service_name="$1"
    local image_repo="$2"
    local repo_name="${image_repo##*/}"

    case "$service_name" in
        wifi-event-dispatcher-bort)
            echo "WIFI_EVENT_DISPATCHER_BORT"
            ;;
        wifi-event-dispatcher-server)
            echo "WIFI_EVENT_DISPATCHER_SERVER"
            ;;
        *)
            normalize_to_var_prefix "$repo_name"
            ;;
    esac
}

# Проверка существования файла
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Предупреждение: Файл $ENV_FILE не существует, создаём...${NC}"
    touch "$ENV_FILE"
fi

# Проверка прав на запись
if [ ! -w "$ENV_FILE" ]; then
    echo -e "${RED}Ошибка: Нет прав на запись в файл $ENV_FILE${NC}"
    echo "Текущий пользователь:"
    id || true
    echo "Права на файл:"
    ls -l "$ENV_FILE" || true
    exit 1
fi

# Формируем префикс переменной из image repo, чтобы compose-алиасы
# вроде trip-service -> DISPA_BACKEND_* тоже обновлялись корректно.
VAR_PREFIX=$(resolve_var_prefix "$SERVICE_NAME" "$IMAGE_REPO")

VAR_IMAGE="${VAR_PREFIX}_IMAGE"
VAR_TAG="${VAR_PREFIX}_TAG"

echo -e "${GREEN}===> Обновление образа для сервиса: $SERVICE_NAME${NC}"
echo "Файл: $ENV_FILE"
echo "Переменные: ${VAR_IMAGE}, ${VAR_TAG}"
echo "Образ: $IMAGE_REPO:$IMAGE_TAG"
echo ""

# Функция обновления или добавления переменной
update_or_add_var() {
    local var_name="$1"
    local var_value="$2"
    local file="$3"

    if grep -q "^${var_name}=" "$file" 2>/dev/null; then
        # Переменная существует - обновляем
        sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" "$file"
        echo "  Обновлено: ${var_name}=${var_value}"
    else
        # Переменная не существует - добавляем
        echo "${var_name}=${var_value}" >> "$file"
        echo "  Добавлено: ${var_name}=${var_value}"
    fi
}

# Обновляем переменные
update_or_add_var "$VAR_IMAGE" "$IMAGE_REPO" "$ENV_FILE"
update_or_add_var "$VAR_TAG" "$IMAGE_TAG" "$ENV_FILE"

echo ""
echo -e "${GREEN}===> Готово${NC}"
