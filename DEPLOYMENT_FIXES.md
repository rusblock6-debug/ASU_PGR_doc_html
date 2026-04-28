# Лог исправлений при развертывании RAG-бота

## Дата: 28 апреля 2026

### Исправление #1: Line endings в entrypoint.sh
**Проблема**: `exec /entrypoint.sh: no such file or directory`  
**Причина**: Windows CRLF вместо Unix LF  
**Решение**: Конвертировал CRLF → LF через PowerShell, пересобрал контейнер  
**Статус**: ✅ Исправлено

---

## Текущий статус
- ✅ Контейнеры запущены
- ✅ Модель phi4-mini загружена (2.5 GB)
- ✅ FastAPI сервер работает на :8000
- ✅ Health check пройден (Ollama, ChromaDB, Redis подключены)
- 🔄 Запуск индексации...
