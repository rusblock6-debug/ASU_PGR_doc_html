#!/bin/bash

echo "🚀 Запуск фронтенда в Docker (Development режим)"
echo ""
echo "Приложение будет доступно на: http://localhost:3000"
echo ""

# Проверка наличия backend
echo "⚠️  Убедитесь, что backend запущен на http://0.0.0.0:8001"
echo ""

# Запуск
docker-compose -f docker-compose.dev.yml up --build

