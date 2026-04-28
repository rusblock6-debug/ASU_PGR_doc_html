#!/bin/bash
set -e

echo "🔄 Ожидание запуска Ollama..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
  echo "⏳ Ollama ещё не готов, ждём..."
  sleep 3
done

echo "✅ Ollama запущен"

# Проверка наличия модели Phi-4-mini
if ! curl -s http://ollama:11434/api/tags | grep -q "phi4-mini"; then
  echo "📥 Загрузка модели phi4-mini (это займёт несколько минут)..."
  curl -X POST http://ollama:11434/api/pull -d '{"name":"phi4-mini"}'
  echo "✅ Модель phi4-mini загружена"
else
  echo "✅ Модель phi4-mini уже установлена"
fi

echo "🚀 Запуск AI-бота с гибридным чанкованием..."
exec "$@"
