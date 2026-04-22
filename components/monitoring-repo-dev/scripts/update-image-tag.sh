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
#   trip-service-server -> TRIP_SERVICE_SERVER_IMAGE, TRIP_SERVICE_SERVER_TAG
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

# Проверка существования файла
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Предупреждение: Файл $ENV_FILE не существует, создаём...${NC}"
    touch "$ENV_FILE"
fi

# Формируем префикс переменной: trip-service-server -> TRIP_SERVICE_SERVER
VAR_PREFIX=$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]' | tr '-' '_')

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
