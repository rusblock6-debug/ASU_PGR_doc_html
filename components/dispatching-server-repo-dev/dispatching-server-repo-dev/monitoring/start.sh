#!/bin/bash
# Скрипт автоматического запуска Vector с определением hostname сервера

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# Получаем hostname сервера (не контейнера)
CURRENT_HOSTNAME=$(hostname)

echo "=== Запуск Vector для сбора Docker логов ==="
echo "Обнаружен hostname сервера: $CURRENT_HOSTNAME"

# Определяем namespace по mapping
case "$CURRENT_HOSTNAME" in
    "asd-db")
        CURRENT_NAMESPACE="dispa-bort4"
        ;;
    "nir-track-06")
        CURRENT_NAMESPACE="dispa-bort3"
        ;;
    "nir-track-05")
        CURRENT_NAMESPACE="dispa-dev-server"
        ;;
    "nir-bortarh")
        CURRENT_NAMESPACE="dispa-bort2"
        ;;
    "nir-track-04")
        CURRENT_NAMESPACE="dispa-bort"
        ;;
    "nir-dmi-t-k01")
        CURRENT_NAMESPACE="dispa-stage-server"
        ;;
    "nir-dmi-t-k02")
        CURRENT_NAMESPACE="dispa-stage-bort-1"
        ;;
    "nir-dmi-t-k03")
        CURRENT_NAMESPACE="dispa-stage-bort-2"
        ;;
    *)
        CURRENT_NAMESPACE="$CURRENT_HOSTNAME"
        ;;
esac

# Создаем/обновляем .env файл
cat > "${ENV_FILE}" << EOF
# Автоматически определенный hostname сервера
HOST_HOSTNAME=$CURRENT_HOSTNAME

# Автоматически определенный namespace по mapping
NAMESPACE=$CURRENT_NAMESPACE
EOF

echo "Файл .env создан/обновлен"
echo "  HOST_HOSTNAME=$CURRENT_HOSTNAME"
echo "  NAMESPACE=$CURRENT_NAMESPACE"
echo ""

# Проверяем соответствие hostname -> namespace
case "$CURRENT_HOSTNAME" in
    "asd-db")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-bort-4 ✓"
        ;;
    "nir-track-06")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-bort-3 ✓"
        ;;
    "nir-track-05")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-dev-server ✓"
        ;;
    "nir-bortarh")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-bort-2 ✓"
        ;;
    "nir-track-04")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-bort ✓"
        ;;
    "nir-dmi-t-k01")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-stage-server ✓"
        ;;
    "nir-dmi-t-k02")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-stage-bort-1 ✓"
        ;;
    "nir-dmi-t-k03")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-stage-bort-2 ✓"
        ;;
    *)
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: $CURRENT_HOSTNAME (по умолчанию)"
        ;;
esac

echo ""

# Определяем команду для Docker Compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "Ошибка: docker-compose или docker compose не найдены!"
    exit 1
fi

echo "Запуск Docker Compose ($DOCKER_COMPOSE_CMD)..."
cd "${SCRIPT_DIR}" && $DOCKER_COMPOSE_CMD up -d --force-recreate --remove-orphans

echo ""
echo "Vector запущен успешно!"
echo ""
echo "Проверить статус:"
echo "  docker ps | grep vector"
echo ""
echo "Посмотреть логи:"
echo "  docker logs vector-logs"
echo ""
echo "Проверить hostname:"
echo "  docker exec vector-logs env | grep HOST_HOSTNAME"
