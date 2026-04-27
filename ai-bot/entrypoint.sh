#!/bin/bash
set -e

echo "🔄 Ожидание запуска Ollama..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
  echo "⏳ Ollama ещё не готов, ждём..."
  sleep 3
done

echo "✅ Ollama запущен"

# Проверка наличия модели
if ! curl -s http://ollama:11434/api/tags | grep -q "qwen2.5:3b"; then
  echo "📥 Загрузка модели qwen2.5:3b (это займёт несколько минут)..."
  curl -X POST http://ollama:11434/api/pull -d '{"name":"qwen2.5:3b"}'
  echo "✅ Модель загружена"
else
  echo "✅ Модель qwen2.5:3b уже установлена"
fi

echo "🚀 Запуск AI-бота..."
exec "$@"
