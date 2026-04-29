# RAG Bot для АСУ ПГР

## Описание
Self-contained пакет для AI-ассистента системы АСУ ПГР с использованием RAG (Retrieval-Augmented Generation).

## Структура папки
```
tetepfgr/
├── ai-bot/                 # AI бот (FastAPI + ChromaDB + Ollama)
│   ├── docker-compose.yml  # Конфигурация всех сервисов
│   ├── .env.example        # Пример переменных окружения
│   ├── main.py             # FastAPI приложение
│   ├── indexer.py          # Индексация кода и документации
│   ├── chunker.py          # Разбиение на чанки
│   ├── parsers/            # Парсеры документации
│   └── ...
├── admin.html              # Интерфейс администратора
├── data.json               # Документация пользователя
├── directory_data.json     # Справочники
├── screenshots/            # Скриншоты интерфейса
├── library/                # Библиотеки
└── ...
```

## Быстрый старт

### 1. Подготовка
```bash
cd tetepfgr/ai-bot
cp .env.example .env
# Отредактируйте .env при необходимости
```

### 2. Запуск системы
```bash
docker-compose up -d --build
```

Система автоматически:
- Загрузит модель Phi-4-mini в Ollama
- Запустит Redis для кэширования
- Запустит AI бот на порту 8000
- Запустит сервер документации на порту 3000

### 3. Проверка работоспособности
```bash
# Проверка здоровья AI бота
curl http://localhost:8000/health

# Проверка Ollama
curl http://localhost:11434/api/tags

# Проверка Redis
docker exec pgr-redis redis-cli ping
```

### 4. Индексация проекта
После первого запуска выполните полную индексацию:

```bash
python start_indexing.py
```

Или через curl:
```bash
curl -X POST http://localhost:8000/api/index?mode=full \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Использование

### Веб-интерфейс
Откройте в браузере: `http://localhost:3000/admin.html`

### API endpoints

**Задать вопрос:**
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "Как открыть карту?"}'
```

**Переиндексировать:**
```bash
curl -X POST http://localhost:8000/api/index?mode=full \
  -H "X-API-Key: your-api-key"
```

**Статус индексации:**
```bash
curl http://localhost:8000/api/index/status \
  -H "X-API-Key: your-api-key"
```

## Архитектура

### Сервисы
1. **pgr-ollama** - Локальная LLM (Phi-4-mini)
2. **pgr-redis** - Кэш ответов для ускорения
3. **pgr-ai-bot** - FastAPI приложение с RAG логикой
4. **pgr-docs-server** - Сервер документации

### Данные
- `ollama_data/` - Модели Ollama (~4GB)
- `redis_data/` - Кэш Redis
- `ai-bot/chroma_data/` - Векторная база знаний
- `ai-bot/logs/` - Логи приложения
- `ai-bot/snapshots/` - Снэпшоты состояния

## Обновление знаний

После изменения кода или документации:

```bash
# Переиндексация
python start_indexing.py

# Или перезапуск с автоиндексацией
docker-compose down
docker-compose up -d
```

## Передача разработчикам

Для передачи системы достаточно одной папки `tetepfgr/`:

```bash
# Создание архива
tar -czf tetepfgr.tar.gz tetepfgr/

# Или zip
zip -r tetepfgr.zip tetepfgr/
```

Разработчики должны:
1. Распаковать архив
2. Установить Docker Desktop
3. Выполнить `cd tetepfgr/ai-bot && docker-compose up -d`
4. Дождаться загрузки модели (~5 минут первый раз)
5. Выполнить индексацию

## Требования
- Docker Desktop 20.10+
- Docker Compose 2.0+
- Минимум 8GB RAM
- Минимум 10GB свободного места

## Порты
- 3000 - Сервер документации
- 8000 - AI Bot API
- 11434 - Ollama API
- 6379 - Redis

## Troubleshooting

### Модель не загружается
```bash
docker logs pgr-ollama
docker-compose restart ollama
```

### Бот не отвечает
```bash
docker logs pgr-ai-bot
docker-compose restart ai-bot
```

### Ошибка индексации
```bash
docker logs pgr-ai-bot | grep ERROR
docker-compose down
docker-compose up -d
```

### Очистка кэша
```bash
docker-compose down
rm -rf redis_data/*
rm -rf ai-bot/chroma_data/*
docker-compose up -d
```

## Контакты
По вопросам работы системы обращайтесь к команде разработки АСУ ПГР.
