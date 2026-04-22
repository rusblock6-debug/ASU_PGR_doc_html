#!/bin/bash
# Скрипт автоматического запуска Vector с определением hostname сервера

set -e

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
        CURRENT_NAMESPACE="dispa-server"
        ;;
    "nir-bortarh")
        CURRENT_NAMESPACE="dispa-bort2"
        ;;
    "nir-track-04")
        CURRENT_NAMESPACE="dispa-bort"
        ;;
    *)
        CURRENT_NAMESPACE="$CURRENT_HOSTNAME"
        ;;
esac

# Создаем/обновляем .env файл
cat > ./config/vector/.env << EOF
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
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-server ✓"
        ;;
    "nir-bortarh")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-bort-2 ✓"
        ;;
    "nir-track-04")
        echo "Hostname mapping: $CURRENT_HOSTNAME -> namespace: dispa-bort ✓"
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
cd config/vector &&  $DOCKER_COMPOSE_CMD up -d --force-recreate --remove-orphans

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

