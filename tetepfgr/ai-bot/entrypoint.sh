#!/bin/bash
set -e

echo "🚀 Starting AI-bot..."

# Запуск uvicorn
exec uvicorn main:app --host 0.0.0.0 --port 8000
