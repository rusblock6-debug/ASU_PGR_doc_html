#!/bin/sh
set -e

MODE="${APP_MODE:-dev}"

echo "Установка зависимостей..."
npm ci

if [ "$MODE" = "prod" ] || [ "$MODE" = "production" ]; then
  echo "Запуск в режиме (production)"
  echo "[client] APP_MODE=$MODE → build + nginx"
  npm run build
  rm -rf /usr/share/nginx/html/*
  cp -a dist/* /usr/share/nginx/html/
  exec nginx -g 'daemon off;'
else
  echo "Запуск в режиме (development)"
  echo "[client] APP_MODE=$MODE → Vite"
  exec npm run dev -- --host 0.0.0.0
fi
