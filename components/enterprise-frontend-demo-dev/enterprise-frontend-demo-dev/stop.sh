#!/bin/bash

echo "🛑 Остановка всех контейнеров..."
echo ""

docker-compose -f docker-compose.dev.yml down
docker-compose down

echo ""
echo "✅ Контейнеры остановлены"

